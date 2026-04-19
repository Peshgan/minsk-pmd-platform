"""
Algorithm B — Blind Spot Classifier.

Design doc reference: Layer 3, Algorithm B.

A "blind spot" is an H3 hexagonal zone that satisfies both:
  1. HIGH PMD density  : visit_count > P75 of all visited hexes
  2. ZERO cycling infra: no cycleways or bike lanes cross the hex

Severity = density_score × conflict_weight
  conflict_weight (from OSM maxspeed or highway type):
    1.5  — maxspeed > 60 km/h  (scooters share space with fast traffic)
    1.2  — maxspeed 40–60 km/h (medium-speed roads)
    1.0  — residential / unknown

H3 resolution 9  →  hex edge ≈ 174 m, area ≈ 0.105 km².

Outputs:
  data/output/blind_spots.geojson  — top-10 zones (H3HexagonLayer)
  data/output/all_hexes.geojson    — all visited hexes (density heatmap)

Usage:
    python analytics/blind_spot.py
"""

import json
import os
import time
from collections import defaultdict

import h3
import numpy as np
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, mapping

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT        = os.path.dirname(os.path.dirname(__file__))
GRAPH_PATH  = os.path.join(ROOT, "data", "minsk.graphml")
TRIPS_PATH  = os.path.join(ROOT, "data", "output", "trips.geojson")
OUT_BLIND   = os.path.join(ROOT, "data", "output", "blind_spots.geojson")
OUT_ALL     = os.path.join(ROOT, "data", "output", "all_hexes.geojson")

RESOLUTION  = 9      # H3 hex edge ≈ 174 m
TOP_N       = 10
DENSITY_PCT = 75     # P75 threshold


# ── Maxspeed helpers ───────────────────────────────────────────────────────────

def parse_maxspeed(val) -> float | None:
    """Parse OSM maxspeed tag to km/h.  Returns None if unparseable."""
    if val is None:
        return None
    s = str(val).strip().lower().replace(" ", "")

    # Belarusian / Russian zone codes
    _zones = {
        "by:urban": 60.0, "ru:urban": 60.0,
        "by:rural": 90.0, "ru:rural": 90.0,
        "by:living_zone": 20.0, "ru:living_zone": 20.0,
        "by:motorway": 110.0, "ru:motorway": 110.0,
    }
    if s in _zones:
        return _zones[s]

    # Handle mph
    if "mph" in s:
        try:
            return float(s.replace("mph", "")) * 1.60934
        except ValueError:
            return None

    s = s.replace("km/h", "").replace("kmh", "")
    try:
        return float(s)
    except ValueError:
        return None


def conflict_weight(maxspeed_kmh: float | None, highway: str) -> float:
    """
    Map road speed / type to conflict weight.
    Design doc: 1.5 if >60 km/h, 1.2 if 40–60 km/h, 1.0 otherwise.
    """
    if maxspeed_kmh is not None:
        if maxspeed_kmh > 60:
            return 1.5
        if maxspeed_kmh >= 40:
            return 1.2
        return 1.0

    # Fallback: highway type heuristic (no maxspeed tag in OSM)
    FAST   = {"motorway", "trunk", "motorway_link", "trunk_link"}
    MEDIUM = {"primary", "secondary", "tertiary",
              "primary_link", "secondary_link", "tertiary_link",
              "unclassified"}
    hw = str(highway).lower()
    if hw in FAST:
        return 1.5
    if hw in MEDIUM:
        return 1.2
    return 1.0   # residential, living_street, service …


def has_cycling_infra(edge_attrs: dict) -> bool:
    """Return True if the OSM edge has dedicated cycling infrastructure."""
    CYCLEWAY_TAGS = [
        "cycleway", "cycleway:left", "cycleway:right", "cycleway:both",
        "cycleway:lane", "cycleway:track",
    ]
    EXCLUDE_VALS = {None, "no", "none", "None", "false", ""}
    for tag in CYCLEWAY_TAGS:
        v = edge_attrs.get(tag)
        if v not in EXCLUDE_VALS:
            return True
    hw = str(edge_attrs.get("highway", "")).lower()
    if hw in {"cycleway", "path"}:
        bicycle = str(edge_attrs.get("bicycle", "")).lower()
        if bicycle in ("yes", "designated", ""):
            return True
    return False


