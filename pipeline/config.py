"""Single place to retarget the engine at another city.

Everything downstream reads from here. Swapping CITY + BBOX + H3_RES is meant to be
the whole change needed to run on a different city — that portability claim is the
point of the project, so nothing else in the pipeline should hardcode "Los Angeles".
"""
from pathlib import Path

# ---------------------------------------------------------------- geography
CITY = "Contra Costa County"
SLUG = "contracosta"            # names every artefact, so cities/counties coexist
COUNTRY = "USA"                 # gates the US-only layers (HOLC, ACS)

# west, south, east, north. NOT hand-drawn: this is the exact bounding box of the
# TIGERweb incorporated-place polygon for San Ramon city (GEOID 0668378), read
# off the geometry rather than eyeballed off a map. The polygon itself clips the
# grid in 01, so the hexes follow the real city limits, which are ragged — San
# Ramon annexed in pieces and has Dougherty Valley hanging off the east side.
BBOX = (-122.4301, 37.7185, -121.5342, 38.0999)

# San Ramon is 52.0 km2. At res 8 (0.74 km2) that is 71 hexes — statistically
# tidy, since the city holds ~55 census block groups, but far too coarse to look
# like a map. Res 9 (0.105 km2, ~370 m across) gives ~490 hexes and a real
# picture of where the heat sits.
#
# The trade is documented rather than hidden: Landsat and Sentinel-2 genuinely
# resolve at this size, so heat and canopy are per-hex measurements. The census
# fields cannot be — a res-9 hex is roughly a ninth of a block group, so
# population, age and income are areally interpolated DOWNWARD and vary smoothly
# across neighbours. Real data, coarser than the grid drawn over it. Said out
# loud in the app and in the README.
H3_RES = 8

# ---------------------------------------------------------------- scoring
# Section 7 of the build spec. Exposed here so they're tunable and defensible
# when a judge asks "why 35%?".
#
# A/C access is BACK IN THE SCORE here, and that is the single most important
# difference between this build and the San Ramon one. It is modelled by ranking
# each hex's median household income within the study area and stretching that
# percentile across AC_PCT_MIN..AC_PCT_MAX, so it is only meaningful where income
# genuinely varies. San Ramon's block-group medians ran $100,906-$250,001 — the
# transform would have invented a 35-95% spread across a uniformly wealthy town,
# so it was weighted zero there.
#
# Contra Costa is a different animal. Measured across its 674 block groups with
# income: $18,071 to $250,001, p10 $69,526, median $128,142, p90 $240,586. Thirty
# percent of them fall below San Ramon's POOREST block group. Richmond, San Pablo
# and Bay Point against Blackhawk, Alamo and Diablo is a real gradient, so the
# percentile carries real signal and LA's original weights apply unchanged.
#
# It is still MODELLED, not measured — no census counts air conditioners — and
# the UI must keep labelling it `est`. Restoring its weight restores its
# obligation to be labelled.
WEIGHTS = {
    "heat":     0.35,   # heat_n
    "green":    0.25,   # (1 - greenness_n)
    "ac":       0.25,   # (1 - ac_access_n)  -- MODELED from income; see above
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
#
# LA composited one summer because one summer was plenty: 20 Landsat scenes
# cleared the 20% cloud filter over the basin. Over San Ramon's much smaller
# footprint, summer 2023 yields exactly ONE — and a single scene is not a median,
# it is one afternoon, with whatever haze and whatever synoptic weather that day
# happened to bring.
#
# So the window is three summers rather than one, at the SAME strict cloud
# filter: 2022-2024 gives 35 Landsat and 60 Sentinel-2 scenes. Loosening the
# cloud threshold instead (11 scenes at <50%) would have bought quantity with
# quality, which is the wrong trade for a thermal median.
#
# These are summer months in each year, never a continuous 2022-2024 range —
# 02 searches each year separately and concatenates. A straight range would pull
# in January scenes and quietly turn "peak summer surface temperature" into an
# annual mean.
SUMMER_YEARS = (2022, 2023, 2024)
SUMMER_MMDD = ("06-01", "09-15")
MAX_CLOUD_PCT = 20

# Metric CRS for raster work — UTM 10N covers the East Bay (LA used 11N).
# (Zonal means in a projected CRS avoid the lat/lon pixel anisotropy.)
RASTER_CRS = "EPSG:32610"
# 30 m, not LA's 100 m: a res-9 hex is ~370 m across, so at 100 m it would hold
# only ~10 pixels and the zonal mean would be noise. 30 m is Landsat thermal's
# native grid and gives ~115 px/hex over an area this small.
RASTER_RES_M = 30
MAX_SCENES = 30             # cap per collection so a demo build stays bounded

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
COUNTY_FIPS = "013"          # Contra Costa County (LA build used 037)

# Sanity band for the county-wide ACS total, checked at the end of 03. Contra
# Costa is ~1.16M; LA County was ~9.85M, so this cannot stay hardcoded.
COUNTY_POP_RANGE = (0.9e6, 1.4e6)

# TIGERweb feature used to clip the grid to land/city in 01. LA clipped to the
# whole county; San Ramon clips to the incorporated place, because a county-sized
# clip here would leave the grid covering Mount Diablo and half of Danville.
# County polygon this time, not a place polygon — a different TIGERweb service
# and layer. GEOID 06013 is Contra Costa County.
CLIP_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/13/query?"
            "where=GEOID%3D%2706013%27&outFields=GEOID,NAME&"
            "returnGeometry=true&outSR=4326&f=geojson")

# A/C access is MODELED from an income percentile — there is no A/C census.
# See AC_IN_SCORE below: for San Ramon this layer is built but NOT scored.
AC_PCT_MIN = 35.0
AC_PCT_MAX = 95.0

