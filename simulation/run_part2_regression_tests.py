"""
Automated regression test suite for Stage 2 - Part 2 fixes.
"""
import os
import xml.etree.ElementTree as ET
import pandas as pd

# Test 1: Routes
rou = ET.parse('campus_demand.rou.xml').getroot()
routed_vehs = len(rou.findall('vehicle'))
assert routed_vehs == 600, f"Expected 600 routed vehicles, got {routed_vehs}"
print("TEST 1 (Route compilation): PASS - 600/600 trips successfully routed.")

# Test 2: Network permissions
net = ET.parse('campus.net.xml').getroot()
target_edges = ['-517026169#0', '517026174', '-991056586#1', '-991056586#2', '991056586#2', '-517026169#5', '-1031143232']
edges_dict = {e.get('id'): e for e in net.findall('edge')}
for eid in target_edges:
    lane = edges_dict[eid].findall('lane')[0]
    allow = lane.get('allow') or ''
    assert 'passenger' in allow and 'motorcycle' in allow, f"{eid} does not allow passenger/motorcycle"
print("TEST 2 (Network permissions): PASS - all 7 target service corridors allow passenger/motorcycle.")

# Test 3: Unchanged cycleways
cycleway_edges = ['-517026190#0', '-1010963507#0', '-1030312998']
for eid in cycleway_edges:
    lane = edges_dict[eid].findall('lane')[0]
    allow = lane.get('allow') or ''
    assert 'passenger' not in allow, f"Cycleway {eid} was improperly modified!"
print("TEST 3 (Cycleway preservation): PASS - cycleways and private paths remain protected.")

# Test 4: Parking Area capacities
add = ET.parse('campus_parking.add.xml').getroot()
total_cap = 0
for pa in add.findall('parkingArea'):
    cap = int(pa.get('roadsideCapacity'))
    total_cap += cap
    assert pa.get('onRoad') == 'false', f"Parking area {pa.get('id')} onRoad not set to false"
assert total_cap == 213, f"Expected total capacity 213, got {total_cap}"
print("TEST 4 (Parking Area attributes): PASS - roadsideCapacity recognized, total = 213, onRoad=false.")

# Test 5: Telemetry counters
df = pd.read_csv('output/occupancy_data.csv')
sample_df = df.drop_duplicates('sim_time_sec')
total_entries = sample_df['entry_count'].sum()
cumulative = sample_df['cumulative_entered'].iloc[-1]
assert total_entries == cumulative, f"Sum of interval entries ({total_entries}) != final cumulative ({cumulative})"
print(f"TEST 5 (Telemetry counter integrity): PASS - sum of interval entries ({total_entries}) exactly equals cumulative ({cumulative}).")

# Test 6: Database slots intact
with open('../server/src/seeds/seed.js') as f:
    text = f.read()
import re
fw = sum(int(x) for x in re.findall(r'fourWheelerSlots:\s*(\d+)', text))
tw = sum(int(x) for x in re.findall(r'twoWheelerSlots:\s*(\d+)', text))
assert fw == 147, f"Expected 147 4W slots, got {fw}"
assert tw == 356, f"Expected 356 2W slots, got {tw}"
assert fw + tw == 503, f"Expected 503 total slots, got {fw + tw}"
print("TEST 6 (Database capacity preservation): PASS - exactly 503 slots (147 4W, 356 2W) preserved in seed.js.")

print("\nALL AUTOMATED TESTS PASSED!")
