"""Phase 4 — the story overlays, plus the names the demo actually talks in.

Three things the score itself can't say:
  * HOLC redlining grade  — why the map looks the way it does (US-only)
  * cooling centers       — where relief already exists
  * walk time to relief   — the access gap, which is the intervention argument

...and one thing the demo can't do without: a human name per hex. H3 cells have
none, and "Hex 2417 is the hottest place in LA" persuades nobody. Names come from
OSM place nodes rather than a US neighborhood file, because OSM has them for
Lagos and Delhi too — same reason the grid is H3 and not census tracts.

Fallback chain, per layer:
  1. live fetch (Mapping Inequality / Overpass)  ->  cached to data/*.geojson
  2. the committed data/*.geojson                ->  fully offline
  3. HOLC/names degrade to null; centers hard-stop (the access layer needs them)

Writes data/overlays.csv: h3, name, holc, access_min, access_km.
"""
import json
import math
import sys
import time

import numpy as np
import pandas as pd
import requests

import config as C

OUT_CSV = C.DATA / "overlays.csv"
UA = {"User-Agent": "CoolEquity/0.1 (hackathon heat-equity mapper)"}

# south,west,north,east — Overpass's bbox order, not GeoJSON's.
OQL_BBOX = f"{C.BBOX[1]},{C.BBOX[0]},{C.BBOX[3]},{C.BBOX[2]}"

# What counts as somewhere you can go to escape the heat. Libraries and
# community/rec centers are what US cities actually designate; public pools and
# splash parks are the informal version. Deliberately excludes private pools,
# which LA has tens of thousands of and which help nobody without one.
CENTERS_OQL = f"""[out:json][timeout:{C.OVERPASS_TIMEOUT_S}];
(
  nwr["amenity"="library"]({OQL_BBOX});
  nwr["amenity"="community_centre"]({OQL_BBOX});
  nwr["amenity"="public_bath"]({OQL_BBOX});
  nwr["amenity"="social_facility"]["social_facility"="shelter"]({OQL_BBOX});
  nwr["amenity"="social_facility"]["social_facility:for"~"senior"]({OQL_BBOX});
  nwr["leisure"="swimming_pool"]["access"~"^(yes|public|permissive|customers)$"]({OQL_BBOX});
  nwr["leisure"="water_park"]({OQL_BBOX});
);
out center;"""

PLACES_OQL = f"""[out:json][timeout:{C.OVERPASS_TIMEOUT_S}];
(
  node["place"~"^(neighbourhood|suburb|quarter|borough|city|town|village)$"]["name"]({OQL_BBOX});
);
out center;"""

# NB: `out center`, never `out ... tags`. The `tags` verbosity prints ids and
# tags and *drops the coordinates*, including on plain nodes — which fails
# silently here, as every element parses fine and then has nowhere to be put.

OCTANTS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------- fetching
def overpass(oql, label):
    """Run an Overpass query against the first mirror that answers.

    Public instances rate-limit and go down, and a 504 from one usually means
    you are the load — hence the pause between rounds rather than an immediate
    retry. A demo that depends on exactly one instance is a demo that fails at
    the venue.
    """
    last = None
    for attempt in range(C.OVERPASS_ROUNDS):
        if attempt:
            log(f"    {label}: all mirrors busy — backing off "
                f"{C.OVERPASS_BACKOFF_S}s")
            time.sleep(C.OVERPASS_BACKOFF_S)
        for url in C.OVERPASS_MIRRORS:
            host = url.split("/")[2]
            try:
                log(f"    {label}: querying {host}...")
                r = requests.post(url, data={"data": oql}, headers=UA,
                                  timeout=C.OVERPASS_TIMEOUT_S + 30)
                r.raise_for_status()
                return r.json()["elements"]
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
                log(f"    {host} failed ({last})")
    raise RuntimeError(f"all Overpass mirrors failed — last: {last}")


def cached(path, build, label, refresh):
    """Committed copy first, else live fetch, else None. Never fatal here.

    Cache-first — the opposite of 02_satellite.py, on purpose. The STAC catalog
    does not care how often you ask; Overpass does, and re-pulling 645 amenities
    on every tweak of the scoring code is how you get rate-limited an hour
    before the demo. `--refresh` when you actually want new data.
    """
    if path.exists() and not refresh:
        gj = json.loads(path.read_text())
        log(f"  {label}: cached {path.name} ({len(gj['features'])} features) "
            f"— --refresh to re-pull")
        return gj
    try:
        gj = build()
        n = len(gj["features"])
        if n == 0:
            raise RuntimeError("query returned nothing")
        path.write_text(json.dumps(gj))
        log(f"  {label}: {n} live -> cached {path.name}")
        return gj
    except Exception as e:
        log(f"  {label}: live fetch failed ({type(e).__name__}: {e})")
        if path.exists():
            gj = json.loads(path.read_text())
            log(f"  {label}: using committed {path.name} "
                f"({len(gj['features'])} features)")
            return gj
        log(f"  {label}: NO CACHE at {path.name}")
        return None


