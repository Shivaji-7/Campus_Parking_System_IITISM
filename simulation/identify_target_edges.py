"""
Determine minimum safe set of service edges to enable for motor vehicles.
Strategy:
1. Campus internal roads used as PARKING ACCESS (dest zones) should allow motor vehicles 
2. Ruby Gate (direct campus entry road) should allow motor vehicles
3. Shared cycleways with pictograms (pure cycle/pedestrian paths) should NOT be changed
4. 'access: private' ways should NOT be changed

Minimum set = 6 destination service-road OSM IDs + Ruby Gate + corridor between them.
We identify which specific SUMO edge IDs to modify.
"""
import xml.etree.ElementTree as ET

net = ET.parse('campus.net.xml').getroot()
edges_dict = {e.get('id'): e for e in net.findall('edge')}

# OSM service ways that are CAMPUS INTERNAL DRIVEWAY roads (no cycleway tag, no private access)
# These are the ones that connect parking zones
target_osm_ids = {
    '517026169',   # Zone main_gate + academic_complex corridor
    '517026174',   # Zone health_centre
    '991056586',   # Zone library, nac, i2h  
    '1031143232',  # Ruby Gate
    '1031148062',  # Connects from library side (seen in connections)
    '991057338',   # Check if this is needed
    '1031144175',  # Check if this is needed
    '1031148063',  # Check if this is needed
}

# Cycleways (shared_lane pictogram) - DO NOT enable cars on these
cycleway_osm_ids = {
    '1010963507', '1010963508', '1010963509', '1010963510',
    '1031064865', '1031064866', '1031068030',
    '1031097081', '1031097082', '1031097083', '1031097084', '1031097085', '1031097086',
    '517026190',  
}

# Private access - DO NOT change
private_osm_ids = {'1030312998'}

def osm_id_of_edge(edge_id):
    s = edge_id.lstrip('-')
    return s.split('#')[0]

# Find all SUMO edges whose OSM base ID is in target set
print('=== SUMO edges to enable for motor vehicles (target_osm_ids) ===')
target_sumo_edges = []
for eid, edge in edges_dict.items():
    if edge.get('type') != 'highway.service':
        continue
    osm_id = osm_id_of_edge(eid)
    if osm_id in target_osm_ids:
        for lane in edge.findall('lane'):
            target_sumo_edges.append({
                'sumo_id': eid,
                'osm_id': osm_id,
                'type': edge.get('type'),
                'allow': lane.get('allow'),
                'length': lane.get('length'),
                'speed': lane.get('speed'),
            })
        print(f'  {eid} (OSM {osm_id}): length={edge.findall("lane")[0].get("length")} speed={edge.findall("lane")[0].get("speed")}')

print(f'\nTotal SUMO edges targeted for permission change: {len(target_sumo_edges)}')

print()
print('=== SUMO edges to LEAVE UNCHANGED (cycleways/private) ===')
unchanged_count = 0
for eid, edge in edges_dict.items():
    if edge.get('type') != 'highway.service':
        continue
    osm_id = osm_id_of_edge(eid)
    if osm_id in cycleway_osm_ids or osm_id in private_osm_ids:
        reason = 'cycleway' if osm_id in cycleway_osm_ids else 'private'
        print(f'  UNCHANGED {eid} (OSM {osm_id}): reason={reason}')
        unchanged_count += 1
print(f'Total SUMO service edges left unchanged: {unchanged_count}')

print()
print('=== Service edges NOT in either set (need classification) ===')
for eid, edge in edges_dict.items():
    if edge.get('type') != 'highway.service':
        continue
    osm_id = osm_id_of_edge(eid)
    if osm_id not in target_osm_ids and osm_id not in cycleway_osm_ids and osm_id not in private_osm_ids:
        for lane in edge.findall('lane'):
            print(f'  UNCLASSIFIED {eid} (OSM {osm_id}): allow={lane.get("allow")} length={lane.get("length")}')
