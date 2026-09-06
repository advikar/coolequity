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
            "access_min", "access_km", "score", "rank", "area_m2"]

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
    for name in ("satellite", "census", "overlays"):
        path = C.DATA / f"{name}.csv"
        if not path.exists():
            raise SystemExit(
                f"\nMissing {path.relative_to(C.ROOT)}.\n"
                f"Run the pipeline in order: 01, 02, 03, 04, then 05."
            )
        df = df.merge(pd.read_csv(path), on="h3", how="left")

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
        "pop":        df["pop"].round(0).astype(int),
        "pct65":      df["pct65_s"].round(1),
        "ac":         df["ac_est"].round(1),
        "holc":       df["holc"],
        "access_min": df["access_min"].round(1),
        "access_km":  df["access_km"].round(2),
        "score":      df["score"].round(1),
        "rank":       df["rank"],
        "area_m2":    df["area_m2"].round(0).astype(int),
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