def osm_point(el):
    """Node coords, or the `out center` centroid for a way/relation."""
    if "lat" in el:
        return el["lon"], el["lat"]
    ctr = el.get("center")
    return (ctr["lon"], ctr["lat"]) if ctr else None


def kind_of(tags):
    if tags.get("amenity") == "library":
        return "library"
    if tags.get("amenity") == "community_centre":
        return "community_centre"
    if tags.get("amenity") == "social_facility":
        return "shelter/senior"
    if tags.get("leisure") in ("swimming_pool", "water_park"):
        return "pool"
    return "public_bath"


def check_coords(els, label):
    """Guard the `out center` contract — see the note by the queries above."""
    bad = sum(1 for e in els if osm_point(e) is None)
    if bad:
        raise RuntimeError(
            f"{label}: {bad}/{len(els)} elements came back without coordinates "
            "— the `out` mode dropped them"
        )
    return els


def fetch_centers():
    feats, seen = [], set()
    for el in check_coords(overpass(CENTERS_OQL, "cooling centers"), "centers"):
        pt = osm_point(el)
        # A pool inside a rec center is often mapped as both a node and a way;
        # round to ~10 m so the pair collapses to one marker.
        key = (round(pt[0], 4), round(pt[1], 4))
        if key in seen:
            continue
        seen.add(key)
        tags = el.get("tags", {})
        feats.append({
            "type": "Feature",
            "properties": {
                "kind": kind_of(tags),
                "name": tags.get("name", "Unnamed cooling site"),
            },
            "geometry": {"type": "Point", "coordinates": [round(pt[0], 5),
                                                          round(pt[1], 5)]},
        })
    return {"type": "FeatureCollection", "features": feats}


def fetch_places():
    feats = []
    for el in check_coords(overpass(PLACES_OQL, "place names"), "places"):
        pt = osm_point(el)
        tags = el.get("tags", {})
        feats.append({
            "type": "Feature",
            "properties": {"name": tags["name"], "place": tags.get("place", "")},
            "geometry": {"type": "Point", "coordinates": [round(pt[0], 5),
                                                          round(pt[1], 5)]},
        })
    return {"type": "FeatureCollection", "features": feats}


def fetch_holc():
    r = requests.get(C.HOLC_URL, headers=UA, timeout=90)
    r.raise_for_status()
    gj = r.json()
    # One LA polygon carries a null grade; an ungraded area is not a category.
    gj["features"] = [f for f in gj["features"]
                      if f.get("geometry") and f["properties"].get("grade")
                      in ("A", "B", "C", "D")]
    return gj


# -------------------------------------------------------------------- joins
def holc_grades(hexes, holc_gj):
    """Majority-overlap HOLC grade per hex, or null where the map didn't reach.

    Majority by *area*, not by centroid hit: a hex straddling a C/D boundary
    should read as whichever dominates, and centroid sampling would coin-flip it.
    """
    import geopandas as gpd
    holc = gpd.GeoDataFrame.from_features(holc_gj["features"], crs="EPSG:4326")
    # The 1930s scans digitise with self-intersections here and there; overlay
    # refuses to run on those.
    holc["geometry"] = holc.geometry.make_valid()
    holc = holc[holc.geometry.geom_type.isin(("Polygon", "MultiPolygon"))]
    holc = holc[["grade", "geometry"]].to_crs(C.RASTER_CRS)

    inter = gpd.overlay(hexes[["h3", "geometry"]], holc,
                        how="intersection", keep_geom_type=True)
    inter["a"] = inter.geometry.area
    by = inter.groupby(["h3", "grade"], as_index=False)["a"].sum()

    top = by.sort_values("a").drop_duplicates("h3", keep="last")
    cover = by.groupby("h3")["a"].sum()
    area = hexes.set_index("h3").geometry.area

    top = top.set_index("h3")
    frac = (cover / area).reindex(top.index)
    graded = top["grade"].where(frac >= C.HOLC_MIN_COVER)
    return graded.reindex(hexes["h3"].values).values


def access_time(hexes, centers_gj):
    """Walking minutes and km from each hex centroid to the nearest cooling site.

    Circuity-adjusted straight line (see C.CIRCUITY) — an estimate, not a route.
    """
    import geopandas as gpd
    from shapely.geometry import shape

    pts = gpd.GeoDataFrame(
        geometry=[shape(f["geometry"]) for f in centers_gj["features"]],
        crs="EPSG:4326",
    ).to_crs(C.RASTER_CRS)

    cent = gpd.GeoDataFrame({"h3": hexes["h3"].values},
                            geometry=hexes.geometry.centroid, crs=hexes.crs)
    near = gpd.sjoin_nearest(cent, pts, how="left", distance_col="m")
    # sjoin_nearest emits one row per tie; a hex equidistant from two centers
    # would otherwise duplicate downstream.
    near = near.drop_duplicates("h3").set_index("h3").reindex(hexes["h3"].values)

    km = near["m"].values / 1000.0 * C.CIRCUITY
    return km / C.WALK_SPEED_KMH * 60.0, km