# ---------------------------------------------------------------- overlays (04)
# Mapping Inequality (Univ. of Richmond) digitised HOLC "residential security"
# maps. US-only — COUNTRY gates this layer off everywhere else.
#
# None for San Ramon, and this is a fact about history rather than a gap in the
# build: HOLC surveyed built-up cities in 1935-1940, and San Ramon was farmland
# then — it did not incorporate until 1983. Mapping Inequality has Oakland,
# Berkeley, Richmond, San Francisco, San Jose and Stockton; there is no Contra
# Costa suburb map to load. Setting this to None turns the layer off end to end
# rather than colouring the city with somebody else's grades.
# No HOLC map covers Contra Costa in any useful way. Checked against Mapping
# Inequality directly rather than assumed: the East Bay 1937 survey is an
# Oakland/Berkeley map, and only 8 of its 120 polygons touch this county — all
# graded A, B or C, with NO D grades at all. Turning the layer on would draw a
# sliver over El Cerrito and imply a redlining story the data cannot support.
# LA's best story beat simply does not exist here; say so rather than fake it.
HOLC_URL = None

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
# A demo reads the ranked list aloud, so hex names have to be names a resident
# would recognise. LA had enough OSM place nodes to do that on its own; San Ramon
# has FIVE for 541 hexes, which produces "Windemere NE 19" and tells nobody
# anything. It does, however, have 90 named residential subdivisions mapped as
# landuse polygons — Canyon Lakes, Gale Ranch, Bent Creek Estates — which are
# exactly the names people use. With this on, 04 also pulls those (and named
# parks, which anchor the non-residential hexes) and names a hex after the
# polygon it falls INSIDE, falling back to the nearest anchor.
#
# Off for LA, whose committed places.geojson is place nodes only and whose names
# are already good.
NAME_FROM_LANDUSE = True

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

# Every artefact carries the city SLUG. LA's files are committed under their own
# names on master, and a San Ramon run must not quietly overwrite them — the
# branch is meant to add a city, not replace one. It also means the app's
# ?data=<name> switch can flip between the two without a rebuild.
GRID_FILE = DATA / f"grid_{SLUG}.geojson"        # 01 -> 02
OUT_FILE = DATA / f"{SLUG}.geojson"              # 05 -> the app
CENTERS_FILE = DATA / f"centers_{SLUG}.geojson"  # 04 -> the app
HOLC_FILE = DATA / f"holc_{SLUG}.geojson"        # 04 fallback (unused: HOLC_URL is None)
PLACES_FILE = DATA / f"places_{SLUG}.geojson"    # 04 fallback, committed (hex names)
BOUNDARY_FILE = DATA / f"boundary_{SLUG}.geojson"  # 01 clip polygon, committed
ACS_FILE = DATA / f"acs_{SLUG}.csv"              # 03 fallback, committed
# Residential building footprints, committed. 03 uses them to place people
# INSIDE a block group instead of smearing them evenly across its area.
BUILDINGS_FILE = DATA / f"buildings_{SLUG}.geojson"
# Plantable street centrelines, committed. 04 measures frontage per hex; the app
# turns that into how many street trees the city could actually put in.
STREETS_FILE = DATA / f"streets_{SLUG}.geojson"

# How far outside BBOX 02b pulls buildings. 03 divides a block group's residents
# by that block group's TOTAL housing, so any block group straddling the bbox
# edge needs its outside-the-bbox houses counted or the denominator is short and
# every in-area hex sharing it is inflated.
#
# San Ramon needed 0.09 deg: its bbox was the city, and 17 of the 61 block groups
# touching it ran up to 0.07 deg past the edge. Here BBOX is derived from the
# county's own block groups' bounds, so every one of them is inside it by
# construction and the margin only has to cover geometry slop.
BUILDINGS_MARGIN_DEG = 0.02

# --- when dasymetric placement is allowed at all -------------------------------
# Splitting a block group's residents by building floor area is only better than
# splitting by area if the building mask is COMPLETE and UNBIASED. OSM is neither,
# everywhere. Measured:
#
#   San Ramon         20,417 buildings / ~31k ACS housing units = 0.66 coverage,
#                     even across income (the city is uniformly wealthy)  -> USE IT
#   Contra Costa Co.  139,121 / 426,585 = 0.33 coverage, and coverage by income
#                     quartile runs 0.07 / 0.07 / 0.08 / 0.33 -- the richest
#                     quartile is mapped 4.7x better than the poorest  -> REFUSE
#
# The county case is the dangerous one and it is dangerous in a specific
# direction: population is a MULTIPLIER in the score, so concentrating residents
# into well-mapped areas would systematically demote poor neighbourhoods. An
# equity tool that under-ranks poverty because volunteers mapped Blackhawk more
# thoroughly than North Richmond is worse than useless.
#
# 03_census.py checks both numbers and falls back to area weighting if either
# fails. Do not raise these to force dasymetric on; fix the mask instead.
DASY_MIN_COVERAGE = 0.50     # mapped buildings per ACS housing unit, study-wide
DASY_MAX_INCOME_BIAS = 2.0   # richest-quartile coverage / poorest-quartile
LST_TIF = DATA / f"lst_{SLUG}.tif"               # 02 composite cache, committed
NDVI_TIF = DATA / f"ndvi_{SLUG}.tif"             # 02 composite cache, committed
SAT_CSV = DATA / f"satellite_{SLUG}.csv"
CENSUS_CSV = DATA / f"census_{SLUG}.csv"
OVERLAYS_CSV = DATA / f"overlays_{SLUG}.csv"

DATA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
