"""Source-specific corrections to the discovery inventory; not an open-now roster."""
SOURCE_URL = 'https://ehsd.org/wp-content/uploads/2026/07/Senior_Cooling-Centers-Tips_July-2026.docx'
# The June 2026 revision explicitly identifies these libraries as lacking A/C.
# Exact name + kind avoids excluding unrelated facilities in the same city.
NO_AC_LIBRARIES = {'Kensington Branch Library', 'El Cerrito Branch Contra Costa County Library'}
def eligible_discovery_sites(collection):
    return {**collection, 'features': [f for f in collection['features']
        if not (f['properties'].get('kind') == 'library' and
                f['properties'].get('name') in NO_AC_LIBRARIES)]}
