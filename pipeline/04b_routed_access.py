"""Phase 4b — routed pedestrian walk time to the nearest cooling site.

Why this replaces the straight-line estimate (DATA_QUALITY.md W-1)
-----------------------------------------------------------------
04's `access_time` is a circuity-adjusted straight line: crow-fly distance to the
nearest cooling site × C.CIRCUITY (1.273, the grid-Manhattan ratio) ÷ walk speed.
Its documented failure mode is that a hex one freeway, creek or ridgeline away from
a site reads "close" — the straight line ignores barriers, and a fixed circuity
factor cannot know that suburban San Ramon's winding cul-de-sacs are far more
circuitous than a grid.

This module routes on the real OSM **pedestrian network** instead:

  * `osmnx` builds the walk graph for the study bbox (a freeway with no sidewalk is
    simply not in it, so it cannot be crossed; a footbridge over a creek is);
  * one multi-source Dijkstra from every cooling site gives each graph node its
    true network distance to the nearest site (fast — one pass for the whole grid);
  * door-to-door: the point→graph-node snap distance is added at BOTH ends (hex
    centroid and cooling site), and the result is floored at the straight-line
    distance (you cannot walk less than crow-fly), which removes snapping artefacts.

It is computed ONCE, offline, and written into overlays_<slug>.csv, so nothing
routes at demo time. The downloaded graph is cached to
data/_cache/walkgraph_<slug>.graphml so a rerun needs no network.

Validation before trusting it (per DATA_QUALITY.md follow-up 3): the log reports
the largest-connected-component share (should be ~1.0), the routed/crow-fly ratio
distribution (must be ≥1.0 everywhere), and the count of hexes that fell back to
the straight line. Any hex the pedestrian network cannot reach keeps the
straight-line estimate and is marked access_src="straightline".

Run:  ../.venv/bin/python 04b_routed_access.py   (after 04 has written overlays)
"""
import sys
import numpy as np

import config as C

MARGIN_DEG = 0.02           # pull the graph a little past the bbox so edge hexes
                            # can route to a just-outside site and border routes
                            # are not artificially truncated
GRAPH_CACHE = C.CACHE / f"walkgraph_{C.SLUG}.graphml"


def log(msg):
    print(msg, flush=True)


def build_graph():
    import osmnx as ox
    if GRAPH_CACHE.exists():
        log(f"  walk graph: loading cache {GRAPH_CACHE.name}")
        return ox.load_graphml(GRAPH_CACHE)
    w, s, e, n = C.BBOX
    log(f"  walk graph: downloading OSM pedestrian network for bbox+{MARGIN_DEG}° "
        f"(~{(e-w)*88:.0f}×{(n-s)*111:.0f} km) — this is the slow step")
    G = ox.graph_from_bbox(bbox=(w - MARGIN_DEG, s - MARGIN_DEG,
                                 e + MARGIN_DEG, n + MARGIN_DEG),
                           network_type="walk")
    ox.save_graphml(G, GRAPH_CACHE)
    log(f"  walk graph: cached to {GRAPH_CACHE.relative_to(C.ROOT)}")
    return G


