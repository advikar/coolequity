"""Phase 5 — fuse every layer into one priority score, and write the app's data.

    base_risk = 0.35*heat + 0.25*(1-green) + 0.25*(1-ac) + 0.15*age65
    priority  = base_risk * (0.55 + 0.45*population)
    score     = 100 * minmax(priority)

Every input is min-max normalised *within the city* before it enters the sum.
That is the portability argument: 44 C is an ordinary afternoon in Phoenix and an
emergency in Seattle, so an absolute threshold would rank cities, not
neighborhoods. Weights live in config.py — a judge will ask why 35%.

Reads grid.geojson + satellite.csv + census.csv + overlays.csv.
Writes data/la.geojson — the one file the front end loads.
"""
import json
import sys

import numpy as np
import pandas as pd

import config as C

# The front end reads exactly these. Renaming one breaks the UI silently —
# MapLibre just paints a hex the no-data colour and moves on.
CONTRACT = ["id", "name", "lst", "green", "pop", "pct65", "ac", "holc",
            "access_min", "access_km", "score", "rank", "area_m2", "street_m",
            "canopy_m2", "row_m2", "row_canopy", "veg"]

COORD_DP = 5      # ~1 m at this latitude; halves the file the browser downloads


def log(msg):
    print(msg, flush=True)


def minmax(s):
    lo, hi = s.min(), s.max()
    if not np.isfinite(lo) or hi == lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


# One-sided percentile clip for the SCORING inputs. Raw min-max lets a single
# benign outlier set the scale (one 92%-canopy hex flattens the "missing canopy"
# term; a few huge-population hexes pin the multiplier near its floor). We pull in
# only the LEAST-need tail so it stops setting the scale, and never blunt the
# most-in-need tail — the hottest, oldest and barest blocks are what the tool must
# rank. Which end is benign is read off the score formula: protective inputs enter
# as (1-n) so their HIGH end is low-need; risk inputs enter as n so their LOW end
# is. Population is a saturating multiplier and is clipped at the crowded end.
# Endpoints go into the geojson so the front end normalises against them exactly.
CLIP_LO_Q, CLIP_HI_Q = 2.0, 98.0


def clip_bounds(s, clip_high):
    if clip_high:
        lo, hi = float(s.min()), float(np.percentile(s, CLIP_HI_Q))
    else:
        lo, hi = float(np.percentile(s, CLIP_LO_Q)), float(s.max())
    if not np.isfinite(lo) or hi <= lo:
        lo, hi = float(s.min()), float(s.max())
    return lo, hi


def clip_minmax(s, bounds):
    lo, hi = bounds
    if hi <= lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return ((s - lo) / (hi - lo)).clip(0.0, 1.0)


def shrink_age65(pop, pct65):
    """Empirical-Bayes smoothing of the 65+ share toward the citywide rate."""
    pop65 = pop * pct65 / 100.0
    city = pop65.sum() / pop.sum()               # citywide rate, 0..1
    k = C.AGE65_SHRINK_POP
    return (pop65 + k * city) / (pop + k) * 100.0


def round_coords(geom):
    return [[[round(x, COORD_DP), round(y, COORD_DP)] for x, y in ring]
            for ring in geom["coordinates"]]


