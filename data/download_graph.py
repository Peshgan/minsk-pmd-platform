"""
Download and cache the Minsk road network graph from OpenStreetMap.

Run once. After this, all other scripts load from minsk.graphml
without hitting the network.

Usage:
    python data/download_graph.py
"""

import os
import time
import osmnx as ox

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "minsk.graphml")

# Network type "drive" covers the roads e-scooters share with cars.
# "bike" would add cycleways but misses the conflict zones we care about.
NETWORK_TYPE = "drive"
CITY_QUERY = "Minsk, Belarus"


def download_and_cache():
    if os.path.exists(GRAPH_PATH):
        size_mb = os.path.getsize(GRAPH_PATH) / 1024 / 1024
        print(f"Graph already cached at {GRAPH_PATH} ({size_mb:.1f} MB). Skipping download.")
        return

    print(f"Downloading '{CITY_QUERY}' road network from OpenStreetMap...")
    print("This runs once and may take 1-3 minutes depending on your connection.\n")

    t0 = time.time()
    G = ox.graph_from_place(CITY_QUERY, network_type=NETWORK_TYPE)
    elapsed = time.time() - t0

    nodes, edges = len(G.nodes), len(G.edges)
    print(f"Downloaded in {elapsed:.1f}s — {nodes:,} nodes, {edges:,} edges")

    print(f"Saving to {GRAPH_PATH} ...")
    ox.save_graphml(G, GRAPH_PATH)
    size_mb = os.path.getsize(GRAPH_PATH) / 1024 / 1024
    print(f"Saved ({size_mb:.1f} MB). Future runs load from disk — no network needed.")


def verify_cache():
    """Quick sanity check: load the cached graph and print basic stats."""
    print(f"\nVerifying cache: loading from {GRAPH_PATH} ...")
    t0 = time.time()
    G = ox.load_graphml(GRAPH_PATH)
    elapsed = time.time() - t0
    nodes, edges = len(G.nodes), len(G.edges)
    print(f"Loaded in {elapsed:.1f}s — {nodes:,} nodes, {edges:,} edges")

    # Print CRS info so downstream scripts know the coordinate system
    crs = G.graph.get("crs", "unknown")
    print(f"CRS: {crs}")
    print("Cache OK — ready for synthetic trip generation.")
    return G


if __name__ == "__main__":
    download_and_cache()
    verify_cache()