def routed_meters(grid, centers_gj):
    """Door-to-door network metres from each hex centroid to the nearest cooling
    site. Returns (routed_m, crow_m, stats dict). routed_m is NaN where the network
    cannot reach the hex (caller falls back to the straight line)."""
    import geopandas as gpd
    import networkx as nx
    import osmnx as ox
    from shapely.geometry import shape
    from scipy.spatial import cKDTree

    cen = gpd.GeoSeries(grid.geometry.centroid, crs=grid.crs).to_crs(C.RASTER_CRS)
    cpts = [shape(f["geometry"]) for f in centers_gj["features"]]
    cpt = gpd.GeoSeries(cpts, crs="EPSG:4326").to_crs(C.RASTER_CRS)

    G = build_graph()
    G = ox.project_graph(G, to_crs=C.RASTER_CRS)
    Gu = ox.convert.to_undirected(G)

    comps = sorted((len(c) for c in nx.connected_components(Gu)), reverse=True)
    lcc = comps[0] / Gu.number_of_nodes() if Gu.number_of_nodes() else 0
    log(f"  graph: {Gu.number_of_nodes()} nodes, {Gu.number_of_edges()} edges, "
        f"largest component {lcc:.3f} of nodes")

    hx_nodes, hx_snap = ox.distance.nearest_nodes(
        G, X=cen.x.values, Y=cen.y.values, return_dist=True)
    c_nodes, c_snap = ox.distance.nearest_nodes(
        G, X=cpt.x.values, Y=cpt.y.values, return_dist=True)

    # Virtual super-source joined to each cooling node with edge weight = that
    # site's snap distance, so a single Dijkstra returns, for every node, the
    # minimum over sites of (site_snap + network_distance). Gu is a MultiGraph, so
    # two sites snapping to one node just add parallel edges — Dijkstra takes the
    # smaller, which is exactly what we want; no manual dedup needed.
    SRC = "__cooling_src__"
    Gu.add_node(SRC)
    for nid, sd in zip(np.atleast_1d(c_nodes), np.atleast_1d(c_snap)):
        Gu.add_edge(SRC, nid, length=float(sd))
    dist = nx.single_source_dijkstra_path_length(Gu, SRC, weight="length")

    net = np.array([dist.get(nid, np.nan) for nid in np.atleast_1d(hx_nodes)])
    routed_m = net + np.asarray(hx_snap, dtype=float)   # + hex centroid snap

    tree = cKDTree(np.column_stack([cpt.x.values, cpt.y.values]))
    crow_m, _ = tree.query(np.column_stack([cen.x.values, cen.y.values]))
    # physical floor: a walk cannot be shorter than the straight line
    routed_m = np.where(np.isnan(routed_m), np.nan, np.maximum(routed_m, crow_m))

    ok = ~np.isnan(routed_m)
    ratio = routed_m[ok] / np.maximum(crow_m[ok], 1.0)
    stats = dict(lcc=lcc, reachable=int(ok.sum()), total=int(len(ok)),
                 ratio_med=float(np.median(ratio)) if ok.any() else float("nan"),
                 ratio_min=float(ratio.min()) if ok.any() else float("nan"),
                 ratio_p90=float(np.percentile(ratio, 90)) if ok.any() else float("nan"),
                 snap_p95=float(np.percentile(hx_snap, 95)))
    return routed_m, crow_m, stats


def main():
    import geopandas as gpd
    import pandas as pd
    import json

    log(f"Phase 4b — routed walk time | {C.CITY}")
    if not C.OVERLAYS_CSV.exists():
        raise SystemExit(f"\nNo {C.OVERLAYS_CSV.name}; run 04 first.")
    if not C.CENTERS_FILE.exists():
        raise SystemExit(f"\nNo {C.CENTERS_FILE.name}; run 04 first.")

    grid = gpd.read_file(C.GRID_FILE)[["h3", "geometry"]]
    centers = json.loads(C.CENTERS_FILE.read_text())
    log(f"  {len(grid)} hexes, {len(centers['features'])} cooling sites")

    routed_m, crow_m, st = routed_meters(grid, centers)
    log(f"  connectivity {st['lcc']:.3f} | reachable {st['reachable']}/{st['total']} "
        f"| routed/crow-fly ratio med {st['ratio_med']:.2f} min {st['ratio_min']:.2f} "
        f"p90 {st['ratio_p90']:.2f} | hex snap p95 {st['snap_p95']:.0f} m")
    if st["ratio_min"] < 0.999:
        raise SystemExit("  ABORT: routed < crow-fly somewhere — snapping bug, not shipping.")
    if st["lcc"] < 0.90:
        log("  !! WARNING: walk graph is fragmented (largest component < 90%); "
            "many hexes will fall back to the straight line. Review before shipping.")

    # Fall back to the straight-line estimate where the network cannot reach.
    straight_m = crow_m * C.CIRCUITY
    src = np.where(np.isnan(routed_m), "straightline", "routed")
    final_m = np.where(np.isnan(routed_m), straight_m, routed_m)
    km = final_m / 1000.0
    mins = km / C.WALK_SPEED_KMH * 60.0
    nfb = int((src == "straightline").sum())
    if nfb:
        log(f"  {nfb} hex(es) unreachable on foot — kept the straight-line estimate")

    ov = pd.read_csv(C.OVERLAYS_CSV)
    order = pd.Series(np.arange(len(grid)), index=grid["h3"].values)
    idx = ov["h3"].map(order)                    # align by h3, not row order
    ov["access_min"] = np.round(mins[idx.values], 1)
    ov["access_km"] = np.round(km[idx.values], 2)
    ov["access_src"] = src[idx.values]
    ov.to_csv(C.OVERLAYS_CSV, index=False)
    log(f"  access: median {np.median(mins):.1f} min, max {np.max(mins):.1f} min "
        f"(routed). wrote {C.OVERLAYS_CSV.relative_to(C.ROOT)}")
    log("  re-run 05_score.py to propagate into the geojson.")


if __name__ == "__main__":
    main()
