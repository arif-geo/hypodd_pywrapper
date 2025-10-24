# HypoDD Python Wrapper - Complete Guide & Cookbook

**Template Matching → HypoDD Double-Difference Relocation**

*A comprehensive guide for running earthquake relocation using template matching detections*

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Theoretical Background](#theoretical-background)
3. [File Structure](#file-structure)
4. [Workflow Overview](#workflow-overview)
5. [Command Reference](#command-reference)
6. [Critical Parameters Guide](#critical-parameters-guide)
7. [Output Format](#output-format)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Topics](#advanced-topics)

---

## Quick Start

### Prerequisites
```bash
# Required Python packages
conda activate obspy  # or your Python environment with:
# - pandas, numpy, obspy (optional)
```

### 30-Second Workflow
```bash
cd /path/to/hypodd_pywrapper/scripts

# Option 1: Run everything with comparison
python run_hypodd.py test_comparison

# Option 2: Step-by-step
python run_hypodd.py prepare      # Convert CSV to HypoDD format
python run_hypodd.py ph2dt        # Create differential times
python run_hypodd.py hypodd       # Run relocation
python run_hypodd.py convert      # Convert output to CSV
```

### Expected Output
```
✅ 8 events relocated (out of 23 total)
✅ CSV files created in data/hypoDD_outputs/
✅ Relocation files in data/runs/run_detections_2020/
```

---

## Theoretical Background

### The Template Matching → HypoDD Connection

**What Template Matching Gives You:**
- **Lag time** between detected event and template at each station
- **Cross-correlation coefficient** (quality measure)

**What HypoDD Needs:**
- **Differential times** between event pairs
- **Weights** for each differential time

**Key Insight:** 
```
lag_time = detected_arrival - template_arrival = DIFFERENTIAL TIME!
```

### Two Equivalent Methods

#### Method 1: Cross-Correlation Only (IDAT=1) ⭐ RECOMMENDED
- Put lag times directly in `dt.cc` file
- HypoDD uses them as differential times
- ✅ Theoretically correct
- ✅ Computationally efficient

#### Method 2: Catalog Only (IDAT=2)
- Template: `TT = original_travel_time`
- Detection: `TT = original_travel_time + lag_time`
- ph2dt computes: `dt = TT_det - TT_temp`
- ✅ Mathematically equivalent
- ⚠️ Indirect (extra processing step)

**Result:** Both produce similar locations (~100-300m differences due to numerical precision)

### Why Standard Catalog-Only Fails

**Problem:** In template matching, detected events have the **same** announced travel times as templates:
- Template event: 2020-01-01 00:00:00, arrives at station A at 00:00:08 → TT = 8.00s
- Detected event: 2022-01-01 00:00:00, arrives at station A at 00:00:08 → TT = 8.00s

**Result:** When ph2dt computes `dt = TT₁ - TT₂ = 8.00 - 8.00 = 0.00` → No relocation possible!

**Solution:** Use lag times directly (Method 1) or apply corrections (Method 2)

---

## File Structure

```
hypodd_pywrapper/
│
├── 📚 DOCUMENTATION
│   ├── HYPODD_GUIDE.md              ← YOU ARE HERE (complete guide)
│   ├── README_IMPLEMENTATION.md     ← Technical implementation details
│   ├── README_WORKFLOW.md           ← Original workflow notes
│   └── FILE_STRUCTURE_COMPLETE.md   ← Detailed file inventory
│
├── 🔧 SCRIPTS
│   ├── run_hypodd.py               ← Main workflow automation
│   └── csv_to_hypodd.py            ← Format conversion utilities
│
├── 📊 DATA
│   ├── input_csvs/                  ← Your input data
│   │   ├── nc73818801_fmf_detections_phase_picks.csv
│   │   ├── stations_*.csv
│   │   └── yoon_shelly_ferndale-*.csv
│   │
│   ├── runs/                        ← Run directories (one per experiment)
│   │   └── run_detections_2020/
│   │       ├── 📥 INPUT FILES
│   │       │   ├── station.dat              (station locations)
│   │       │   ├── detections.pha           (phase picks - standard)
│   │       │   ├── detections_cat.pha       (phase picks - lag corrected)
│   │       │   ├── detections.cc            (cross-correlation data)
│   │       │   ├── event_id_mapping.csv     (ID lookup table)
│   │       │   ├── ph2dt.inp                (ph2dt configuration) ⚙️
│   │       │   ├── hypoDD_cc.inp            (HypoDD config - CC method) ⚙️
│   │       │   └── hypoDD_cat.inp           (HypoDD config - catalog method) ⚙️
│   │       │
│   │       └── 📤 OUTPUT FILES
│   │           ├── dt.ct                    (catalog differential times)
│   │           ├── event.dat                (event list)
│   │           ├── event.sel                (selected events)
│   │           ├── station.sel              (selected stations)
│   │           ├── hypoDD.loc               (original locations)
│   │           ├── hypoDD_cc.reloc          (relocated - CC method)
│   │           ├── hypoDD_cat.reloc         (relocated - catalog method)
│   │           ├── hypoDD.sta               (station residuals)
│   │           └── ph2dt.log                (ph2dt log file)
│   │
│   └── hypoDD_outputs/              ← Final CSV outputs
│       ├── hypoDD_cc_cc.csv         (CC method - CSV format)
│       └── hypoDD_cat_cat.csv       (Catalog method - CSV format)
│
└── 🏗️ HYPODD SOURCE
    └── HypoDD-2.1b/
        ├── src/                     (Fortran source code)
        │   ├── hypoDD/hypoDD       (executable)
        │   └── ph2dt/ph2dt         (executable)
        └── examples/example2/       (test data)
```

---

## Workflow Overview

### Full Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. TEMPLATE MATCHING (Done externally)                      │
│    ↓ Produces: detections with lag times & CC values        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PREPARE INPUTS                                           │
│    Command: python run_hypodd.py prepare                    │
│    ↓ Creates:                                               │
│      - station.dat        (station locations)               │
│      - detections.pha     (phase picks)                     │
│      - detections.cc      (lag times as differential times) │
│      - event_id_mapping.csv (ID lookup)                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CREATE DIFFERENTIAL TIMES                                │
│    Command: python run_hypodd.py ph2dt                      │
│    ↓ Runs: ph2dt using ph2dt.inp configuration             │
│    ↓ Creates:                                               │
│      - dt.ct             (catalog differential times)        │
│      - event.dat         (event list)                       │
│      - event.sel         (selected events after filtering)  │
│      - station.sel       (selected stations)                │
│    ⚠️  FILTERING HAPPENS HERE - Check parameters!           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. RUN RELOCATION                                           │
│    Command: python run_hypodd.py hypodd                     │
│    ↓ Runs: hypoDD using hypoDD.inp configuration           │
│    ↓ Creates:                                               │
│      - hypoDD.reloc      (relocated event locations)        │
│      - hypoDD.loc        (original locations for reference) │
│      - hypoDD.sta        (station residuals)                │
│    ⚠️  MORE FILTERING HAPPENS HERE - Check OBSCC!           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. CONVERT TO CSV                                           │
│    Command: python run_hypodd.py convert                    │
│    ↓ Creates: hypoDD_*.csv with original event IDs         │
└─────────────────────────────────────────────────────────────┘
```

### Understanding Event Filtering

Your data: **23 events** → Only **8 relocated**

```
INPUT: 23 events
   ↓
ph2dt filters based on connectivity
   ↓ MINLNK=8, MINOBS=8 (TOO STRICT!)
   ↓
8 events selected (weakly linked events removed)
   ↓
HypoDD clusters events
   ↓ OBSCC=8 (minimum observations per pair)
   ↓
8 events in 1 cluster → RELOCATED ✅
15 events isolated → NOT RELOCATED ❌
```

---

## Command Reference

### Basic Commands

```bash
# Compile HypoDD (first time only)
python run_hypodd.py compile

# Test with HypoDD examples
python run_hypodd.py example

# Prepare input files from CSV
python run_hypodd.py prepare

# Prepare with lag corrections (catalog-only method)
python run_hypodd.py prepare_catalog

# Run ph2dt (create differential times)
python run_hypodd.py ph2dt

# Run HypoDD relocation
python run_hypodd.py hypodd

# Convert .reloc to CSV
python run_hypodd.py convert

# Convert specific file
python run_hypodd.py convert path/to/file.reloc _suffix
```

### Advanced Commands

```bash
# Run complete comparison test (CC vs Catalog methods)
python run_hypodd.py test_comparison

# Show help
python run_hypodd.py help
```

### What Each Command Does

| Command | Input Files | Output Files | Purpose |
|---------|-------------|--------------|---------|
| `prepare` | CSV files | `.pha`, `.cc`, `.dat` | Convert to HypoDD format |
| `prepare_catalog` | CSV files | `detections_cat.pha` | Apply lag corrections |
| `ph2dt` | `.pha`, `ph2dt.inp` | `dt.ct`, `event.dat` | Create differential times |
| `hypodd` | `dt.ct/dt.cc`, `hypoDD.inp` | `.reloc`, `.loc` | Relocate events |
| `convert` | `.reloc`, `event_id_mapping.csv` | `.csv` | Convert to CSV format |
| `test_comparison` | All | All + comparison stats | Test both methods |

---

## Critical Parameters Guide

### 🔴 Parameters Affecting Event Count

#### **1. ph2dt.inp - Event Selection (HIGHEST IMPACT)**

```bash
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
   0      500     15     15     8      8     50
```

| Parameter | Current | Effect | Recommended Range | Impact on Event Count |
|-----------|---------|--------|-------------------|----------------------|
| **MINLNK** | 8 | Min. common stations to be neighbors | 4-6 (relaxed)<br>8-10 (strict) | ⭐⭐⭐ HIGHEST |
| **MINOBS** | 8 | Min. observations per event pair saved | 4-6 (relaxed)<br>8-10 (strict) | ⭐⭐⭐ HIGHEST |
| **MAXNGH** | 15 | Max neighbors per event | 15-20 | ⭐ Low |
| **MAXSEP** | 15 | Max separation (km) | 15-30 | ⭐ Low (template matching) |
| **MAXDIST** | 500 | Max station distance (km) | 100-500 | ⭐⭐ Medium |

**Why MINLNK and MINOBS are critical:**
- With **star topology** (all events only linked to template), high values exclude weakly-connected events
- Lower values = more events included, but possibly lower quality

#### **2. hypoDD.inp - Clustering (MEDIUM IMPACT)**

```bash
*--- event clustering:
* OBSCC  OBSCT
    8     0
```

| Parameter | Current | Effect | Recommended Range | Impact |
|-----------|---------|--------|-------------------|--------|
| **OBSCC** | 8 | Min. CC observations per pair for clustering | 4-6 (relaxed)<br>8-10 (strict) | ⭐⭐⭐ HIGH |
| **OBSCT** | 0 | Min. catalog observations (not used for CC-only) | 0 (CC-only)<br>4-8 (catalog) | ⭐⭐ Medium |

### 🟡 Parameters Affecting Relocation Quality

#### **3. hypoDD.inp - Data Weighting**

```bash
* NITER WTCCP WTCCS WRCC WDCC WTCTP WTCTS WRCT WDCT DAMP
  5     1.0   0.5   -9   -9    0.0   0.0    -9   -9   80
  5     1.0   0.5   -9    5    0.0   0.0    -9   -9   90
  5     1.0   0.5    6    5    0.0   0.0    -9   -9   90
```

| Parameter | Effect | Typical Values | Notes |
|-----------|--------|----------------|-------|
| **WTCCP/WTCCS** | Weight for CC P/S data | 0.5-1.0 | Higher = trust CC more |
| **WTCTP/WTCTS** | Weight for catalog P/S data | 0.0 (CC-only)<br>0.5-1.0 (catalog) | Set to 0 for CC-only |
| **WRCC/WRCT** | Residual threshold (seconds) | -9 (no limit)<br>3-8 (with limit) | Reject picks with large residuals |
| **WDCC/WDCT** | Max distance for pairs (km) | -9 (no limit)<br>2-10 (with limit) | Tightens in later iterations |
| **DAMP** | Damping for LSQR solver | 70-100 | Higher = more stable, slower convergence |

### 🟢 Less Critical Parameters

| Parameter | File | Typical Values | Effect |
|-----------|------|----------------|--------|
| **IDAT** | hypoDD.inp | 1 (CC), 2 (catalog), 3 (both) | Data type selection |
| **IPHA** | hypoDD.inp | 1 (P), 2 (S), 3 (both) | Phase type selection |
| **ISOLV** | hypoDD.inp | 1 (SVD), 2 (LSQR) | Solver type |
| **ISTART** | hypoDD.inp | 1 (single), 2 (network) | Starting locations |

---

## Parameter Tuning Strategies

### Strategy 1: Maximize Event Count (Aggressive)

**Goal:** Relocate as many events as possible

```bash
# ph2dt.inp
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
   0      500     20     20     4      4     50

# hypoDD_cc.inp
* OBSCC  OBSCT
    4     0
```

**Expected Result:**
- ✅ Relocate 15-20 events (instead of 8)
- ⚠️ May include poorly constrained events
- ⚠️ Lower precision

**Use when:** Exploring data, preliminary analysis

### Strategy 2: Balance Quality & Quantity (Moderate)

**Goal:** Good compromise

```bash
# ph2dt.inp
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
   0      500     20     20     6      6     50

# hypoDD_cc.inp
* OBSCC  OBSCT
    6     0
```

**Expected Result:**
- ✅ Relocate 10-15 events
- ✅ Better quality than aggressive
- ✅ More events than conservative

**Use when:** Standard analysis, publication-quality

### Strategy 3: High Quality Only (Conservative - Current)

**Goal:** Only well-constrained events

```bash
# ph2dt.inp
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
   0      500     15     15     8      8     50

# hypoDD_cc.inp
* OBSCC  OBSCT
    8     0
```

**Expected Result:**
- ✅ Relocate 8-10 events
- ✅ High precision
- ⚠️ Many events excluded

**Use when:** Final publication, precise locations critical

### Quick Parameter Test Workflow

```bash
# 1. Backup original configs
cp ph2dt.inp ph2dt_original.inp
cp hypoDD_cc.inp hypoDD_cc_original.inp

# 2. Edit parameters (use your favorite editor)
nano ph2dt.inp
nano hypoDD_cc.inp

# 3. Re-run pipeline
python run_hypodd.py ph2dt
python run_hypodd.py hypodd
python run_hypodd.py convert

# 4. Check results
# Look for: "# events after dtime match" in output
# Compare with previous runs

# 5. Repeat with different parameters
```

---

## Output Format

### CSV Output Structure

The relocated events are saved in CSV format with the following columns:

```csv
event_id,hypodd_id,latitude,longitude,depth,x_m,y_m,z_m,ex_m,ey_m,ez_m,...
nc73818801_20200318_231602,100001,40.465145,-124.477376,29.678,28.3,-61.4,-102.3,...
```

| Column | Description | Units | Notes |
|--------|-------------|-------|-------|
| `event_id` | Original event ID from input CSV | string | Use for joining with original data |
| `hypodd_id` | HypoDD integer ID | integer | 100000+ |
| `latitude` | Relocated latitude | decimal degrees | WGS84 |
| `longitude` | Relocated longitude | decimal degrees | WGS84 |
| `depth` | Relocated depth | km | Positive down |
| `x_m`, `y_m`, `z_m` | Cartesian offsets from cluster centroid | meters | East, North, Down |
| `ex_m`, `ey_m`, `ez_m` | Location errors | meters | NOT meaningful with LSQR solver |
| `year`, `month`, `day` | Origin date | integers | - |
| `hour`, `minute`, `second` | Origin time | integers, float | - |
| `magnitude` | Magnitude | float | 0.0 if not available |
| `n_cc_p`, `n_cc_s` | Number of CC P & S observations | integer | Data quality indicator |
| `n_cat_p`, `n_cat_s` | Number of catalog P & S observations | integer | Usually 0 for CC-only |
| `rms_cc` | RMS residual for CC data | milliseconds | Lower = better fit |
| `rms_cat` | RMS residual for catalog data | milliseconds | -9.0 if not used |
| `cluster_id` | Cluster index | integer | Usually 1 |
| `origin_time` | ISO8601 formatted time | string | For convenience |

### Reading Output in Python

```python
import pandas as pd

# Read relocated events
df = pd.read_csv('hypoDD_outputs/hypoDD_cc_cc.csv')

# Join with original detections
detections = pd.read_csv('input_csvs/nc73818801_fmf_detections_phase_picks.csv')
merged = detections.merge(df, on='event_id', how='inner')

# Plot relocations
import matplotlib.pyplot as plt
plt.scatter(df['longitude'], df['latitude'], c=df['depth'], cmap='viridis_r')
plt.colorbar(label='Depth (km)')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title(f'Relocated Events (n={len(df)})')
plt.show()
```

---

## Troubleshooting

### Problem: Too Few Events Relocated

**Symptoms:**
```
# events total = 23
# events selected = 8
→ Only 8 events relocated
```

**Diagnosis:**
1. Check ph2dt.log: `> weakly linked events = X`
2. High number = events don't have enough connections

**Solutions:**
1. **Lower MINLNK and MINOBS** (see Parameter Strategies above)
2. **Lower OBSCC** in hypoDD.inp
3. **Increase MAXSEP** if events are far apart
4. **Check your CC data** - do events have lag times to multiple neighbors?

### Problem: No Events Relocated

**Symptoms:**
```
# events after dtime match = 0
→ No output files created
```

**Solutions:**
1. **Check dt.cc file exists** and has data
2. **Verify IDAT=1** in hypoDD.inp for CC-only mode
3. **Lower ALL connectivity thresholds** (MINLNK=2, MINOBS=2, OBSCC=2)
4. **Check for errors** in ph2dt.log and hypoDD.log

### Problem: Poor Convergence

**Symptoms:**
```
RMS not decreasing
NaN values in output
```

**Solutions:**
1. **Increase DAMP** (try 90-100)
2. **Check initial locations** - too far from truth?
3. **Reduce WTCCP/WTCCS** to weight data less aggressively
4. **Try ISOLV=1 (SVD)** instead of LSQR

### Problem: Large Location Uncertainties

**Symptoms:**
```
ex_m, ey_m, ez_m > 1000 meters
```

**Notes:**
- **LSQR errors are NOT meaningful** (see Paige & Saunders documentation)
- Use RMS residuals and iteration convergence instead
- Compare CC vs Catalog methods to assess consistency

### Problem: ID Mapping Issues

**Symptoms:**
```
KeyError in reloc_to_csv
Missing event IDs in output
```

**Solutions:**
1. **Verify event_id_mapping.csv exists** in run directory
2. **Check column names**: should be `original_id` & `synthetic_id` OR `event_id` & `hypodd_id`
3. **Re-run prepare step** to regenerate mapping

---

## Advanced Topics

### Running Multiple Parameter Tests

Create a test script:

```python
# test_parameters.py
import subprocess
import shutil
import os

# Define parameter sets to test
param_sets = [
    {'name': 'aggressive', 'minlnk': 4, 'minobs': 4, 'obscc': 4},
    {'name': 'moderate',   'minlnk': 6, 'minobs': 6, 'obscc': 6},
    {'name': 'conservative', 'minlnk': 8, 'minobs': 8, 'obscc': 8},
]

for params in param_sets:
    print(f"\n{'='*60}")
    print(f"Testing: {params['name']}")
    print(f"{'='*60}")
    
    # Update ph2dt.inp
    with open('ph2dt.inp', 'r') as f:
        content = f.read()
    # ... modify content with params ...
    with open('ph2dt.inp', 'w') as f:
        f.write(content)
    
    # Run pipeline
    subprocess.run(['python', 'run_hypodd.py', 'ph2dt'])
    subprocess.run(['python', 'run_hypodd.py', 'hypodd'])
    
    # Save results
    shutil.copy('hypoDD.reloc', f'hypoDD_{params["name"]}.reloc')
```

### Understanding Star Topology Limitations

Your template matching creates a **star network**:

```
Detection 1 ----\
Detection 2 -----\
Detection 3 -------> Template Event
Detection 4 -----/
Detection 5 ----/
```

**Problem:** Events only connected to template, not to each other.

**Solutions:**
1. **Lower thresholds** to include weak links
2. **Cross-correlate detections** with each other (advanced)
3. **Use multiple templates** (if available)
4. **Accept fewer relocations** with high-quality constraints

### Comparing Methods (CC vs Catalog)

```bash
# Run full comparison
python run_hypodd.py test_comparison

# Outputs:
# - hypoDD_cc.reloc (CC method)
# - hypoDD_cat.reloc (catalog method)
# - Comparison statistics

# Typical differences: 100-300m (acceptable)
```

### Batch Processing Multiple Datasets

```bash
# Structure:
data/runs/
  ├── run_2020/
  ├── run_2021/
  └── run_2022/

# Process each:
for run in run_2020 run_2021 run_2022; do
    cd data/runs/$run
    python ../../scripts/run_hypodd.py ph2dt
    python ../../scripts/run_hypodd.py hypodd
    python ../../scripts/run_hypodd.py convert
done
```

---

## Best Practices

### ✅ DO

1. **Start conservative** → Relax parameters gradually
2. **Check logs** after each step (ph2dt.log, hypoDD.log)
3. **Version control** your .inp files
4. **Document parameter choices** in run directory
5. **Compare methods** (CC vs catalog) to assess consistency
6. **Plot results** to visually inspect relocations
7. **Keep original data** - never overwrite input CSVs

### ❌ DON'T

1. **Don't blindly accept default parameters**
2. **Don't ignore filtering messages** in logs
3. **Don't trust error estimates** from LSQR (ex_m, ey_m, ez_m)
4. **Don't expect 100% of events to relocate** (star topology limitation)
5. **Don't modify .reloc files** manually (will break CSV conversion)
6. **Don't delete event_id_mapping.csv** (needed for CSV conversion)

---

## Quick Reference Card

### Essential Files

| File | Purpose | Edit? |
|------|---------|-------|
| `ph2dt.inp` | ph2dt parameters | ✅ YES - Tune MINLNK, MINOBS |
| `hypoDD.inp` | HypoDD parameters | ✅ YES - Tune OBSCC |
| `station.dat` | Station locations | ❌ Auto-generated |
| `detections.pha` | Phase picks | ❌ Auto-generated |
| `detections.cc` | Lag times | ❌ Auto-generated |
| `event_id_mapping.csv` | ID lookup | ❌ Auto-generated, DO NOT DELETE |

### Critical Parameters Cheat Sheet

| Want More Events? | ↓ Lower These | Typical Values |
|-------------------|---------------|----------------|
| ph2dt: MINLNK | ↓ | 4-8 |
| ph2dt: MINOBS | ↓ | 4-8 |
| hypoDD: OBSCC | ↓ | 4-8 |

| Want Higher Quality? | ↑ Raise These | Typical Values |
|----------------------|---------------|----------------|
| ph2dt: MINLNK | ↑ | 8-12 |
| ph2dt: MINOBS | ↑ | 8-12 |
| hypoDD: OBSCC | ↑ | 8-12 |

### Quick Commands

```bash
# Full workflow
python run_hypodd.py test_comparison

# Individual steps
python run_hypodd.py prepare && python run_hypodd.py ph2dt && python run_hypodd.py hypodd && python run_hypodd.py convert

# Check how many events will be relocated
grep "events selected" data/runs/*/ph2dt.log
grep "Clustered events" data/runs/*/hypoDD.log
```

---

## References & Credits

- **HypoDD**: Waldhauser & Ellsworth (2000), *BSSA* - Double-Difference Earthquake Location
- **Template Matching**: Various (FMF, EQcorrscan, etc.)
- **Implementation**: Arif & Claude (October 2025)
- **HypoDD Manual**: See `HypoDD-2.1b/Doc/`

---

## Support & Issues

**Common Issues:**
- Check this guide's [Troubleshooting](#troubleshooting) section
- Review [Critical Parameters](#critical-parameters-guide)
- Examine log files: `ph2dt.log`, `hypoDD.log`

**For Development:**
- GitHub: [Your repository]
- Contact: [Your contact]

---

**Last Updated:** October 22, 2025  
**Version:** 2.0  
**Guide Type:** Complete Cookbook & Reference

