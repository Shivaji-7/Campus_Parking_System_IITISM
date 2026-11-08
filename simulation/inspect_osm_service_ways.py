"""
Check whether the 6 restricted zone edges are reachable via paths
that only use residential/unclassified edges (no service edges needed).
Also check which service-road edges are direct campus driveways vs. just 
internal paths - to determine which ones to enable for passenger/motorcycle.
"""
import xml.etree.ElementTree as ET

osm = ET.parse('iit_ism_dhanbad.osm').getroot()
osm_ways = {}
for w in osm.findall('way'):
    wid = w.get('id')
    tags = {t.get('k'): t.get('v') for t in w.findall('tag')}
    nd_refs = [n.get('ref') for n in w.findall('nd')]
    osm_ways[wid] = {'tags': tags, 'nodes': nd_refs}

# All service ways and their tags
service_ways = {wid: data for wid, data in osm_ways.items() if data['tags'].get('highway') == 'service'}
print(f'Total OSM service ways: {len(service_ways)}')
print()

# What additional tags do service ways have (access, service type, etc.)?
all_keys = set()
for data in service_ways.values():
    all_keys.update(data['tags'].keys())
print('Tag keys seen in service ways:', sorted(all_keys))
print()

# Print all service way tags
for wid, data in service_ways.items():
    print(f'OSM way {wid}: {data["tags"]}')