# ── Step 1: density map ────────────────────────────────────────────────────────

def build_density_map(trips_path: str) -> dict[str, int]:
    """Count GPS points per H3 cell across all trips."""
    print("Building H3 density map ...")
    density: dict[str, int] = defaultdict(int)
    with open(trips_path, encoding="utf-8") as f:
        features = json.load(f)["features"]

    total_points = 0
    for feat in features:
        coords = feat["geometry"]["coordinates"]   # [[lon, lat], ...]
        for lon, lat in coords:
            cell = h3.latlng_to_cell(lat, lon, RESOLUTION)
            density[cell] += 1
            total_points += 1

    print(f"  {total_points:,} GPS points -> {len(density):,} unique H3 cells"
          f" (resolution {RESOLUTION})")
    return dict(density)


# ── Step 2: edge GeoDataFrame ──────────────────────────────────────────────────

def load_edge_gdf(graph_path: str) -> gpd.GeoDataFrame:
    """
    Load the OSM drive graph and return a GeoDataFrame of edges with
    columns: geometry, maxspeed_kmh, highway, has_infra, weight.
    """
    print("Loading road network for spatial join ...")
    G = ox.load_graphml(graph_path)
    edges = ox.graph_to_gdfs(G, nodes=False)   # geopandas GeoDataFrame

    # Parse maxspeed
    edges["maxspeed_kmh"] = edges.get("maxspeed", None)
    if "maxspeed" in edges.columns:
        edges["maxspeed_kmh"] = edges["maxspeed"].apply(
            lambda v: parse_maxspeed(v[0] if isinstance(v, list) else v)
        )
    else:
        edges["maxspeed_kmh"] = None

    edges["highway_str"] = edges["highway"].apply(
        lambda v: v[0] if isinstance(v, list) else str(v)
    )

    edges["conflict_w"] = edges.apply(
        lambda row: conflict_weight(row["maxspeed_kmh"], row["highway_str"]),
        axis=1,
    )

    # Check cycling infrastructure per edge
    edges["has_infra"] = edges.apply(
        lambda row: has_cycling_infra(row.to_dict()), axis=1
    )

    print(f"  {len(edges):,} edges loaded")
    infra_count = edges["has_infra"].sum()
    print(f"  Cycling infra edges: {infra_count:,} ({infra_count/len(edges)*100:.1f}%)")
    return edges


# ── Step 3: hex analysis ───────────────────────────────────────────────────────

def analyse_hexes(
    density: dict[str, int],
    edges: gpd.GeoDataFrame,
    density_pct: int = DENSITY_PCT,
) -> list[dict]:
    """
    For each high-density hex:
      - Build its polygon
      - Spatial join to find intersecting edges
      - Compute infra_score and dominant conflict_weight
      - Return list of hex record dicts
    """
    counts = np.array(list(density.values()))
    threshold = float(np.percentile(counts, density_pct))
    print(f"\nDensity P{density_pct} threshold: {threshold:.0f} visits")

    high_density_cells = {
        cell: cnt for cell, cnt in density.items() if cnt >= threshold
    }
    print(f"High-density cells: {len(high_density_cells):,} / {len(density):,}")

    # Build GeoDataFrame of candidate hex polygons
    rows = []
    for cell, cnt in high_density_cells.items():
        # h3.cell_to_boundary returns list of (lat, lon) — convert to (lon, lat) for Shapely
        boundary_latlon = h3.cell_to_boundary(cell)
        polygon = Polygon([(lon, lat) for lat, lon in boundary_latlon])
        rows.append({"h3_cell": cell, "visit_count": cnt, "geometry": polygon})

    hex_gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")

    # Spatial join: find edges intersecting each hex
    print("Running spatial join (edges x hexes) ...")
    joined = gpd.sjoin(
        hex_gdf,
        edges[["geometry", "conflict_w", "has_infra"]],
        how="left",
        predicate="intersects",
    )

    # Aggregate per hex
    results = []
    for cell, group in joined.groupby("h3_cell"):
        visit_count = group["visit_count"].iloc[0]

        valid = group.dropna(subset=["conflict_w"])
        if len(valid) == 0:
            # No edges found in hex (unlikely) — use defaults
            infra_score  = 0
            dom_weight   = 1.0
        else:
            infra_score  = int(valid["has_infra"].any())
            dom_weight   = float(valid["conflict_w"].max())

        visit_count = int(visit_count)
        severity = visit_count * dom_weight

        results.append({
            "h3_cell":       cell,
            "visit_count":   visit_count,
            "infra_score":   infra_score,
            "conflict_weight": dom_weight,
            "severity":      round(severity, 2),
            "is_blind_spot": infra_score == 0,
        })

    return results


