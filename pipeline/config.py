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

# Hexes with no residents — open ocean, national forest — are dropped before
# scoring. They are not just clutter: sea surface reads 18.4 C against a 51.9 C
# urban max, so leaving them in stretches the heat normalisation over a range no
# inhabited hex occupies. They also invert the headline correlation — across all
# 3,486 hexes corr(LST, greenness) is +0.09, but across the 3,008 populated ones
# it is -0.61 (and -0.58 after removing a quadratic spatial trend, so it is a
# real shade effect and not LA's coastal gradient).
MIN_POP = 1.0

# Share-aged-65 is a ratio, so a hex holding 4 people can read 100% elderly.
# Shrink each hex's rate toward the citywide rate with a pseudo-count of this
# many people (empirical Bayes): a 4-person hex at 100% lands near the city
# mean, while a 5,000-person hex keeps 98% of its own weight. Without it the
# Age-65 layer's colour ramp is set by a 4-person artefact and goes flat.
AGE65_SHRINK_POP = 100.0

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

# ---------------------------------------------------------------- overlays (04)
# Mapping Inequality (Univ. of Richmond) digitised HOLC "residential security"
# maps. US-only — COUNTRY gates this layer off everywhere else.
HOLC_URL = ("https://dsl.richmond.edu/panorama/redlining/static/"
            "citiesData/CALosAngeles1939/geojson.json")

# A hex must be at least this covered by graded polygons before it inherits a
# grade. The 1939 map stops at the then-built-up city, so most of the San
# Fernando Valley is genuinely ungraded; without a floor, a hex that merely
# clips a boundary would be coloured as if it were redlined.
HOLC_MIN_COVER = 0.25

# Public Overpass instances, tried in order. The main one throttles hard on a
# demo day, so the mirror leads.
OVERPASS_MIRRORS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
OVERPASS_TIMEOUT_S = 180
OVERPASS_ROUNDS = 3          # passes over the mirror list before giving up
OVERPASS_BACKOFF_S = 45      # pause between passes — a 504 usually means us

# ---------------------------------------------------------------- intervention
# Front end mirrors these; keep them in sync with app/index.html.
TREE_CANOPY_M2 = 40      # ~40 m2 canopy per mature urban tree
COST_PER_TREE = 500      # planting + 3yr maintenance, USD
WALK_SPEED_KMH = 4.8     # walking pace for the access-time layer

# Straight-line distance under-states a walk, because nobody walks through
# buildings. 4/pi = 1.273 is the exact expected ratio of Manhattan to Euclidean
# distance over uniformly-distributed bearings — i.e. the penalty for a perfect
# street grid, which is very close to what most of LA is.
#
# This is the spec's documented fallback, and it is deliberately the primary
# method: a real osmnx walk graph over this 3,400 km2 bbox is millions of nodes
# and tens of minutes of Overpass download, which is not something to put on the
# critical path of a live demo. Say "circuity-adjusted straight line" out loud
# rather than implying it is routed.
CIRCUITY = 1.273

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "_cache"          # gitignored intermediates (big rasters)

GRID_FILE = DATA / "grid.geojson"        # 01 -> 02
OUT_FILE = DATA / "la.geojson"           # 05 -> the app
CENTERS_FILE = DATA / "centers.geojson"  # 04 -> the app (cooling-center markers)
HOLC_FILE = DATA / "holc_la.geojson"     # 04 fallback, committed
PLACES_FILE = DATA / "places.geojson"    # 04 fallback, committed (hex names)

DATA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
