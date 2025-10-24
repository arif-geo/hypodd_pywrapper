# HypoDD Conversion Summary

## What We Did

### Task 1: Station File ✅
- Created `create_station_file()` function
- Reads station CSV and outputs HypoDD format: `STA LAT LON ELV`
- Generated `station.dat` with 27 stations

### Task 2: Real Catalog Data ✅
- Created `load_catalog()` function to read Yoon & Shelly catalog
- Extracts: lat, lon, depth, magnitude, uncertainty_x (eh), uncertainty_z (ez)
- Loaded 10,033 events from catalog

### Task 3: Improved csv_to_pha ✅
- **Template events**: Use full catalog info (location, magnitude, uncertainties)
- **Detected events**: Inherit template's location but mag=0.0, uncertainties=0.0
- Added clear comments explaining the logic

## Results

### Event ID 100022 (Template: nc73818801)
```
# 2022 12 15  2 16  4.11  40.4657 -124.4777  29.78 2.47 6.46 1.09 0.00    100022
```
- Location: 40.4657°N, -124.4777°E, 29.78 km depth
- Magnitude: 2.47
- Uncertainties: EH=6.46 km, EZ=1.09 km (from catalog)
- Weight: 1.0 (template picks have no CC values)

### Event ID 100000 (Detection: nc73818801_20200309_105118)
```
# 2020  3  9 10 51 18.61  40.4657 -124.4777  29.78 0.00 0.00 0.00 0.00    100000
```
- Location: Same as template (initial guess)
- Magnitude: 0.00 (unknown - HypoDD won't estimate this)
- Uncertainties: 0.00 (using template location as proxy)
- Weight: CC values (0.6-0.9 range)

## Key Design Decisions

1. **Magnitude for detected events**: Set to 0.0
   - HypoDD doesn't estimate magnitude
   - This is just a placeholder
   - Consider: Could calculate from amplitude ratios later

2. **Uncertainties for detected events**: Set to 0.0
   - We're using template location as initial guess
   - HypoDD will relocate these events relative to template
   - The uncertainty comes from the relocation process, not the initial location

3. **Weights**: 
   - Template events: 1.0 (no CC available)
   - Detected events: CC values (correlation coefficient 0.6-1.0)

## Output Files

- `station.dat`: 27 stations
- `detections.pha`: 23 events (22 detections + 1 template)
- `detections.cc`: Differential times for event pairs (CC ≥ 0.6)
- `event_id_mapping.csv`: Maps synthetic IDs (100000-100022) back to original IDs

## Questions to Consider

1. **Should we include EY uncertainty?** Currently only using EH and EZ from catalog
2. **Should we filter detections by CC threshold before creating .pha?** Or keep all?
3. **Do we need to calculate initial magnitude estimates?** (amplitude ratios, etc.)
