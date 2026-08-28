"""Phase 3 — population, age 65+, and a modeled A/C-access proxy per hex.

ACS 5-year block groups, area-weighted into the H3 grid. US-only by construction;
the global path for this layer is WorldPop + the Meta Relative Wealth Index.

Fallback chain:
  1. Census API + cartographic boundary file  ->  cached to data/acs.csv
  2. data/acs.csv                             ->  fully offline
  3. hard stop

Writes data/census.csv: h3, pop, pct65, income, ac_est.
"""
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd
import requests

import config as C

ACS_URL = f"https://api.census.gov/data/{C.ACS_YEAR}/acs/acs5"
BG_ZIP = (f"https://www2.census.gov/geo/tiger/GENZ{C.ACS_YEAR}/shp/"
          f"cb_{C.ACS_YEAR}_{C.STATE_FIPS}_bg_500k.zip")
BG_CACHE = C.CACHE / f"bg_{C.STATE_FIPS}.zip"
ACS_CSV = C.ACS_FILE                  # committed fallback
OUT_CSV = C.CENSUS_CSV

POP = "B01001_001E"
INCOME = "B19013_001E"
UNITS = "B25001_001E"   # total housing units — denominator for the dasymetric guard
# B01001 age brackets from 65 up, male then female.
AGE65 = [f"B01001_{n:03d}E" for n in (20, 21, 22, 23, 24, 25,
                                      44, 45, 46, 47, 48, 49)]


def log(msg):
    print(msg, flush=True)


def load_key():
    """Read CENSUS_API_KEY from the environment or the gitignored .env."""
    key = os.environ.get("CENSUS_API_KEY")
    if key:
        return key.strip()
    env = C.ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("CENSUS_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def fetch_acs():
    """Block-group ACS table for the target county. Cached to data/acs.csv."""
    key = load_key()
    params = {
        "get": ",".join([POP, INCOME, UNITS] + AGE65),
        "for": "block group:*",
        "in": f"state:{C.STATE_FIPS} county:{C.COUNTY_FIPS}",
    }
    if key:
        params["key"] = key
    else:
        log("  no CENSUS_API_KEY — trying unkeyed (rate-limited)")

    r = requests.get(ACS_URL, params=params, timeout=60)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])

    num = [POP, INCOME, UNITS] + AGE65
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    # ACS uses large negative sentinels (-666666666) for suppressed estimates.
    df[num] = df[num].mask(df[num] < -1e6)

    df["GEOID"] = (df["state"] + df["county"] + df["tract"] + df["block group"])
    df["pop"] = df[POP].fillna(0)
    df["pop65"] = df[AGE65].sum(axis=1, min_count=1).fillna(0)
    df["income"] = df[INCOME]
    df["units"] = df[UNITS].fillna(0)

    out = df[["GEOID", "pop", "pop65", "income", "units"]]
    out.to_csv(ACS_CSV, index=False)
    log(f"  ACS: {len(out)} block groups, pop {out['pop'].sum():,.0f} "
        f"-> cached {ACS_CSV.name}")
    return out


def load_block_groups():
    """Cartographic boundary block groups for the state, filtered to the county."""
    import geopandas as gpd
    if not BG_CACHE.exists():
        log(f"  downloading block-group geometry ({BG_ZIP.rsplit('/',1)[-1]})...")
        r = requests.get(BG_ZIP, timeout=180)
        r.raise_for_status()
        BG_CACHE.write_bytes(r.content)
    log(f"  geometry: {BG_CACHE.name} ({BG_CACHE.stat().st_size/1e6:.1f} MB)")
    gdf = gpd.read_file(f"zip://{BG_CACHE}")
    gdf = gdf[gdf["COUNTYFP"] == C.COUNTY_FIPS].copy()
    return gdf[["GEOID", "geometry"]].to_crs(C.RASTER_CRS)


