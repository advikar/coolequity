"""Source-specific corrections to the discovery inventory; not an open-now roster.

Bakersfield has no documented exclusions yet: the Kern County cooling-center
page lists county-run and independent centers but does not identify mapped
discovery sites (libraries, pools, community centres) that lack A/C. Keep the
hook so a future finding can be applied without touching 04/04b.
"""
SOURCE_URL = 'https://www.kerncounty.com/government/aging-adult-services/services/cooling-centers'
# Exact name + kind avoids excluding unrelated facilities in the same city.
NO_AC_LIBRARIES = set()

def eligible_discovery_sites(collection):
    return {**collection, 'features': [f for f in collection['features']
        if not (f['properties'].get('kind') == 'library' and
                f['properties'].get('name') in NO_AC_LIBRARIES)]}
