"""
Simple test script to convert CSV to HypoDD formats
"""

from softwares.hypodd_pywrapper.scripts.csv_hypodd import csv_to_pha, csv_to_cc, create_event_id_mapping, create_station_file, load_catalog

# Input files
csv_file = '../data/input_csvs/nc73818801_fmf_detections_phase_picks.csv'
station_csv = '../data/input_csvs/stations_2000_onshore_permanent_50km_cleaned_2022.csv'
catalog_csv = '../data/input_csvs/yoon_shelly_ferndale-2022-12-01.csv'

# Output files
pha_file = '../data/hypoDD_inputs/detections.pha'
cc_file = '../data/hypoDD_inputs/detections.cc'
sta_file = '../data/hypoDD_inputs/station.dat'
mapping_file = '../data/hypoDD_inputs/event_id_mapping.csv'

print("Converting CSV to HypoDD formats...")
print("="*60)

# Step 1: Create station file
create_station_file(station_csv, sta_file)

# Step 2: Load catalog from Yoon & Shelly
catalog_info = load_catalog(catalog_csv)

# Step 3: Create event ID mapping
event_mapping = create_event_id_mapping(csv_file, mapping_file)

# Step 4: Convert to .pha using the mapping and catalog
csv_to_pha(csv_file, pha_file, catalog_info, event_mapping)

# Step 5: Convert to .cc using the same mapping
csv_to_cc(csv_file, cc_file, min_cc=0.6, event_id_mapping=event_mapping)

print("="*60)
print("Done! Check the output files:")
print(f"  {sta_file}")
print(f"  {pha_file}")
print(f"  {cc_file}")
print(f"  {mapping_file} (to map back synthetic IDs to original)")

