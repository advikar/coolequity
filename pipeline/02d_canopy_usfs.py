"""Phase 2d — measured tree canopy from the USFS / CAL FIRE 2022 product.

Why this replaces 02c (the Meta/WRI canopy-height model)
--------------------------------------------------------
02c read Meta's Canopy Height Map, whose imagery is **2009–2020** and which reads
~38% below professional aerial assessment. This module reads the **USFS Pacific
Southwest / CAL FIRE California Urban Tree Canopy (2022)** instead:

  * 0.6 m, derived from **2022 NAIP** aerial imagery by a deep-CNN classifier
    (EarthDefine/Dewberry under USFS+CAL FIRE+NOAA), CC0 public domain;
  * an aerial-grade **canopy / no-canopy classification**, not a height proxy, so
    the low bias and the "ranks but does not certify" caveat both go away — the
    percentages are citable in absolute terms;
  * it ships a 2018→2022 change layer (not consumed here, but see DATA_QUALITY.md).

Get the data (per urban area, or statewide) from
<https://www.fs.usda.gov/r05/state-private-tribal/california-urban-canopy-data>
and drop each urban area's `*_canopy2022.tif` **and** its matching urban-boundary
`*.shp` into `data/_cache/canopy_src/`. A county that spans several urban areas
(Contra Costa) needs several pairs; this module processes every pair it finds and
sums per-hex pixel counts, so the split across urban areas is transparent.

The raster
----------
EPSG:3310 (California Albers, **equal-area** — so pixel area is exactly
`res^2` m² with no web-Mercator distortion, which is what 02c got wrong for
`row_m2`). Values: **1 = canopy, 255 = nodata**. Non-canopy land is *not* stored,
so the denominator for a canopy fraction is the assessed land inside the urban
boundary, taken from the boundary shapefile — not "every pixel in the hex."

Output (identical contract to 02c, so 05_score.py and the app are unchanged)
---------------------------------------------------------------------------
  canopy_pct      canopy px / (hex ∩ urban boundary) px, as %
  canopy_m2       canopy px × pixel area (equal-area, exact)
  row_m2          UNSHADED plantable public right-of-way inside the boundary
  row_canopy_pct  share of that right-of-way already shaded
"""
import glob
import sys

import numpy as np

import config as C

CANOPY_VALUE = 1          # USFS raster: 1 = canopy, 255 = nodata
CANOPY_MIN_HT_M = None    # not a height product; kept only so logs read the same
ROW_HALF_WIDTH_M = 7.0    # plantable strip half-width, matches 02c
STRIPE_ROWS = 2048        # window height; bounds memory on a county-size raster
SRC_DIR = C.CACHE / "canopy_src"


def log(msg):
    print(msg, flush=True)


