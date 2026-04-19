"""
Algorithm A — Dangerous Driving Detector.

Design doc reference: Layer 3, Algorithm A.

Pipeline per trip:
  1. Load (lon, lat, t) sequence from trips.geojson
  2. Compute segment distances via Haversine
  3. Derive speed at each segment midpoint
  4. Derive acceleration via sliding window (window = 3 consecutive speed values)
  5. Classify each GPS point: SAFE / WARN / DANGER
     WARN   : |a| in [2.5, 3.5) m/s²  (sustained 1+ point)
     DANGER : |a| >= 3.5 m/s²          (sustained 2+ consecutive points)
  6. Tag trip-level verdict and export annotated GeoJSON for the dashboard

Outputs:
  data/output/analyzed_trips.geojson  — full LineString features with per-point labels
  data/output/dangerous_segments.geojson — only the flagged segments (PathLayer feed)
  data/output/analysis_report.json   — summary statistics for the dashboard panel

Usage:
    python analytics/dangerous_driving.py
"""

import json
import os
import time
from math import atan2, cos, radians, sin, sqrt

# ── Thresholds (Algorithm A, design doc) ──────────────────────────────────────

WARN_ACCEL   = 2.5   # m/s²  — amber flag
DANGER_ACCEL = 3.5   # m/s²  — red flag (Dozza 2013 calibration)
DANGER_WINDOW = 2    # consecutive points above threshold → confirmed DANGER

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT          = os.path.dirname(os.path.dirname(__file__))
TRIPS_PATH    = os.path.join(ROOT, "data", "output", "trips.geojson")
OUT_ANALYZED  = os.path.join(ROOT, "data", "output", "analyzed_trips.geojson")
OUT_SEGMENTS  = os.path.join(ROOT, "data", "output", "dangerous_segments.geojson")
OUT_REPORT    = os.path.join(ROOT, "data", "output", "analysis_report.json")


# ── Geometry ───────────────────────────────────────────────────────────────────

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6_371_000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


# ── Core algorithm ─────────────────────────────────────────────────────────────

def compute_kinematics(coords: list, timestamps: list) -> tuple:
    """
    Return parallel lists: speeds (m/s) and accelerations (m/s²),
    one value per GPS point.

    Speed[i]  = distance(i-1, i) / dt(i-1, i)   — segment speed arriving at i
    Accel[i]  = (speed[i] - speed[i-1]) / dt     — first-difference acceleration

    Index 0 is seeded with 0.0 for both (no predecessor).
    """
    n = len(coords)
    speeds = [0.0] * n
    accels = [0.0] * n

    for i in range(1, n):
        lon1, lat1 = coords[i - 1]
        lon2, lat2 = coords[i]
        dt = timestamps[i] - timestamps[i - 1]
        if dt < 1e-6:
            speeds[i] = speeds[i - 1]
        else:
            dist = haversine(lon1, lat1, lon2, lat2)
            speeds[i] = dist / dt

        dt_accel = timestamps[i] - timestamps[i - 1]
        if dt_accel < 1e-6:
            accels[i] = 0.0
        else:
            accels[i] = (speeds[i] - speeds[i - 1]) / dt_accel

    return speeds, accels


def classify_points(accels: list) -> list:
    """
    Assign a label to each GPS point using a sliding window:

      DANGER : |a| >= DANGER_ACCEL for this point AND at least one
               of its immediate neighbours also exceeds DANGER_ACCEL.
               (window = 2 consecutive points — suppresses single GPS spikes)
      WARN   : |a| >= WARN_ACCEL (single point, not enough for DANGER)
      SAFE   : everything else
    """
    n = len(accels)
    abs_a = [abs(a) for a in accels]
    labels = ["SAFE"] * n

    for i in range(n):
        if abs_a[i] >= DANGER_ACCEL:
            # Check window: at least one neighbour also above threshold
            prev_high = (i > 0     and abs_a[i - 1] >= DANGER_ACCEL)
            next_high = (i < n - 1 and abs_a[i + 1] >= DANGER_ACCEL)
            if prev_high or next_high:
                labels[i] = "DANGER"
            else:
                labels[i] = "WARN"   # isolated spike → downgrade to WARN
        elif abs_a[i] >= WARN_ACCEL:
            labels[i] = "WARN"

    return labels


def trip_verdict(labels: list) -> str:
    """Roll up point labels to a single trip-level verdict."""
    if "DANGER" in labels:
        return "DANGER"
    if "WARN" in labels:
        return "WARN"
    return "SAFE"