def load_buildings():
    """Residential building centroids + floor area from 02b.

    Returns (all_buildings, city_buildings). Both are needed, and mixing them
    up is the easy way to get this wrong:

      * the DENOMINATOR (a block group's total housing) must use ALL buildings,
        including the ones outside the city limits, or a block group straddling
        the border assigns every one of its residents to its in-city half;
      * the NUMERATOR (housing inside a given hex) must use only in-city
        buildings, because hexes are kept if they *intersect* the boundary and
        so deliberately overhang into Danville, Dublin and Blackhawk.

    Optional on purpose: before 02b has been run, or outside the US, the
    pipeline still works — it falls back to area weighting and says so.
    """
    if not C.BUILDINGS_FILE.exists():
        return None, None
    import geopandas as gpd
    b = gpd.read_file(C.BUILDINGS_FILE).to_crs(C.RASTER_CRS)[["area_m2", "geometry"]]
    if not C.BOUNDARY_FILE.exists():
        return b, b
    city = gpd.read_file(C.BOUNDARY_FILE).to_crs(C.RASTER_CRS)
    inside = gpd.sjoin(b, city[["geometry"]], how="inner", predicate="within")
    return b, inside[["area_m2", "geometry"]]


def dasymetric_is_safe(city_buildings, bgs):
    """Is the building mask complete and unbiased enough to place people with?

    Two ways it can fail, and the second is the one that matters.

    COMPLETENESS: if OSM has mapped a third of the housing, floor area is a
    sample, not a census, and area weighting is the more honest estimator.

    BIAS: OSM is volunteer-mapped, and volunteers do not distribute themselves
    evenly across a county. If wealthy block groups are mapped better than poor
    ones -- and in Contra Costa they are, 4.7x better -- then weighting by
    mapped floor area moves residents from poor areas to rich ones. Population
    multiplies the priority score, so that would systematically demote exactly
    the neighbourhoods an equity tool exists to find. This check is the reason
    the county build does not use dasymetric placement.

    Returns (ok, reason).
    """
    import geopandas as gpd
    have = bgs[bgs["units"] > 0].copy()
    if have.empty:
        return False, "no housing-unit counts to check the mask against"

    hit = gpd.sjoin(city_buildings, have[["GEOID", "geometry"]],
                    how="inner", predicate="within")
    have["mapped"] = have["GEOID"].map(hit.groupby("GEOID").size()).fillna(0)

    cov = have["mapped"].sum() / have["units"].sum()
    log(f"    mask check: {have['mapped'].sum():,.0f} mapped buildings vs "
        f"{have['units'].sum():,.0f} ACS housing units = {cov:.2f} coverage")
    if cov < C.DASY_MIN_COVERAGE:
        return False, (f"coverage {cov:.2f} < {C.DASY_MIN_COVERAGE:.2f} — the mask "
                       f"is a sample, not a census")

    inc = have[have["income"].notna() & (have["income"] > 0)].copy()
    if len(inc) >= 40:
        inc["cov"] = inc["mapped"] / inc["units"]
        q = pd.qcut(inc["income"], 4, labels=False, duplicates="drop")
        lo, hi = inc.loc[q == 0, "cov"].median(), inc.loc[q == q.max(), "cov"].median()
        bias = (hi / lo) if lo > 0 else float("inf")
        log(f"    mask check: coverage by income quartile "
            f"{inc.groupby(q, observed=True)['cov'].median().round(2).tolist()} "
            f"-> richest/poorest = {bias:.1f}x")
        if bias > C.DASY_MAX_INCOME_BIAS:
            return False, (f"mask is {bias:.1f}x better in rich block groups than poor "
                           f"ones — weighting by it would demote poor neighbourhoods")
    return True, f"coverage {cov:.2f}, no material income bias"


