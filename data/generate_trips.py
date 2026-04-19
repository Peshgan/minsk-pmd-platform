"""
Generate synthetic scooter trips on the Minsk road network.

GPS model: 1 fix per second (1 Hz) — matches real Bolt/Whoosh telemetry.
This gives clean kinematics: speed = distance/1s, accel = Δspeed/1s.

Dangerous event injection pattern (guaranteed 2+ consecutive DANGER points):
  ..., base, MAX, MAX, 0.5, base, ...
  accels:  +large,  0,  -8.5,  +4.5
  labels:   WARN  SAFE  DANGER DANGER   → trip_verdict = DANGER

Outputs data/output/trips.geojson — 500 trips, 20% dangerous.

Usage:
    python data/generate_trips.py
"""

import json
import os
import time
from math import atan2, cos, radians, sin, sqrt

import networkx as nx
import numpy as np
import osmnx as ox

# ── Configuration ──────────────────────────────────────────────────────────────

GRAPH_PATH  = os.path.join(os.path.dirname(__file__), "minsk.graphml")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "trips.geojson")

N_TRIPS         = 500
DANGEROUS_RATIO = 0.20

BASE_SPEED_MIN  = 3.5   # m/s  ≈ 12.6 km/h
BASE_SPEED_MAX  = 6.0   # m/s  ≈ 21.6 km/h
SPEED_NOISE_STD = 0.20  # Gaussian noise per GPS second
MAX_SPEED       = 9.0   # hard cap

PATH_MIN_M = 400
PATH_MAX_M = 5000

RANDOM_SEED = 42

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


# ── Geometry ───────────────────────────────────────────────────────────────────

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6_371_000
    phi1, phi2 = radians(lat1), radians(lat2)
    a = (sin((radians(lat2) - phi1) / 2) ** 2
         + cos(phi1) * cos(phi2) * sin((radians(lon2 - lon1)) / 2) ** 2)
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def path_to_dense(G, path_nodes: list):
    """
    Return dense (lon, lat) coords every ~8m along the OSM path
    AND their cumulative distances.
    """
    # cum[i] = cumulative distance TO dense[i]  → always len(cum) == len(dense)
    dense: list = []
    cum:   list = []

    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        edge = G[u][v][0]
        raw = (list(edge["geometry"].coords)
               if "geometry" in edge
               else [(G.nodes[u]["x"], G.nodes[u]["y"]),
                     (G.nodes[v]["x"], G.nodes[v]["y"])])

        for j in range(len(raw) - 1):
            p1, p2 = raw[j], raw[j + 1]
            seg_m = haversine(p1[0], p1[1], p2[0], p2[1])
            n_pts = max(1, int(seg_m / 8))
            for k in range(n_pts):
                t = k / n_pts
                pt = (p1[0] + t * (p2[0] - p1[0]),
                      p1[1] + t * (p2[1] - p1[1]))
                prev_cum = cum[-1] if cum else 0.0
                step_d   = haversine(*dense[-1], *pt) if dense else 0.0
                dense.append(pt)
                cum.append(prev_cum + step_d)

    last = path_nodes[-1]
    last_pt = (G.nodes[last]["x"], G.nodes[last]["y"])
    step_d  = haversine(*dense[-1], *last_pt) if dense else 0.0
    dense.append(last_pt)
    cum.append((cum[-1] if cum else 0.0) + step_d)

    return dense, cum


def interp_on_path(dense, cum_dists, d: float):
    """Interpolate (lon, lat) at cumulative distance d."""
    total = cum_dists[-1]
    d = min(max(d, 0.0), total)
    lo, hi = 0, len(cum_dists) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if cum_dists[mid] <= d:
            lo = mid
        else:
            hi = mid
    seg = cum_dists[hi] - cum_dists[lo]
    if seg < 1e-9:
        return dense[lo]
    t = (d - cum_dists[lo]) / seg
    return (dense[lo][0] + t * (dense[hi][0] - dense[lo][0]),
            dense[lo][1] + t * (dense[hi][1] - dense[lo][1]))


# ── Speed profile (1-second ticks) ────────────────────────────────────────────

