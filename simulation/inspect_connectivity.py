"""
Deep inspection: OSM source ways for the 6 restricted zones and the Ruby Gate,
connectivity to adjacent passable edges, and route reachability.
"""
import xml.etree.ElementTree as ET

# --- 1. Find OSM way types for restricted edges ---
osm = ET.parse('iit_ism_dhanbad.osm').getroot()
osm_ways = {}
for w in osm.findall('way'):
    wid = w.get('id')
    tags = {t.get('k'): t.get('v') for t in w.findall('tag')}
    osm_ways[wid] = tags

# Extract base OSM IDs from SUMO edge IDs (strip leading - and trailing #n)
def base_osm_id(sumo_id):
    s = sumo_id.lstrip('-')
    return s.split('#')[0]

restricted_edges = ['-517026169#0', '517026174', '-991056586#1', '-991056586#2', '991056586#2', '-517026169#5', '-1031143232']
print('=== OSM source tags for restricted edges ===')
for eid in restricted_edges:
    oid = base_osm_id(eid)
    tags = osm_ways.get(oid, {})
    print(f'{eid} -> OSM {oid}: {tags}')

# Also check the 8 working destination edges
working_edges = {
    'zone_sac': '991055730',
    'zone_nlhc': '-517026168#2',
    'zone_cse': '1207647016#1',
    'zone_amber': '1031061562#3',
    'zone_aquamarine': '1029515471',
    'zone_mechanical': '-517026179#7',
    'zone_enviro': '-517026179#5',
    'zone_oat': '-1118600401',
}
print()
print('=== OSM source tags for WORKING zone edges ===')
for zone, eid in working_edges.items():
    oid = base_osm_id(eid)
    tags = osm_ways.get(oid, {})
    print(f'{zone} ({eid}) -> OSM {oid}: {tags}')

# --- 2. Network connectivity: what edges connect TO the restricted edges? ---
net = ET.parse('campus.net.xml').getroot()
edges = {e.get('id'): e for e in net.findall('edge')}
connections = net.findall('connection')

print()
print('=== Connections INTO restricted destination edges ===')
for eid in ['-517026169#0', '517026174', '-991056586#1', '-991056586#2', '991056586#2', '-517026169#5']:
    incoming = [c for c in connections if c.get('to') == eid]
    for c in incoming:
        from_e = edges.get(c.get('from'))
        from_type = from_e.get('type') if from_e is not None else 'unknown'
        print(f'  -> {eid}: from={c.get("from")} type={from_type}')

print()
print('=== Connections OUT OF restricted edges (to find their successors) ===')
for eid in ['-517026169#0', '517026174', '-991056586#1', '-991056586#2', '991056586#2', '-517026169#5']:
    outgoing = [c for c in connections if c.get('from') == eid]
    for c in outgoing:
        to_e = edges.get(c.get('to'))
        to_type = to_e.get('type') if to_e is not None else 'unknown'
        print(f'  {eid} ->: to={c.get("to")} type={to_type}')

# --- 3. Ruby Gate connectivity ---
print()
print('=== Ruby Gate (-1031143232) connections ===')
rb_out = [c for c in connections if c.get('from') == '-1031143232']
rb_in = [c for c in connections if c.get('to') == '-1031143232']
print(f'Outgoing from Ruby Gate:')
for c in rb_out:
    to_e = edges.get(c.get('to'))
    to_type = to_e.get('type') if to_e is not None else 'unknown'
    to_allow = to_e.findall('lane')[0].get('allow') if to_e is not None else 'unknown'
    print(f'  -> {c.get("to")}: type={to_type} allow={to_allow}')
print(f'Incoming to Ruby Gate:')
for c in rb_in:
    from_e = edges.get(c.get('from'))
    from_type = from_e.get('type') if from_e is not None else 'unknown'
    print(f'  <- {c.get("from")}: type={from_type}')