def main():
    import geopandas as gpd
    import pandas as pd
    import rasterio
    from rasterio.windows import Window
    from rasterio.features import rasterize

    log(f"Phase 2d — canopy (USFS/CAL FIRE 2022) | {C.CITY}")
    tifs = sorted(glob.glob(str(SRC_DIR / "**" / "*_canopy2022.tif"), recursive=True))
    shps = glob.glob(str(SRC_DIR / "**" / "*.shp"), recursive=True)
    if not tifs:
        raise SystemExit(
            f"\nNo USFS canopy rasters in {SRC_DIR}.\n"
            f"Download this city's urban-area zip(s) from the USFS California Urban\n"
            f"Canopy page and unzip the *_canopy2022.tif + boundary *.shp into that\n"
            f"folder. See the module docstring.")

    hexes = gpd.read_file(C.GRID_FILE)[["h3", "geometry"]]
    n = len(hexes)
    px_tot = np.zeros(n)   # pixels of each hex that fall on assessed land
    px_can = np.zeros(n)   # of those, canopy
    row_tot = np.zeros(n)  # right-of-way pixels on assessed land
    row_can = np.zeros(n)  # of those, already shaded

    streets = None
    if C.STREETS_FILE.exists():
        streets = gpd.read_file(C.STREETS_FILE)
    else:
        log(f"  !! no {C.STREETS_FILE.name}; row_m2 will be 0. Run 04 first for it.")

    import os
    from rasterio.windows import from_bounds
    pix_area_m2 = None
    for tif in tifs:
        stem = tif[:-len("_canopy2022.tif")]
        # boundary shp for this urban area — beside the raster, or anywhere under
        # SRC_DIR (the USFS zips keep rasters in urbancanopy2022/ and boundaries
        # in a sibling urbanboundary/). Match by urban-area name.
        cand = glob.glob(os.path.join(os.path.dirname(tif), "*.shp")) or shps
        if not cand:
            raise SystemExit(f"  no urban-boundary .shp found for {os.path.basename(tif)}")
        bnd_path = cand[0] if len(cand) == 1 else _match_boundary(stem, cand)

        with rasterio.open(tif) as src:
            crs = src.crs
            if pix_area_m2 is None:
                pix_area_m2 = float(src.res[0] * src.res[1])   # 3310 => exact ground m²
            bnd_union = gpd.read_file(bnd_path).to_crs(crs).geometry.union_all()
            hx = hexes.to_crs(crs)
            # Denominator geometry: each hex clipped to the assessed urban boundary,
            # so a hex overhanging into unassessed (rural) land does not count that
            # overhang as "no canopy" — only assessed pixels are the denominator.
            clipped = hx.geometry.intersection(bnd_union)
            row_geom = None
            if streets is not None:
                row_geom = (streets.to_crs(crs).geometry.buffer(ROW_HALF_WIDTH_M)
                            .union_all().intersection(bnd_union))
            rminx, rminy, rmaxx, rmaxy = src.bounds
            done = 0
            # Per-hex windowed read: each hex is ~0.1–0.8 km² (300k–2M px), so we
            # read only its own bounding box (the .ovr overviews make this cheap)
            # rather than striping the whole 2-billion-pixel raster. Scales to a
            # county by iterating more hexes, not by reading more per hex.
            for i, g in enumerate(clipped):
                if g.is_empty:
                    continue
                gx0, gy0, gx1, gy1 = g.bounds
                if gx1 <= rminx or gx0 >= rmaxx or gy1 <= rminy or gy0 >= rmaxy:
                    continue
                win = from_bounds(max(gx0, rminx), max(gy0, rminy),
                                  min(gx1, rmaxx), min(gy1, rmaxy),
                                  transform=src.transform)
                win = win.round_offsets().round_lengths()
                if win.width < 1 or win.height < 1:
                    continue
                arr = src.read(1, window=win)
                tr = src.window_transform(win)
                mask = rasterize([(g, 1)], out_shape=arr.shape, transform=tr,
                                 fill=0, dtype="uint8").astype(bool)
                canopy = (arr == CANOPY_VALUE) & mask
                px_tot[i] += int(mask.sum())
                px_can[i] += int(canopy.sum())
                if row_geom is not None and not row_geom.is_empty and g.intersects(row_geom):
                    rg = g.intersection(row_geom)
                    if not rg.is_empty:
                        rmask = rasterize([(rg, 1)], out_shape=arr.shape, transform=tr,
                                          fill=0, dtype="uint8").astype(bool)
                        row_tot[i] += int(rmask.sum())
                        row_can[i] += int((rmask & (arr == CANOPY_VALUE)).sum())
                done += 1
            log(f"  {os.path.basename(tif)}: assessed {done} hexes")

    out = pd.DataFrame({"h3": hexes["h3"]})
    with np.errstate(invalid="ignore", divide="ignore"):
        out["canopy_pct"] = np.where(px_tot > 0, px_can / px_tot * 100, np.nan)
        out["row_canopy_pct"] = np.where(row_tot > 0, row_can / row_tot * 100, 0.0)
    out["canopy_m2"] = (px_can * pix_area_m2).round(0)
    out["row_m2"] = ((row_tot - row_can) * pix_area_m2).clip(min=0).round(0)

    # The USFS product covers 2020 Census urban areas only, so rural-fringe hexes
    # outside the boundary come back NaN. Fill them from the older Meta/WRI CHM
    # canopy (still a *measured* height product, and better than the NDVI proxy in
    # exactly the summer-dry fringe where NDVI is weakest). Save the CHM run as
    # `canopy_<slug>_chm.csv` beside this output to enable the fallback.
    chm_path = C.CANOPY_CSV.with_name(C.CANOPY_CSV.stem + "_chm.csv")
    if chm_path.exists():
        chm = pd.read_csv(chm_path).set_index("h3")
        miss = out["canopy_pct"].isna()
        out = out.set_index("h3")
        for c in ["canopy_pct", "row_canopy_pct", "canopy_m2", "row_m2"]:
            if c in chm.columns:
                out[c] = out[c].where(~out["canopy_pct"].isna() if c != "canopy_pct"
                                      else out[c].notna(), chm[c])
        out = out.reset_index()
        log(f"  filled {int(miss.sum())} fringe hexes (outside the urban boundary) "
            f"from the CHM fallback {chm_path.name}")

    ok = out["canopy_pct"].notna()
    log(f"  canopy_pct: {out.loc[ok,'canopy_pct'].min():.1f}–"
        f"{out.loc[ok,'canopy_pct'].max():.1f}% (median "
        f"{out.loc[ok,'canopy_pct'].median():.1f}%, {ok.sum()}/{n} hexes assessed)")
    # population-weighted canopy sanity line — this is what the city will quote
    log(f"  canopy area: {out.canopy_m2.sum()/1e6:.2f} km² | "
        f"unshaded ROW: {out.row_m2.sum()/1e6:.2f} km²")
    out.to_csv(C.CANOPY_CSV, index=False)
    log(f"  wrote {C.CANOPY_CSV.relative_to(C.ROOT)}")


def _match_boundary(stem, cands):
    """When a folder holds several urban areas, pick the boundary whose filename
    shares the longest prefix with this raster's urban-area name."""
    import os
    base = os.path.basename(stem).lower()
    return max(cands, key=lambda c: len(os.path.commonprefix(
        [base, os.path.splitext(os.path.basename(c))[0].lower()])))


if __name__ == "__main__":
    main()