def area_weight(hexes, bgs, buildings=None, city_buildings=None):
    """Split each block group's people across the hexes it overlaps.

    Two ways to do the split, and which one is used matters a lot at res 9.

    AREA weighting assumes people are spread evenly across a block group. That
    is the standard areal-interpolation assumption and it is fine at res 8,
    where a hex is 0.82 km2 and averages over whatever is inside it. At res 9
    (0.11 km2) it breaks: a block group that contains both an apartment complex
    and a golf course hands the golf course a proportional share of the
    residents. Measured on the first San Ramon build, that put >=50 phantom
    residents into each of 57 hexes with no housing in them at all -- 6.9% of
    the city -- and pushed one empty hex to #10 in the priority ranking.

    DASYMETRIC weighting splits by residential floor area instead, using the
    building footprints from 02b as the mask for where people can actually be.
    Same total population, placed where the housing is. Hexes with no housing
    get no residents, which is the correct answer rather than a small one.

    Falls back to area weighting per block group where no buildings are mapped,
    so a gap in OSM coverage loses those residents' precision but never deletes
    them -- the city total still reconciles against ACS.
    """
    import geopandas as gpd
    bgs = bgs.copy()
    bgs["bg_area"] = bgs.geometry.area

    inter = gpd.overlay(
        hexes[["h3", "geometry"]], bgs, how="intersection", keep_geom_type=True
    )

    # Clip every piece to the study boundary before measuring it. 01_make_grid
    # keeps any hex that *intersects* the boundary, so the grid deliberately
    # overhangs the city — and an unclipped area weight then hands those hexes a
    # share of residents who live outside it. Measured on Bakersfield: 457,733
    # people against an ACS place total of 408,366, a 12% overcount concentrated
    # on exactly the edge hexes a planner would question first. The dasymetric
    # path solves this by clipping the building mask; area weighting needs the
    # same treatment, and it is the path taken whenever the mask is too sparse.
    if C.BOUNDARY_FILE.exists():
        city = gpd.read_file(C.BOUNDARY_FILE).to_crs(inter.crs).geometry.union_all()
        before = inter.geometry.area.sum()
        inter["geometry"] = inter.geometry.intersection(city)
        inter = inter[~inter.geometry.is_empty]
        log(f"    clipped pieces to {C.CITY} limits: "
            f"{before/1e6:,.0f} -> {inter.geometry.area.sum()/1e6:,.0f} km2")

    inter["frac"] = inter.geometry.area / inter["bg_area"]

    if buildings is not None:
        inter = inter.reset_index(drop=True)
        inter["piece"] = inter.index
        # Numerator: in-city housing only (see load_buildings).
        hit = gpd.sjoin(city_buildings, inter[["piece", "geometry"]],
                        how="inner", predicate="within")
        floor = hit.groupby("piece")["area_m2"].sum()
        inter["floor"] = inter["piece"].map(floor).fillna(0.0)
        # The denominator has to be the floor area of the WHOLE block group,
        # including the part lying outside the hex grid. Summing only the
        # pieces that intersect the grid would make each partly-covered block
        # group's shares total 1 over its covered half, importing residents who
        # live in Danville. That mistake inflated the city total from 85k to
        # 108k the first time this ran, which is how it was caught -- the ACS
        # reconciliation check below is the thing that catches it.
        # Denominator: ALL housing in the block group, in-city or not.
        bg_hit = gpd.sjoin(buildings, bgs[["GEOID", "geometry"]],
                           how="inner", predicate="within")
        bg_total = bg_hit.groupby("GEOID")["area_m2"].sum()
        bg_floor = inter["GEOID"].map(bg_total).fillna(0.0)
        housed = bg_floor > 0
        inter["frac"] = np.where(housed, inter["floor"] / bg_floor.replace(0, np.nan),
                                 inter["frac"])
        inter["frac"] = inter["frac"].fillna(0.0)
        n_fallback = int((~housed).groupby(inter["GEOID"]).first().sum())
        log(f"    dasymetric: {int(housed.sum())} of {len(inter)} pieces "
            f"weighted by residential floor area"
            + (f"; {n_fallback} block groups had no mapped housing "
               f"and kept area weighting" if n_fallback else ""))
    inter["pop_s"] = inter["pop"] * inter["frac"]
    inter["pop65_s"] = inter["pop65"] * inter["frac"]

    g = inter.groupby("h3")
    out = pd.DataFrame({
        "pop": g["pop_s"].sum(),
        "pop65": g["pop65_s"].sum(),
    })
    # Income is a median, so it can't be summed — weight it by the people it
    # describes, not by area, or empty industrial slivers would sway it.
    w = inter.dropna(subset=["income"]).copy()
    w["wt"] = w["pop_s"]
    gi = w.groupby("h3")
    num = gi.apply(lambda d: np.average(d["income"], weights=d["wt"])
                   if d["wt"].sum() > 0 else np.nan, include_groups=False)
    out["income"] = num

    out["pct65"] = np.where(out["pop"] > 0, out["pop65"] / out["pop"] * 100, 0.0)
    return out.reset_index()


