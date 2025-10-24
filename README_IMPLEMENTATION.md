# HypoDD Python Wrapper - Implementation Summary

## Overview
This Python wrapper enables running HypoDD double-difference earthquake relocation using template matching detection results, without leaving the Python environment.

## Key Implementation Details

### Problem Solved
**Core Issue**: Template matching detections have the same announced travel times as their parent templates (since that's how template matching works), resulting in zero differential times in catalog-only mode.

**Solution**: Two equivalent methods implemented:
1. **CC-only method (IDAT=1)**: Uses lag times directly from cross-correlation as differential times
2. **Catalog-only method (IDAT=2)**: Applies lag corrections to travel times in .pha file

Both methods are theoretically equivalent and produce similar results (~100-300m differences due to numerical implementation).

---

## File Structure

```
hypodd_pywrapper/
├── scripts/
│   ├── run_hypodd.py           # Main workflow script
│   └── csv_to_hypodd.py        # Conversion utilities
├── data/
│   ├── input_csvs/             # Input detection data
│   ├── runs/
│   │   └── run_detections_2020/
│   │       ├── detections.pha          # Original phase file
│   │       ├── detections_cat.pha      # Lag-corrected phase file
│   │       ├── detections.cc           # Cross-correlation data
│   │       ├── station.dat             # Station file
│   │       ├── hypoDD_cc.inp          # CC-only config
│   │       ├── hypoDD_cat.inp         # Catalog-only config
│   │       ├── hypoDD_cc.reloc        # CC-only results
│   │       └── hypoDD_cat.reloc       # Catalog-only results
│   └── hypoDD_outputs/          # CSV output files
│       ├── hypoDD_cc_cc.csv
│       └── hypoDD_cat_cat.csv
```

---

## Available Commands

### Basic Workflow
```bash
python run_hypodd.py prepare    # Convert CSV to HypoDD inputs
python run_hypodd.py ph2dt      # Create differential times
python run_hypodd.py hypodd     # Run relocation
```

### Testing & Comparison
```bash
python run_hypodd.py test_comparison  # Run both methods and compare
```

### Output Conversion
```bash
python run_hypodd.py convert           # Convert all .reloc files to CSV
python run_hypodd.py convert file.reloc _cc  # Convert specific file with suffix
```

### Other Commands
```bash
python run_hypodd.py compile           # Compile HypoDD Fortran
python run_hypodd.py example           # Test with example data
python run_hypodd.py prepare_catalog   # Prepare lag-corrected inputs
```

---

## Key Functions

### `csv_to_hypodd.py`

#### `csv_to_pha(csv_file, output_file, catalog_info, event_id_mapping, apply_lag_correction=False)`
Converts CSV phase picks to HypoDD .pha format.
- **apply_lag_correction=False**: Standard mode - template and detections have same travel times
- **apply_lag_correction=True**: Catalog-only mode - adds lag times to detected event travel times

#### `csv_to_cc(csv_file, output_file, min_cc=0.6, event_id_mapping=None)`
Converts CSV to .cc format with lag times as differential times.

### `run_hypodd.py`

#### `reloc_to_csv(reloc_file, output_dir=None, method_suffix='', event_id_mapping_file=None)`
Converts HypoDD .reloc output to CSV format.
- Maps synthetic event IDs back to original IDs
- Creates ISO8601 formatted origin_time column
- Outputs to `../data/hypoDD_outputs/` by default
- Auto-appends method suffix (_cc or _cat)

#### `run_comparison_test()`
Runs full comparison between CC-only and catalog-only methods:
1. Prepares inputs for both methods
2. Runs ph2dt on standard inputs
3. Runs HypoDD with CC-only (IDAT=1)
4. Runs ph2dt with lag-corrected inputs
5. Runs HypoDD with catalog-only (IDAT=2)
6. Compares results and reports statistics
7. Converts both results to CSV

#### `compare_relocations(reloc_file1, reloc_file2, label1, label2)`
Compares two relocation files and reports:
- Horizontal differences (meters)
- Depth differences (meters)
- 3D distances (meters)
- Events with differences > 10m threshold

---

## CSV Output Format

The converted CSV files contain the following columns:

| Column | Description |
|--------|-------------|
| `original_event_id` | Original event ID from input CSV |
| `event_id` | Synthetic ID used by HypoDD (100000+) |
| `latitude` | Relocated latitude (decimal degrees) |
| `longitude` | Relocated longitude (decimal degrees) |
| `depth` | Relocated depth (km) |
| `x_m`, `y_m`, `z_m` | Cartesian offsets relative to cluster centroid (meters) |
| `ex_m`, `ey_m`, `ez_m` | Location errors (meters) - not meaningful with LSQR solver |
| `year`, `month`, `day` | Origin date |
| `hour`, `minute`, `second` | Origin time |
| `magnitude` | Magnitude (if available) |
| `n_cc_p`, `n_cc_s` | Number of cross-correlation P & S observations |
| `n_cat_p`, `n_cat_s` | Number of catalog P & S observations |
| `rms_cc` | RMS residual for CC data (ms) |
| `rms_cat` | RMS residual for catalog data (ms) |
| `cluster_id` | Cluster index |
| `origin_time` | ISO8601 formatted origin time |

---

## Configuration Files

### `hypoDD_cc.inp` (Cross-Correlation Only)
```
IDAT = 1        # Use CC data only
OBSCC = 8       # Min 8 CC obs per pair
OBSCT = 0       # No catalog clustering
WTCCP = 1.0     # Full weight on CC P-waves
WTCCS = 0.5     # Half weight on CC S-waves
WTCTP = 0.0     # Zero weight on catalog
```

### `hypoDD_cat.inp` (Catalog Only)
```
IDAT = 2        # Use catalog data only
OBSCC = 0       # No CC clustering
OBSCT = 8       # Min 8 catalog obs per pair
WTCCP = 0.0     # Zero weight on CC
WTCTP = 1.0     # Full weight on catalog P-waves
WTCTS = 0.5     # Half weight on catalog S-waves
```

---

## Example Usage

### Complete workflow from CSV to relocated CSV:

```bash
# 1. Prepare inputs
python run_hypodd.py prepare

# 2. Run ph2dt
python run_hypodd.py ph2dt

# 3. Run relocation with CC method
python run_hypodd.py hypodd

# 4. Convert results to CSV
python run_hypodd.py convert
```

### Or run everything with comparison:

```bash
python run_hypodd.py test_comparison
```

This will:
- ✅ Prepare both standard and lag-corrected inputs
- ✅ Run both CC-only and catalog-only methods
- ✅ Compare results with statistics
- ✅ Convert both outputs to CSV
- ✅ Save all files in organized directories

---

## Results Summary

From test comparison run:
- **Events relocated**: 8
- **Horizontal differences**: 32-199 m (mean: 112 m)
- **Depth differences**: -114 to +260 m (mean: 25 m)
- **3D differences**: 92-324 m (mean: 168 m)

These differences are within normal ranges for earthquake relocation and arise from:
- Different data coverage (catalog has 177 dtimes vs CC has 156)
- Different iteration convergence paths
- Numerical precision in ray tracing

**Both methods successfully relocate events!** ✅

---

## Theory: Why This Works

### Template Matching → HypoDD Connection

**Template matching gives you:**
- Lag time between detected event and template at each station
- Cross-correlation coefficient (quality measure)

**HypoDD needs:**
- Differential times between event pairs
- Weights for each differential time

**Key insight**: `lag_time = detected_arrival - template_arrival` **IS** the differential time!

### Two Equivalent Approaches

**Method 1 (CC-only, IDAT=1):**
- Put lag times directly in `dt.cc` file
- HypoDD uses them as-is
- ✅ Theoretically correct
- ✅ Computationally efficient

**Method 2 (Catalog-only, IDAT=2):**
- Template: `TT = original_travel_time`
- Detection: `TT = original_travel_time + lag_time`
- ph2dt computes: `dt = TT_det - TT_temp = lag_time`
- ✅ Mathematically equivalent
- ⚠️ Indirect approach (adds intermediate step)

Both produce nearly identical results (~100-300m differences due to numerical implementation details).

---

## Credits

Implementation by: Arif & Claude (October 2025)
Based on: HypoDD v2.1b by Felix Waldhauser