def extract_danger_segments(
    coords: list,
    labels: list,
    accels: list,
    speeds: list,
    timestamps: list,
    trip_id: str,
) -> list:
    """
    Return a list of GeoJSON LineString features, one per contiguous run
    of WARN/DANGER points, for the PathLayer in the dashboard.
    """
    segments = []
    i = 0
    while i < len(labels):
        if labels[i] in ("WARN", "DANGER"):
            j = i
            while j < len(labels) and labels[j] in ("WARN", "DANGER"):
                j += 1
            # segment covers indices i..j-1
            seg_coords = coords[i:j]
            if len(seg_coords) >= 2:
                seg_accels = accels[i:j]
                peak_a     = max(abs(a) for a in seg_accels)
                verdict    = "DANGER" if peak_a >= DANGER_ACCEL else "WARN"
                segments.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": seg_coords,
                    },
                    "properties": {
                        "trip_id":   trip_id,
                        "verdict":   verdict,
                        "peak_accel_ms2": round(peak_a, 3),
                        "peak_speed_ms":  round(max(speeds[i:j]), 2),
                        "duration_s":     round(timestamps[j - 1] - timestamps[i], 1),
                        "n_points":       j - i,
                    },
                })
            i = j
        else:
            i += 1
    return segments


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()

    print(f"Loading trips from {TRIPS_PATH} ...")
    with open(TRIPS_PATH, encoding="utf-8") as f:
        geojson_in = json.load(f)

    features_in = geojson_in["features"]
    print(f"  {len(features_in)} trips loaded\n")

    analyzed_features  = []
    danger_seg_features = []

    # Counters for report
    verdicts = {"SAFE": 0, "WARN": 0, "DANGER": 0}
    true_positives   = 0   # injected dangerous + detected DANGER
    false_negatives  = 0   # injected dangerous + not detected
    false_positives  = 0   # not injected + detected DANGER
    true_negatives   = 0

    peak_accels_all  = []  # for distribution stats

    for feat in features_in:
        props      = feat["properties"]
        trip_id    = props["trip_id"]
        coords     = feat["geometry"]["coordinates"]   # [[lon, lat], ...]
        timestamps = props["timestamps_s"]
        injected   = props["has_dangerous_event"]

        speeds, accels = compute_kinematics(coords, timestamps)
        labels         = classify_points(accels)
        verdict        = trip_verdict(labels)

        verdicts[verdict] += 1

        # Confusion matrix vs injected ground truth
        if injected and verdict == "DANGER":
            true_positives += 1
        elif injected and verdict != "DANGER":
            false_negatives += 1
        elif not injected and verdict == "DANGER":
            false_positives += 1
        else:
            true_negatives += 1

        peak_a = max(abs(a) for a in accels)
        peak_accels_all.append(peak_a)

        # Annotated trip feature
        analyzed_features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": {
                **props,
                "verdict":           verdict,
                "peak_accel_ms2":    round(peak_a, 3),
                "max_speed_ms":      round(max(speeds), 2),
                "point_labels":      labels,          # per-point classification
            },
        })

        # Dangerous segment features for PathLayer
        segs = extract_danger_segments(
            coords, labels, accels, speeds, timestamps, trip_id
        )
        danger_seg_features.extend(segs)

    # ── Write analyzed trips GeoJSON ───────────────────────────────────────────
    with open(OUT_ANALYZED, "w", encoding="utf-8") as f:
        json.dump(
            {"type": "FeatureCollection", "features": analyzed_features},
            f, ensure_ascii=False, separators=(",", ":"),
        )

    # ── Write dangerous segments GeoJSON ──────────────────────────────────────
    with open(OUT_SEGMENTS, "w", encoding="utf-8") as f:
        json.dump(
            {"type": "FeatureCollection", "features": danger_seg_features},
            f, ensure_ascii=False, separators=(",", ":"),
        )

    # ── Compute report ─────────────────────────────────────────────────────────
    n = len(features_in)
    precision = true_positives / max(true_positives + false_positives, 1)
    recall    = true_positives / max(true_positives + false_negatives, 1)
    f1        = 2 * precision * recall / max(precision + recall, 1e-9)

    mean_peak = sum(peak_accels_all) / n
    max_peak  = max(peak_accels_all)

    report = {
        "algorithm":         "Algorithm A — Dangerous Driving Detector",
        "version":           "1.0",
        "thresholds": {
            "warn_accel_ms2":   WARN_ACCEL,
            "danger_accel_ms2": DANGER_ACCEL,
            "window_points":    DANGER_WINDOW,
        },
        "trips_analyzed":    n,
        "verdicts": verdicts,
        "dangerous_segments_found": len(danger_seg_features),
        "detection_quality": {
            "true_positives":  true_positives,
            "false_negatives": false_negatives,
            "false_positives": false_positives,
            "true_negatives":  true_negatives,
            "precision":       round(precision, 3),
            "recall":          round(recall, 3),
            "f1_score":        round(f1, 3),
        },
        "acceleration_stats": {
            "mean_peak_ms2":   round(mean_peak, 3),
            "max_peak_ms2":    round(max_peak, 3),
            "threshold_ms2":   DANGER_ACCEL,
        },
        "output_files": {
            "analyzed_trips":    OUT_ANALYZED,
            "dangerous_segments": OUT_SEGMENTS,
        },
    }

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # ── Print summary ──────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    injected_total = true_positives + false_negatives

    print("=" * 55)
    print("ALGORITHM A — RESULTS")
    print("=" * 55)
    print(f"Trips analyzed      : {n}")
    print(f"  SAFE              : {verdicts['SAFE']}")
    print(f"  WARN              : {verdicts['WARN']}")
    print(f"  DANGER            : {verdicts['DANGER']}")
    print()
    print(f"Ground truth (injected dangerous trips): {injected_total}")
    print(f"  Detected (TP)     : {true_positives}")
    print(f"  Missed   (FN)     : {false_negatives}")
    print(f"  False alarms (FP) : {false_positives}")
    print()
    print(f"Precision : {precision:.1%}")
    print(f"Recall    : {recall:.1%}")
    print(f"F1 score  : {f1:.3f}")
    print()
    print(f"Dangerous segments  : {len(danger_seg_features)}")
    print(f"Max peak accel      : {max_peak:.2f} m/s^2")
    print(f"Runtime             : {elapsed:.2f}s")
    print("=" * 55)
    print(f"\nOutputs:")
    print(f"  {OUT_ANALYZED}")
    print(f"  {OUT_SEGMENTS}")
    print(f"  {OUT_REPORT}")


if __name__ == "__main__":
    main()