def load():
    grid = json.loads(C.GRID_FILE.read_text())
    props = pd.DataFrame([f["properties"] for f in grid["features"]])

    df = props
    for path in (C.SAT_CSV, C.CENSUS_CSV, C.OVERLAYS_CSV):
        if not path.exists():
            raise SystemExit(
                f"\nMissing {path.relative_to(C.ROOT)}.\n"
                f"Run the pipeline in order: 01, 02, 03, 04, then 05."
            )
        df = df.merge(pd.read_csv(path), on="h3", how="left")

    # MEASURED canopy replaces the NDVI proxy at source, AFTER satellite.csv has
    # supplied green_pct, so the score, the output and every log line downstream
    # all read one number. `green_pct` keeps its name — it is the pipeline<->app
    # contract — but stops meaning "greenness" and starts meaning "ground under
    # vegetation at least 2 m tall".
    #
    # This is a correction, not a refinement. On San Ramon the NDVI proxy put
    # canopy at 21.2% of the ground; the canopy-height model puts it at 11.2%.
    # NDVI cannot tell an irrigated lawn from an oak, and in a summer-dry
    # climate that is most of the difference.
    if C.CANOPY_CSV.exists():
        df = df.merge(pd.read_csv(C.CANOPY_CSV), on="h3", how="left")
        have = df["canopy_pct"].notna()
        log(f"  canopy: MEASURED for {int(have.sum())}/{len(df)} hexes from a "
            f"canopy-height model; NDVI proxy retained where absent")
        # Keep the NDVI figure as `veg`. It is not a worse canopy measure — it
        # is a measure of something else: TOTAL photosynthesising ground, trees
        # plus lawn plus shrub. Both cool, and independently: holding the other
        # constant, canopy correlates with surface heat at -0.807 and non-tree
        # vegetation at -0.649. The difference between the two is the useful
        # part, because "already irrigated, no shade" is where a tree is
        # cheapest to plant and likeliest to survive.
        df["veg_pct"] = df["green_pct"]
        df["green_pct"] = df["canopy_pct"].where(have, df["green_pct"])
    else:
        log("  canopy: no canopy CSV — using the NDVI proxy, which overstates "
            "tree cover roughly 2x. Run 02c_canopy.py.")

    missing = df["lst_c"].isna().sum() + df["pop"].isna().sum()
    if missing:
        raise SystemExit(f"\n{missing} hexes missing inputs — rerun 02/03/04.")
    return grid, df


