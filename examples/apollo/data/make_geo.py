"""Writes the map data for apollo.md beside this file, from Natural Earth 1:50m (public domain,
naturalearthdata.com):
  pacific-land.geojson   land in the central Pacific, from ne_50m_land
  us-states.geojson      the 48 contiguous US states, from ne_50m_admin_1_states_provinces_lakes
Run it again only to rebuild them; the sheet reads the GeoJSON.
  python make_geo.py NATURAL_EARTH_DIR      (the folder that holds the unzipped .shp, .shx and .dbf files)"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
import handbook  # noqa: E402

if len(sys.argv) != 2:
    sys.exit(__doc__)
NE = Path(sys.argv[1])
PACIFIC = (-180.0, -150.0, -30.0, 30.0)


def inside(box, lon, lat):
    return box[0] <= lon <= box[1] and box[2] <= lat <= box[3]


def rounded(ring, places):
    out = []
    for x, y in ring:
        q = [round(x, places), round(y, places)]
        if not out or q != out[-1]:
            out.append(q)
    return out


def write(name, feats):
    (HERE / name).write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(HERE / name)


land = []
for _, _, parts in handbook._read_shapes(NE / "ne_50m_land.shp"):
    for part in parts:
        if all(inside(PACIFIC, *q) for q in part):
            land.append({"type": "Feature", "properties": {},
                         "geometry": {"type": "Polygon", "coordinates": [rounded(part, 3)]}})
write("pacific-land.geojson", land)

states = []
for props, _, parts in handbook._read_shapes(NE / "ne_50m_admin_1_states_provinces_lakes.shp"):
    if props.get("iso_a2") != "US" or props.get("postal") in ("AK", "HI", "DC"):
        continue
    rings = [r for r in (rounded(p, 2) for p in parts) if len(r) >= 4]
    states.append({"type": "Feature", "properties": {"name": props["name"], "postal": props["postal"]},
                   "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}})
write("us-states.geojson", states)