def model_ac_access(income):
    """MODELED A/C access from an income percentile. Not measured — labelled est.

    Percentile rather than raw dollars so the mapping ports to any currency or
    cost-of-living, consistent with normalising everything within the city.
    """
    pct = income.rank(pct=True)
    pct = pct.fillna(pct.median())
    return C.AC_PCT_MIN + (C.AC_PCT_MAX - C.AC_PCT_MIN) * pct


def main():
    import geopandas as gpd
    log(f"Phase 3 — census | ACS {C.ACS_YEAR} 5-yr | "
        f"state {C.STATE_FIPS} county {C.COUNTY_FIPS}")

    hexes = gpd.read_file(C.GRID_FILE).to_crs(C.RASTER_CRS)

    try:
        acs = fetch_acs()
    except Exception as e:
        log(f"  Census API failed ({type(e).__name__}: {e})")
        if ACS_CSV.exists():
            log(f"  falling back to cached {ACS_CSV.name}")
            acs = pd.read_csv(ACS_CSV, dtype={"GEOID": str})
        else:
            raise SystemExit(
                f"\nNo ACS data and no cache at {ACS_CSV}.\n"
                "Set CENSUS_API_KEY in .env (free: "
                "https://api.census.gov/data/key_signup.html)"
            )

    bgs = load_block_groups().merge(acs, on="GEOID", how="left")
    miss = bgs["pop"].isna().sum()
    if miss:
        log(f"  {miss} block groups had no ACS row — treated as empty")
    bgs[["pop", "pop65"]] = bgs[["pop", "pop65"]].fillna(0)

    buildings, city_buildings = load_buildings()
    if buildings is None:
        log("  area-weighting into hexes (no buildings file — run 02b for "
            "dasymetric placement)...")
    else:
        ok, why = dasymetric_is_safe(city_buildings, bgs)
        if ok:
            log(f"  dasymetric-weighting into hexes ({why}; "
                f"{len(city_buildings):,} buildings inside {C.CITY}, "
                f"{len(buildings):,} for block-group totals)...")
        else:
            # Loud, not a footnote: silently swapping estimators is how a build
            # ends up with a method nobody can describe six weeks later.
            log(f"  !! DASYMETRIC REFUSED: {why}")
            log(f"  !! falling back to AREA weighting — see config.DASY_* "
                f"for why this guard exists")
            buildings = city_buildings = None
    per_hex = area_weight(hexes, bgs, buildings, city_buildings)

    out = hexes[["h3"]].merge(per_hex, on="h3", how="left")
    out[["pop", "pop65"]] = out[["pop", "pop65"]].fillna(0)
    out["pct65"] = out["pct65"].fillna(0)
    out["ac_est"] = model_ac_access(out["income"])

    out = out[["h3", "pop", "pct65", "income", "ac_est"]]
    out["pop"] = out["pop"].round(0)
    out[["pct65", "ac_est"]] = out[["pct65", "ac_est"]].round(2)
    out.to_csv(OUT_CSV, index=False)

    total = out["pop"].sum()
    empty = int((out["pop"] < 1).sum())
    log(f"  pop    {total:,.0f} across {len(out)} hexes ({empty} uninhabited)")
    log(f"  pct65  {out.pct65.min():.1f}–{out.pct65.max():.1f}% "
        f"(median {out.pct65.median():.1f})")
    log(f"  income ${out.income.min():,.0f}–${out.income.max():,.0f}")
    log(f"  ac_est {out.ac_est.min():.0f}–{out.ac_est.max():.0f}% (MODELED)")
    log(f"  wrote {OUT_CSV.relative_to(C.ROOT)}")

    # A wild miss means the area weighting is wrong. The band is per-county in
    # config — but note this total is only the part of the county the grid
    # covers, so it is a floor check, not an equality check.
    lo, hi = C.COUNTY_POP_RANGE
    if total > hi:
        log(f"  WARNING: total {total:,.0f} exceeds county upper bound {hi:,.0f} "
            f"— area weighting is double-counting", file=sys.stderr)


if __name__ == "__main__":
    main()