# ── Step 4: GeoJSON export ─────────────────────────────────────────────────────

def hex_to_geojson_feature(rec: dict, rank: int | None = None) -> dict:
    """Convert a hex record to a GeoJSON Feature with H3 polygon geometry."""
    boundary_latlon = h3.cell_to_boundary(rec["h3_cell"])
    coords_lonlat = [[lon, lat] for lat, lon in boundary_latlon]
    coords_lonlat.append(coords_lonlat[0])   # close the ring

    centroid_lat, centroid_lon = h3.cell_to_latlng(rec["h3_cell"])

    props = {
        **rec,
        "centroid_lon": round(centroid_lon, 6),
        "centroid_lat": round(centroid_lat, 6),
    }
    if rank is not None:
        props["rank"] = rank

    return {
        "type": "Feature",
        "geometry": {
            "type":        "Polygon",
            "coordinates": [coords_lonlat],
        },
        "properties": props,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()

    # ── 1. Density map ─────────────────────────────────────────────────────────
    density = build_density_map(TRIPS_PATH)

    # ── 2. Edge GeoDataFrame ───────────────────────────────────────────────────
    edges = load_edge_gdf(GRAPH_PATH)

    # ── 3. Hex analysis ────────────────────────────────────────────────────────
    hex_records = analyse_hexes(density, edges)

    blind_spots = [r for r in hex_records if r["is_blind_spot"]]
    blind_spots.sort(key=lambda r: r["severity"], reverse=True)
    top_blind   = blind_spots[:TOP_N]

    # ── 4. All-hexes GeoJSON (density heatmap) ─────────────────────────────────
    all_features = []
    for cell, cnt in density.items():
        boundary = h3.cell_to_boundary(cell)
        coords   = [[lon, lat] for lat, lon in boundary]
        coords.append(coords[0])
        all_features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {"h3_cell": cell, "visit_count": cnt},
        })

    with open(OUT_ALL, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": all_features},
                  f, ensure_ascii=False, separators=(",", ":"))

    # ── 5. Top-10 blind spots GeoJSON ─────────────────────────────────────────
    top_features = [
        hex_to_geojson_feature(rec, rank=i + 1)
        for i, rec in enumerate(top_blind)
    ]
    with open(OUT_BLIND, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": top_features},
                  f, indent=2, ensure_ascii=False)

    # ── 6. Print results ───────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'='*58}")
    print("ALGORITHM B — BLIND SPOT CLASSIFICATION RESULTS")
    print(f"{'='*58}")
    print(f"Total hexes visited      : {len(density):,}")
    print(f"High-density hexes (P75) : {len(hex_records):,}")
    print(f"Blind spots (no infra)   : {len(blind_spots):,}")
    print(f"  of which top-{TOP_N} exported")
    print()
    print(f"{'Rank':<5} {'H3 Cell':<16} {'Visits':>7} {'Infra':>6}"
          f" {'CW':>5} {'Severity':>9}")
    print("-" * 58)
    for i, rec in enumerate(top_blind, 1):
        print(f"  {i:<4} {rec['h3_cell']:<16} {rec['visit_count']:>7}"
              f" {rec['infra_score']:>6} {rec['conflict_weight']:>5.1f}"
              f" {rec['severity']:>9.1f}")
    print()
    print(f"Runtime  : {elapsed:.1f}s")
    print(f"{'='*58}")
    print(f"\nOutputs:")
    print(f"  {OUT_BLIND}")
    print(f"  {OUT_ALL}")


if __name__ == "__main__":
    main()
