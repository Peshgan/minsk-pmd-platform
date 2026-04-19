"""
Generate synthetic scooter trips on the Minsk road network.

Outputs data/output/trips.geojson:
  - 500 trips as GeoJSON LineString features
  - Each feature stores timestamps and speed metadata
  - ~20% of trips contain injected dangerous driving events
    (sudden acceleration/braking above 3.5 m/s² threshold)

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
DANGEROUS_RATIO = 0.20      # 20% of trips get injected dangerous events

# Scooter speed parameters (m/s)
BASE_SPEED_MIN  = 3.5       # ≈ 12.6 km/h
BASE_SPEED_MAX  = 6.0       # ≈ 21.6 km/h
SPEED_NOISE_STD = 0.25      # Gaussian noise per GPS point
MAX_SPEED       = 9.0       # hard cap

# Dangerous driving thresholds (Algorithm A, design doc §Layer 3)
DANGER_ACCEL_MIN = 3.8      # m/s²  (threshold: 3.5 → use 3.8 to be clearly above)
DANGER_ACCEL_MAX = 6.0      # m/s²

# Path length constraints (metres)
PATH_MIN_M = 400
PATH_MAX_M = 5000

# GPS interpolation: one virtual fix every N metres
POINT_SPACING_M = 8

RANDOM_SEED = 42

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


# ── Geometry helpers ───────────────────────────────────────────────────────────

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in metres between two (lon, lat) points."""
    R = 6_371_000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def path_to_coords(G, path_nodes: list) -> list:
    """
    Walk the path node sequence and return dense (lon, lat) points,
    sampled every POINT_SPACING_M metres using edge geometry when available.
    """
    dense: list[tuple[float, float]] = []

    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        edge = G[u][v][0]   # key 0 in MultiDiGraph

        if "geometry" in edge:
            raw = list(edge["geometry"].coords)  # (lon, lat)
        else:
            raw = [
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"]),
            ]

        for j in range(len(raw) - 1):
            p1, p2 = raw[j], raw[j + 1]
            seg_m = haversine(p1[0], p1[1], p2[0], p2[1])
            n_pts = max(1, int(seg_m / POINT_SPACING_M))
            for k in range(n_pts):
                t = k / n_pts
                dense.append((
                    p1[0] + t * (p2[0] - p1[0]),
                    p1[1] + t * (p2[1] - p1[1]),
                ))

    last = path_nodes[-1]
    dense.append((G.nodes[last]["x"], G.nodes[last]["y"]))
    return dense


# ── Speed profile ──────────────────────────────────────────────────────────────

def make_speed_profile(
    n: int,
    base: float,
    has_danger: bool,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Speed (m/s) at each GPS point with Gaussian noise.

    Dangerous event: a speed spike sustained for 2-3 consecutive points,
    followed by sharp braking — both above the 3.5 m/s² Algorithm A threshold.
    Injected in the middle third of the trip so the detector has context on
    both sides.
    """
    speeds = np.clip(rng.normal(base, SPEED_NOISE_STD, n), 1.0, MAX_SPEED)

    if has_danger and n > 15:
        mid_s   = n // 3
        mid_e   = 2 * n // 3
        evt_idx = int(rng.integers(mid_s, mid_e))
        accel   = rng.uniform(DANGER_ACCEL_MIN, DANGER_ACCEL_MAX)

        # dt per GPS point at base speed (seconds)
        dt = POINT_SPACING_M / base
        spike = accel * dt * 2  # Δv that produces the required acceleration

        # 2-3 point burst of high speed
        burst = int(rng.integers(2, 4))
        for k in range(burst):
            speeds[min(evt_idx + k, n - 1)] = min(base + spike, MAX_SPEED)

        # Immediate braking after the burst
        brake_idx = min(evt_idx + burst, n - 1)
        speeds[brake_idx] = max(base - spike * 0.8, 1.0)

    return speeds


def coords_to_timestamps(coords: list, speeds: np.ndarray) -> list:
    """Accumulate travel time (seconds) at each GPS point."""
    ts = [0.0]
    for i in range(1, len(coords)):
        d = haversine(coords[i - 1][0], coords[i - 1][1],
                      coords[i][0],     coords[i][1])
        v = max((speeds[i - 1] + speeds[i]) / 2, 0.5)
        ts.append(ts[-1] + d / v)
    return ts


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)

    print(f"Loading graph from {GRAPH_PATH} ...")
    G = ox.load_graphml(GRAPH_PATH)
    nodes_list = list(G.nodes)
    n_nodes    = len(nodes_list)
    print(f"  {n_nodes:,} nodes, {len(G.edges):,} edges\n")

    # Pre-assign which trip indices will be dangerous
    n_dangerous  = int(N_TRIPS * DANGEROUS_RATIO)
    dangerous_set = set(
        rng.choice(N_TRIPS, n_dangerous, replace=False).tolist()
    )

    features = []
    skipped  = 0
    attempts = 0
    t0       = time.time()
    trip_idx = 0

    while trip_idx < N_TRIPS:
        attempts += 1
        if attempts > N_TRIPS * 25:
            print(f"WARNING: stopping after {attempts} attempts ({trip_idx} trips built)")
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

        coords = path_to_coords(G, path_nodes)
        if len(coords) < 5:
            continue

        base_speed = float(rng.uniform(BASE_SPEED_MIN, BASE_SPEED_MAX))
        has_danger = trip_idx in dangerous_set
        speeds     = make_speed_profile(len(coords), base_speed, has_danger, rng)
        timestamps = coords_to_timestamps(coords, speeds)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[round(lon, 7), round(lat, 7)]
                                for lon, lat in coords],
            },
            "properties": {
                "trip_id":             f"trip_{trip_idx:04d}",
                "timestamps_s":        [round(t, 2) for t in timestamps],
                "n_points":            len(coords),
                "distance_m":          round(path_len, 1),
                "duration_s":          round(timestamps[-1], 1),
                "avg_speed_ms":        round(float(np.mean(speeds)), 2),
                "has_dangerous_event": has_danger,
            },
        })

        trip_idx += 1
        if trip_idx % 50 == 0 or trip_idx == N_TRIPS:
            print(f"  {trip_idx:>3}/{N_TRIPS}  [{time.time() - t0:.1f}s]")

    # ── Write output ───────────────────────────────────────────────────────────
    geojson = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))

    size_kb  = os.path.getsize(OUTPUT_PATH) / 1024
    dist_arr = [feat["properties"]["distance_m"] for feat in features]
    n_danger = sum(1 for feat in features if feat["properties"]["has_dangerous_event"])

    print(f"\nSaved {len(features)} trips -> {OUTPUT_PATH}  ({size_kb:.0f} KB)")
    print(f"  Dangerous trips : {n_danger} ({n_danger/len(features)*100:.0f}%)")
    print(f"  Skipped (no path): {skipped}")
    print(f"  Distance range  : {min(dist_arr):.0f}m - {max(dist_arr):.0f}m"
          f"  (mean {sum(dist_arr)/len(dist_arr):.0f}m)")
    print(f"  Total time      : {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
