"""Single place to retarget the engine at another city.

Everything downstream reads from here. Swapping CITY + BBOX + H3_RES is meant to be
the whole change needed to run on a different city — that portability claim is the
point of the project, so nothing else in the pipeline should hardcode "Los Angeles".
"""
from pathlib import Path

# ---------------------------------------------------------------- geography
CITY = "Los Angeles"
COUNTRY = "USA"                 # gates the US-only layers (HOLC, ACS)

# west, south, east, north — the LA basin, trimmed to avoid mostly-ocean hexes.
BBOX = (-118.67, 33.70, -118.15, 34.34)

# res 8 ~0.74 km2 (city detail), res 7 ~5.16 km2 (fewer cells, smoother map).
# Spec calls for 8; drop to 7 if the browser lags with the real cell count.
H3_RES = 8

# ---------------------------------------------------------------- scoring
# Section 7 of the build spec. Exposed here so they're tunable and defensible
# when a judge asks "why 35%?".
WEIGHTS = {
    "heat":     0.35,   # heat_n
    "green":    0.25,   # (1 - greenness_n)
    "ac":       0.25,   # (1 - ac_access_n)
    "age65":    0.15,   # age65_n
}
# priority = base_risk * (POP_FLOOR + POP_WEIGHT * population_n)
POP_FLOOR = 0.55
POP_WEIGHT = 0.45

# ---------------------------------------------------------------- satellite
# Summer window — LST is only meaningful at peak heat.
SUMMER_START = "2023-06-01"
SUMMER_END = "2023-09-15"
MAX_CLOUD_PCT = 20

# Metric CRS for raster work — UTM 11N covers LA. Retarget with the city.
# (Zonal means in a projected CRS avoid the lat/lon pixel anisotropy.)
RASTER_CRS = "EPSG:32611"
RASTER_RES_M = 100          # 30 m Landsat / 10 m S2 downsampled; hexes are ~900 m across
MAX_SCENES = 20             # cap per collection so a demo build stays bounded

# NDVI -> vegetation-cover-% proxy: clamp, then scale linearly to 0..CANOPY_MAX.
#
# Endpoints are physical, not percentile-based: NDVI ~0.05 is the bare-soil/paved
# threshold and ~0.65 is dense healthy canopy in this composite (observed p99 =
# 0.67). They must stay absolute because canopy % feeds the ROI tree count — a
# relative stretch would make a desert city look as green as a forest one.
#
# The spec's 0.20-0.80 was calibrated for wetter imagery: against LA's dry-summer
# median NDVI of 0.24 it floored 40% of hexes at exactly 0% green, flattening the
# layer and pinning the ROI slider. 0.05-0.65 gives a citywide median of ~14%,
# consistent with LA's published ~21% tree canopy for a dry-summer composite.
NDVI_CLAMP = (0.05, 0.65)
CANOPY_MAX_PCT = 45.0

# ---------------------------------------------------------------- census (US)
ACS_YEAR = 2023
STATE_FIPS = "06"
COUNTY_FIPS = "037"          # Los Angeles County

# A/C access is MODELED from an income percentile — there is no A/C census.
# These bounds are the plausible spread for LA County, not measured values, and
# the UI must keep labelling the layer "est.".
AC_PCT_MIN = 35.0
AC_PCT_MAX = 95.0

# ---------------------------------------------------------------- intervention
# Front end mirrors these; keep them in sync with app/index.html.
TREE_CANOPY_M2 = 40      # ~40 m2 canopy per mature urban tree
COST_PER_TREE = 500      # planting + 3yr maintenance, USD
WALK_SPEED_KMH = 4.8     # haversine fallback for access time

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "_cache"          # gitignored intermediates (big rasters)

GRID_FILE = DATA / "grid.geojson"        # 01 -> 02
OUT_FILE = DATA / "la.geojson"           # 05 -> the app
CENTERS_FILE = DATA / "centers.geojson"

DATA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
