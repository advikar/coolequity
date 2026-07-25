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
ACS_CSV = C.DATA / "acs.csv"          # committed fallback
OUT_CSV = C.DATA / "census.csv"

POP = "B01001_001E"
INCOME = "B19013_001E"
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
        "get": ",".join([POP, INCOME] + AGE65),
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

    num = [POP, INCOME] + AGE65
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    # ACS uses large negative sentinels (-666666666) for suppressed estimates.
    df[num] = df[num].mask(df[num] < -1e6)

    df["GEOID"] = (df["state"] + df["county"] + df["tract"] + df["block group"])
    df["pop"] = df[POP].fillna(0)
    df["pop65"] = df[AGE65].sum(axis=1, min_count=1).fillna(0)
    df["income"] = df[INCOME]

    out = df[["GEOID", "pop", "pop65", "income"]]
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


def area_weight(hexes, bgs):
    """Split each block group's people across the hexes it overlaps, by area.

    Assumes people are spread evenly within a block group. That's the standard
    areal-interpolation assumption and it's reasonable at block-group size, but
    it is an assumption — worth saying out loud if a judge asks.
    """
    import geopandas as gpd
    bgs = bgs.copy()
    bgs["bg_area"] = bgs.geometry.area

    inter = gpd.overlay(
        hexes[["h3", "geometry"]], bgs, how="intersection", keep_geom_type=True
    )
    inter["frac"] = inter.geometry.area / inter["bg_area"]
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

    log("  area-weighting into hexes...")
    per_hex = area_weight(hexes, bgs)

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

    # LA County is ~9.85M; a wild miss means the area weighting is wrong.
    if not (5e6 < total < 12e6):
        log(f"  WARNING: county total {total:,.0f} looks off", file=sys.stderr)


if __name__ == "__main__":
    main()