def main():
    log(f"Phase 5 — score | {C.CITY}")
    grid, df = load()
    log(f"  merged: {len(df)} hexes x {len(df.columns)} fields")

    keep = df["pop"] >= C.MIN_POP
    log(f"  dropping {(~keep).sum()} uninhabited hexes (pop < {C.MIN_POP:g}) "
        f"— ocean and forest, see config.MIN_POP")
    df = df[keep].reset_index(drop=True)

    df["pct65_s"] = shrink_age65(df["pop"], df["pct65"])
    log(f"  pct65: raw max {df.pct65.max():.1f}% -> smoothed "
        f"{df.pct65_s.max():.1f}% (median {df.pct65_s.median():.1f}%)")

    # p2/p98 endpoints per scoring input, reused by the app (keyed by the
    # property the front end reads). clip_high on the protective inputs and on
    # population; heat and age keep their true maximum.
    bounds = {
        "lst":   clip_bounds(df["lst_c"],     clip_high=False),
        "green": clip_bounds(df["green_pct"], clip_high=True),
        "ac":    clip_bounds(df["ac_est"],    clip_high=True),
        "pct65": clip_bounds(df["pct65_s"],   clip_high=False),
        "pop":   clip_bounds(df["pop"],       clip_high=True),
    }
    log("  score inputs clipped to p2/p98: " + ", ".join(
        f"{k} {lo:.1f}-{hi:.1f}" for k, (lo, hi) in bounds.items()))
    n = pd.DataFrame({
        "heat":  clip_minmax(df["lst_c"], bounds["lst"]),
        "green": clip_minmax(df["green_pct"], bounds["green"]),
        "ac":    clip_minmax(df["ac_est"], bounds["ac"]),
        "age65": clip_minmax(df["pct65_s"], bounds["pct65"]),
        "pop":   clip_minmax(df["pop"], bounds["pop"]),
    })

    W = C.WEIGHTS
    base = (W["heat"] * n["heat"]
            + W["green"] * (1 - n["green"])
            + W["ac"] * (1 - n["ac"])
            + W["age65"] * n["age65"])
    priority = base * (C.POP_FLOOR + C.POP_WEIGHT * n["pop"])

    df["score"] = 100 * minmax(priority)
    # Rank the unrounded priority: rounding score to 1dp first would manufacture
    # ties and hand the demo two hexes both labelled #1.
    df["rank"] = priority.rank(method="dense", ascending=False).astype(int)

    df["access_min"] = df["access_min"].fillna(df["access_min"].median())
    df["access_km"] = df["access_km"].fillna(df["access_km"].median())

    out = pd.DataFrame({
        "id":         df["id"].astype(int),
        "name":       df["name"].fillna("Unnamed"),
        "lst":        df["lst_c"].round(2),
        "green":      df["green_pct"].round(2),
        # Total vegetation from NDVI. `veg` minus `green` is non-tree ground.
        "veg":        (df["veg_pct"] if "veg_pct" in df.columns
                       else df["green_pct"]).round(1),
        "canopy_m2":  (df["canopy_m2"] if "canopy_m2" in df.columns
                       else df["green_pct"] / 100 * df["area_m2"]).round(0),
        # Plantable public ground: street right-of-way not already shaded. The
        # one figure here that describes what the CITY can do, as opposed to
        # what the block needs.
        "row_m2":     (df["row_m2"] if "row_m2" in df.columns
                       else pd.Series(0, index=df.index)).fillna(0).round(0),
        "row_canopy": (df["row_canopy_pct"] if "row_canopy_pct" in df.columns
                       else pd.Series(0.0, index=df.index)).fillna(0).round(1),
        "pop":        df["pop"].round(0).astype(int),
        "pct65":      df["pct65_s"].round(1),
        # 2dp, not 1: measured A/C is nearly uniform in hot cities, so its clip
        # range is narrow and 1dp rounding blows up the app's live-score parity.
        "ac":         df["ac_est"].round(2),
        "holc":       df["holc"],
        "access_min": df["access_min"].round(1),
        "access_km":  df["access_km"].round(2),
        "score":      df["score"].round(1),
        "rank":       df["rank"],
        "area_m2":    df["area_m2"].round(0).astype(int),
        # Metres of city-plantable street centreline. Not scored — it answers
        # "can the city act here?", which is a different question from
        # "should it?", and mixing the two would let good access paper over
        # real need.
        "street_m":   df["street_m"].fillna(0).round(0).astype(int),
    })[CONTRACT]

    by_id = {int(r["id"]): r for r in out.to_dict("records")}
    feats = []
    for f in grid["features"]:
        p = by_id.get(f["properties"]["id"])
        if p is None:
            continue
        # NaN is not JSON; holc is legitimately absent outside the 1939 map.
        p = {k: (None if isinstance(v, float) and np.isnan(v) else v)
             for k, v in p.items()}
        feats.append({"type": "Feature", "properties": p,
                      "geometry": {"type": "Polygon",
                                   "coordinates": round_coords(f["geometry"])}})

    # p2/p98 endpoints the front end normalises against to reproduce this rank.
    norm = {k: [round(lo, 4), round(hi, 4)] for k, (lo, hi) in bounds.items()}
    C.OUT_FILE.write_text(json.dumps({"type": "FeatureCollection",
                                      "norm": norm, "features": feats}))

    log(f"  score: {out.score.min():.1f}–{out.score.max():.1f} "
        f"(median {out.score.median():.1f})")
    log(f"  pop_n: median {n['pop'].median():.3f} — population multiplier spans "
        f"{C.POP_FLOOR:.2f}–{C.POP_FLOOR + C.POP_WEIGHT:.2f}")
    graded = out["holc"].notna().sum()
    log(f"  holc:  {graded}/{len(out)} graded")
    log(f"  wrote {C.OUT_FILE.relative_to(C.ROOT)} "
        f"({len(feats)} hexes, {C.OUT_FILE.stat().st_size/1e6:.1f} MB)")

    log("\n  Top 10 priority hexes")
    top = out.nsmallest(10, "rank")
    for _, r in top.iterrows():
        log(f"    #{r['rank']:<3d} {r['score']:5.1f}  {r['name'][:34]:<34s} "
            f"{r['lst']:.1f}C  {r['green']:4.1f}% green  "
            f"{r['pop']:6,d} people  {r['access_min']:5.1f} min  "
            f"HOLC {r['holc'] or '-'}")

    # The redlining claim in the demo script is a factual assertion about this
    # dataset. Check it here rather than discovering it is false on stage.
    if graded:
        g = out.dropna(subset=["holc"]).groupby("holc")
        log("\n  HOLC grade vs. today (the Section 10 story beat)")
        for grade, sub in g:
            log(f"    {grade}: {len(sub):4d} hexes  {sub.lst.mean():.1f}C  "
                f"{sub.green.mean():4.1f}% green  {sub.access_min.mean():5.1f} min  "
                f"score {sub.score.mean():.1f}")

    if out["rank"].min() != 1:
        log("  WARNING: no rank-1 hex — ranking is broken", file=sys.stderr)


if __name__ == "__main__":
    main()