def make_speed_profile(n_seconds: int, base: float,
                       has_danger: bool, rng: np.random.Generator) -> np.ndarray:
    """
    Speed (m/s) at each 1-second tick.

    Dangerous injection: [... base, MAX, MAX, MAX, 0.5, MAX, base ...]
    accels:              [  +large,   0,   0, -8.5, +8.5,   ≈-3 ]
    Window at brake (0.5): next_high = abs(+8.5) ≥ 3.5 → DANGER ✓
    Window at recovery (MAX): prev_high = abs(-8.5) ≥ 3.5 → DANGER ✓
    Works for ANY base_speed — no dependency on base ≥ 4.0.
    """
    speeds = np.clip(rng.normal(base, SPEED_NOISE_STD, n_seconds), 0.5, MAX_SPEED)

    if has_danger and n_seconds > 14:
        mid_s = n_seconds // 3
        mid_e = 2 * n_seconds // 3
        evt   = int(rng.integers(mid_s, mid_e - 6))

        speeds[evt]     = MAX_SPEED   # acceleration burst
        speeds[evt + 1] = MAX_SPEED   # sustained fast → accel=0
        speeds[evt + 2] = MAX_SPEED   # sustained fast → accel=0
        speeds[evt + 3] = 0.5         # hard brake     → accel=-8.5  DANGER candidate
        speeds[evt + 4] = MAX_SPEED   # rebound        → accel=+8.5  DANGER candidate
        speeds[evt + 5] = base        # return to base

    return speeds


# ── GPS trace from speed profile ───────────────────────────────────────────────

def speeds_to_gps(dense, cum_dists, speeds: np.ndarray):
    """
    Walk the path second-by-second.
    At each tick t the scooter moves speeds[t] metres → yields one (lon, lat).
    """
    total = cum_dists[-1]
    gps   = []
    d     = 0.0
    for spd in speeds:
        lon, lat = interp_on_path(dense, cum_dists, d)
        gps.append([round(lon, 7), round(lat, 7)])
        d = min(d + spd, total)
    return gps


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)

    print(f"Loading graph from {GRAPH_PATH} ...")
    G = ox.load_graphml(GRAPH_PATH)
    nodes_list = list(G.nodes)
    n_nodes    = len(nodes_list)
    print(f"  {n_nodes:,} nodes  {len(G.edges):,} edges\n")

    n_dangerous   = int(N_TRIPS * DANGEROUS_RATIO)
    dangerous_set = set(rng.choice(N_TRIPS, n_dangerous, replace=False).tolist())

    features = []
    skipped  = 0
    attempts = 0
    t0       = time.time()
    trip_idx = 0

    while trip_idx < N_TRIPS:
        attempts += 1
        if attempts > N_TRIPS * 25:
            print(f"WARNING: giving up after {attempts} attempts ({trip_idx} trips)")
            break

        orig = nodes_list[int(rng.integers(0, n_nodes))]
        dest = nodes_list[int(rng.integers(0, n_nodes))]
        if orig == dest:
            continue

        try:
            path_nodes = nx.shortest_path(G, orig, dest, weight="length")
        except nx.NetworkXNoPath:
            skipped += 1
            continue

        path_len = sum(
            G[path_nodes[i]][path_nodes[i + 1]][0].get("length", 0)
            for i in range(len(path_nodes) - 1)
        )
        if not (PATH_MIN_M <= path_len <= PATH_MAX_M):
            continue

        dense, cum_dists = path_to_dense(G, path_nodes)
        if len(dense) < 5:
            continue

        base_speed  = float(rng.uniform(BASE_SPEED_MIN, BASE_SPEED_MAX))
        n_seconds   = max(int(path_len / base_speed) + 1, 12)
        has_danger  = trip_idx in dangerous_set

        speeds      = make_speed_profile(n_seconds, base_speed, has_danger, rng)
        gps_coords  = speeds_to_gps(dense, cum_dists, speeds)
        timestamps  = list(range(n_seconds))   # [0, 1, 2, ..., n-1]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": gps_coords,
            },
            "properties": {
                "trip_id":             f"trip_{trip_idx:04d}",
                "timestamps_s":        timestamps,
                "n_points":            n_seconds,
                "distance_m":          round(path_len, 1),
                "duration_s":          n_seconds - 1,
                "avg_speed_ms":        round(float(np.mean(speeds)), 2),
                "has_dangerous_event": has_danger,
            },
        })

        trip_idx += 1
        if trip_idx % 50 == 0 or trip_idx == N_TRIPS:
            print(f"  {trip_idx:>3}/{N_TRIPS}  [{time.time() - t0:.1f}s]")

    geojson = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))

    size_kb  = os.path.getsize(OUTPUT_PATH) / 1024
    dist_arr = [f["properties"]["distance_m"] for f in features]
    n_d      = sum(1 for f in features if f["properties"]["has_dangerous_event"])

    print(f"\nSaved {len(features)} trips -> {OUTPUT_PATH}  ({size_kb:.0f} KB)")
    print(f"  Dangerous  : {n_d} ({n_d/len(features)*100:.0f}%)")
    print(f"  Skipped    : {skipped}")
    print(f"  Dist range : {min(dist_arr):.0f}m - {max(dist_arr):.0f}m"
          f"  mean {sum(dist_arr)/len(dist_arr):.0f}m")
    print(f"  Time       : {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
