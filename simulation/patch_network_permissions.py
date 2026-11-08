"""
Part A Fix: Network lane permission transformation.

STRATEGY: We do NOT re-run netconvert (which would lose calibration).
Instead we apply a targeted SUMO edge-type override file 
(campus_edge_types_override.add.xml) that is loaded as an additional file.

For SUMO, the correct way to override permissions at runtime without 
regenerating the network is to use a <laneTypeRerouter> or 
laneAttribute edit. However the cleanest approach for a batch change
is a Python script that directly patches the campus.net.xml XML
on the targeted OSM-sourced edges only.

This script:
1. Backs up campus.net.xml -> campus.net.xml.backup_stage1 (already done)
2. Applies lane permission change on the 34 targeted edges
3. Changes allow="pedestrian delivery bicycle" to 
   allow="passenger motorcycle delivery bicycle pedestrian evehicle"
   (matching the default.allow from netconvert config header)
4. Leaves cycleway-tagged and private edges UNCHANGED
5. Writes a log of all changed lanes.

ONLY affected OSM IDs are patched:
  517026169  - Main gate corridor + Academic complex corridor
  517026174  - Health centre spur
  991056586  - Library, NAC, I2H corridor (Maxar digitized service road)
  1031143232 - Ruby Gate entry road
  1031148062 - Campus internal link (connects from CSE side to 991056586)
  1031148063 - Campus internal link  
  991057338  - Campus internal spur
  1031144175 - Campus spur

UNCHANGED (cycleways):
  517026190, 1010963507/08/09/10, 1031064865/66, 1031068030, 1031097081-86
UNCHANGED (private):
  1030312998
"""
import xml.etree.ElementTree as ET
import shutil
import os

NET_FILE = 'campus.net.xml'
BACKUP = 'campus.net.xml.backup_stage1'

# Target OSM IDs whose service edges should allow motor vehicles
TARGET_OSM_IDS = {
    '517026169',   # Main gate corridor + Academic complex corridor
    '517026174',   # Health centre access road
    '991056586',   # Library, NAC, I2H corridor
    '1031143232',  # Ruby Gate entry road
    '1031148062',  # Campus internal connector
    '1031148063',  # Campus internal connector
    '991057338',   # Campus internal spur
    '1031144175',  # Campus spur
}

# OSM IDs to leave completely unchanged
SKIP_OSM_IDS = {
    '517026190',   # Cycleway (shared_lane pictogram)
    '1010963507', '1010963508', '1010963509', '1010963510',  # Cycleways
    '1031064865', '1031064866', '1031068030',  # Cycleways
    '1031097081', '1031097082', '1031097083',  # Cycleways
    '1031097084', '1031097085', '1031097086',  # Cycleways
    '1030312998',  # Private access
}

# New permission string: passenger + motorcycle + delivery + bicycle + pedestrian + evehicle
NEW_ALLOW = 'passenger motorcycle delivery bicycle pedestrian evehicle'

def osm_id_of_edge(edge_id: str) -> str:
    s = edge_id.lstrip('-')
    return s.split('#')[0]

print(f'Loading {NET_FILE} ...')
tree = ET.parse(NET_FILE)
root = tree.getroot()

changed_lanes = []
skipped_lanes = []

for edge in root.findall('edge'):
    eid = edge.get('id')
    osm_id = osm_id_of_edge(eid)
    etype = edge.get('type')
    
    if etype != 'highway.service':
        continue
    
    if osm_id in SKIP_OSM_IDS:
        skipped_lanes.append(eid)
        continue
    
    if osm_id in TARGET_OSM_IDS:
        for lane in edge.findall('lane'):
            old_allow = lane.get('allow')
            if old_allow == 'pedestrian delivery bicycle':
                lane.set('allow', NEW_ALLOW)
                changed_lanes.append({
                    'edge_id': eid,
                    'osm_id': osm_id,
                    'old_allow': old_allow,
                    'new_allow': NEW_ALLOW,
                })

print(f'Total lane permissions changed: {len(changed_lanes)}')
print(f'Total edges skipped (cycleways/private): {len(skipped_lanes)}')

# Write patched network
print(f'Writing patched network to {NET_FILE} ...')
tree.write(NET_FILE, encoding='UTF-8', xml_declaration=True)
print('Done.')

# Write change log
log_path = os.path.join('output', 'network_permission_changes.csv')
os.makedirs('output', exist_ok=True)
with open(log_path, 'w', encoding='utf-8', newline='') as f:
    f.write('edge_id,osm_id,old_allow,new_allow\n')
    for c in changed_lanes:
        f.write(f'{c["edge_id"]},{c["osm_id"]},{c["old_allow"]},{c["new_allow"]}\n')
print(f'Change log written to {log_path}')
print()
print('Summary of changed edges:')
for c in changed_lanes:
    print(f'  {c["edge_id"]} (OSM {c["osm_id"]}): {c["old_allow"]} -> {c["new_allow"]}')