def octant(dx, dy):
    ang = math.degrees(math.atan2(dx, dy)) % 360      # 0 = due north
    return OCTANTS[int((ang + 22.5) // 45) % 8]


def hex_names(hexes, places_gj):
    """Name each hex after the nearest OSM place node.

    Dozens of hexes fall inside one neighborhood, so the nearest hex keeps the
    bare name and the rest get a compass suffix — "Van Nuys" vs "Van Nuys SE".
    The ranked list is read aloud in the demo; two identical rows would be worse
    than a slightly clumsy one.
    """
    import geopandas as gpd
    from shapely.geometry import shape

    pl = gpd.GeoDataFrame(
        {"pname": [f["properties"]["name"] for f in places_gj["features"]]},
        geometry=[shape(f["geometry"]) for f in places_gj["features"]],
        crs="EPSG:4326",
    ).to_crs(C.RASTER_CRS)

    cent = gpd.GeoDataFrame({"h3": hexes["h3"].values},
                            geometry=hexes.geometry.centroid, crs=hexes.crs)
    near = gpd.sjoin_nearest(cent, pl, how="left", distance_col="m")
    near = near.drop_duplicates("h3").reset_index(drop=True)

    px = pl.geometry.x.values[near["index_right"].values]
    py = pl.geometry.y.values[near["index_right"].values]
    near["oct"] = [octant(x - ax, y - ay) for x, y, ax, ay
                   in zip(near.geometry.x, near.geometry.y, px, py)]

    labels, used = {}, set()
    for pname, grp in near.sort_values("m").groupby("pname", sort=False):
        for i, (_, row) in enumerate(grp.iterrows()):
            base = pname if i == 0 else f"{pname} {row['oct']}"
            label, n = base, 2
            while label in used:                       # same octant twice over
                label, n = f"{base} {n}", n + 1
            used.add(label)
            labels[row["h3"]] = label

    return pd.Series(labels).reindex(hexes["h3"].values).values


# --------------------------------------------------------------------- main
def main():
    import geopandas as gpd
    refresh = "--refresh" in sys.argv
    log(f"Phase 4 — overlays | {C.CITY}{' | --refresh' if refresh else ''}")
    hexes = gpd.read_file(C.GRID_FILE).to_crs(C.RASTER_CRS)
    log(f"  grid: {len(hexes)} hexes")

    centers = cached(C.CENTERS_FILE, fetch_centers, "centers", refresh)
    places = cached(C.PLACES_FILE, fetch_places, "places", refresh)
    holc = (cached(C.HOLC_FILE, fetch_holc, "HOLC", refresh)
            if C.COUNTRY == "USA" else None)

    if not centers or not centers["features"]:
        raise SystemExit(
            f"\nNo cooling centers and no cache at {C.CENTERS_FILE}.\n"
            "The access-gap layer is the intervention argument — refusing to "
            "invent one."
        )

    out = pd.DataFrame({"h3": hexes["h3"].values})

    out["name"] = (hex_names(hexes, places) if places else
                   [f"Hex {i}" for i in range(len(hexes))])
    if not places:
        log("  names: no place data — falling back to 'Hex N'")

    if holc:
        out["holc"] = holc_grades(hexes, holc)
        got = out["holc"].notna().sum()
        share = out["holc"].value_counts().to_dict()
        log(f"  HOLC: {got}/{len(out)} hexes graded {share}")
    else:
        out["holc"] = None
        log(f"  HOLC: skipped (COUNTRY={C.COUNTRY} — US-only layer)")

    mins, km = access_time(hexes, centers)
    out["access_min"] = np.round(mins, 1)
    out["access_km"] = np.round(km, 2)

    out.to_csv(OUT_CSV, index=False)
    log(f"  centers: {len(centers['features'])} sites")
    log(f"  access:  {out.access_min.min():.0f}–{out.access_min.max():.0f} min "
        f"(median {out.access_min.median():.0f}), circuity {C.CIRCUITY}")
    log(f"  names:   {out.name.nunique()} distinct, e.g. "
        f"{', '.join(out.name.head(3))}")
    log(f"  wrote {OUT_CSV.relative_to(C.ROOT)}")

    # Every hex is within ~1 km of somewhere in a city this dense; a citywide
    # median over an hour means the center list came back nearly empty.
    if out.access_min.median() > 60:
        log("  WARNING: median walk time looks implausible — check centers",
            file=sys.stderr)


if __name__ == "__main__":
    main()
