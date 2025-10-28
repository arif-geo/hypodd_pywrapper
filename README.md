# HypoDD Python Wrapper - Complete Guide

**Template Matching → HypoDD Double-Difference Earthquake Relocation**

A comprehensive Python wrapper for running HypoDD earthquake relocation using template matching detection results, without leaving Python.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation & Setup](#installation--setup)
3. [Directory Structure](#directory-structure)
4. [Theoretical Background](#theoretical-background)
5. [Complete Workflow](#complete-workflow)
6. [Command Reference](#command-reference)
7. [Critical Parameters](#critical-parameters)
8. [File Formats](#file-formats)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

---

## Quick Start

### Prerequisites
```bash
conda activate obspy  # Python environment with pandas, numpy
```

### 30-Second Workflow
```bash
cd /path/to/hypodd_pywrapper/scripts

# Option 1: Run full pipeline (default)
python run_hypodd.py

# Option 2: Step-by-step
python run_hypodd.py prepare      # Convert CSV to HypoDD format
python run_hypodd.py ph2dt        # Create differential times
python run_hypodd.py hypodd       # Run relocation
python run_hypodd.py convert      # Convert output to CSV
```

### Available Commands
```bash
python run_hypodd.py help                    # Show help
python run_hypodd.py compile                 # Compile HypoDD Fortran
python run_hypodd.py example                 # Test with example data
python run_hypodd.py prepare                 # Convert CSV to HypoDD inputs
python run_hypodd.py ph2dt                   # Create differential times
python run_hypodd.py hypodd [inp_file]       # Run relocation
python run_hypodd.py convert <file> [sfx]    # Convert .reloc to CSV
python run_hypodd.py compare                 # Compare CC vs catalog methods
```

---

## Installation & Setup

### 1. Clone/Download Repository
```bash
git clone https://github.com/your-repo/hypodd_pywrapper.git
cd hypodd_pywrapper
```

### 2. Compile HypoDD
```bash
cd scripts
python run_hypodd.py compile
```

### 3. Test Installation
```bash
python run_hypodd.py example
```

---

## Directory Structure

```
hypodd_pywrapper/
│
├── 📚 DOCUMENTATION
│   └── README.md                    ← YOU ARE HERE
│
├── 🔧 SCRIPTS
│   ├── run_hypodd.py               ← Main workflow automation
│   ├── csv_hypodd.py                ← Format conversion utilities
│   └── compare_utils.py             ← Comparison utilities
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
│   │           └── hypoDD.sta               (station residuals)
│   │
│   └── hypoDD_outputs/              ← Final CSV outputs
│       ├── hypoDD_cc_cc.csv         (CC method - CSV format)
│       └── hypoDD_cat_cat.csv       (Catalog method - CSV format)
│
└── 🏗️ HYPODD SOURCE
    └── HypoDD-2.1b/
        ├── src/
        │   ├── hypoDD/hypoDD       (executable)
        │   └── ph2dt/ph2dt         (executable)
        └── examples/example2/       (test data)
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

**Problem:** Template matching detections have the **same** announced travel times as templates:
- Template event: 2020-01-01 00:00:00, arrives at station A at 00:00:08 → TT = 8.00s
- Detected event: 2022-01-01 00:00:00, arrives at station A at 00:00:08 → TT = 8.00s

**Result:** When ph2dt computes `dt = TT₁ - TT₂ = 8.00 - 8.00 = 0.00` → No relocation possible!

**Solution:** Use lag times directly (Method 1) or apply corrections (Method 2)

---

## Complete Workflow

### Pipeline Diagram

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

Example: **23 events** → Only **8 relocated**

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

### Basic Usage

| Command | Description | Example |
|---------|-------------|---------|
| **(no args)** | Run full workflow | `python run_hypodd.py` |
| `help` | Show help message | `python run_hypodd.py help` |
| `compile` | Compile HypoDD Fortran | `python run_hypodd.py compile` |
| `example` | Test with example data | `python run_hypodd.py example` |
| `prepare` | Convert CSV to inputs | `python run_hypodd.py prepare` |
| `ph2dt` | Create differential times | `python run_hypodd.py ph2dt` |
| `hypodd [file]` | Run relocation | `python run_hypodd.py hypodd` |
| `convert <file>` | Convert to CSV | `python run_hypodd.py convert hypoDD.reloc` |
| `compare` | Compare methods | `python run_hypodd.py compare` |

### What Each Command Does

| Command | Input Files | Output Files | Purpose |
|---------|-------------|--------------|---------|
| `prepare` | CSV files | `.pha`, `.cc`, `.dat` | Convert to HypoDD format |
| `ph2dt` | `.pha`, `ph2dt.inp` | `dt.ct`, `event.dat` | Create differential times |
| `hypodd` | `dt.ct/dt.cc`, `hypoDD.inp` | `.reloc`, `.loc` | Relocate events |
| `convert` | `.reloc`, `event_id_mapping.csv` | `.csv` | Convert to CSV format |
| `compare` | All | All + comparison stats | Test both methods |

---

## Critical Parameters

### 🔴 Parameters Affecting Event Count (HIGHEST IMPACT)

#### 1. ph2dt.inp - Event Selection

```bash
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
   0      500     15     15     8      8     50
```

| Parameter | Current | Effect | Recommended Range | Impact |
|-----------|---------|--------|-------------------|--------|
| **MINLNK** | 8 | Min. common stations to be neighbors | 4-6 (relaxed)<br>8-10 (strict) | ⭐⭐⭐ HIGHEST |
| **MINOBS** | 8 | Min. observations per event pair saved | 4-6 (relaxed)<br>8-10 (strict) | ⭐⭐⭐ HIGHEST |
| **MAXSEP** | 15 | Max separation (km) | 15-30 | ⭐ Low |
| **MAXDIST** | 500 | Max station distance (km) | 100-500 | ⭐⭐ Medium |

**Why MINLNK and MINOBS are critical:**
- With **star topology** (all events only linked to template), high values exclude weakly-connected events
- Lower values = more events included, but possibly lower quality

#### 2. hypoDD.inp - Event Clustering

```bash
*--- event clustering:
* OBSCC  OBSCT    MINDIST  MAXDIST  MAXGAP
    8     0        -999     -999    -999
```

| Parameter | Current | Effect | Recommended Range | Impact |
|-----------|---------|--------|-------------------|--------|
| **OBSCC** | 8 | Min. CC observations per pair | 4-6 (relaxed)<br>8-10 (strict) | ⭐⭐⭐ HIGH |
| **OBSCT** | 0 | Min. catalog observations | 0 (CC-only)<br>4-8 (catalog) | ⭐⭐ Medium |

### 🟡 Parameters Affecting Quality

#### 3. hypoDD.inp - Data Weighting

```bash
* NITER WTCCP WTCCS WRCC WDCC WTCTP WTCTS WRCT WDCT DAMP
  5     1.0   0.5   -9   -9    0.0   0.0    -9   -9   80
```

| Parameter | Effect | Typical Values | Notes |
|-----------|--------|----------------|-------|
| **WTCCP/WTCCS** | Weight for CC P/S data | 0.5-1.0 | Higher = trust CC more |
| **WTCTP/WTCTS** | Weight for catalog P/S | 0.0 (CC-only)<br>0.5-1.0 (catalog) | Set to 0 for CC-only |
| **WRCC/WRCT** | Residual threshold (sec) | -9 (no limit)<br>3-8 (with limit) | Reject large residuals |
| **WDCC/WDCT** | Max distance for pairs (km) | -9 (no limit)<br>2-10 (with limit) | Tightens in iterations |
| **DAMP** | Damping for LSQR solver | 70-100 | Higher = stable, slower |

### Parameter Tuning Strategies

#### Strategy 1: Maximize Event Count (Aggressive)
```bash
# ph2dt.inp
MINLNK=4  MINOBS=4  MAXSEP=20

# hypoDD.inp
OBSCC=4
```
**Result:** 15-20 events, lower precision

#### Strategy 2: Balance Quality & Quantity (Moderate) ⭐ RECOMMENDED
```bash
# ph2dt.inp
MINLNK=6  MINOBS=6  MAXSEP=20

# hypoDD.inp
OBSCC=6
```
**Result:** 10-15 events, good quality

#### Strategy 3: High Quality Only (Conservative)
```bash
# ph2dt.inp
MINLNK=8  MINOBS=8  MAXSEP=15

# hypoDD.inp
OBSCC=8
```
**Result:** 8-10 events, high precision

---

## File Formats

### CSV Output Format

Relocated events are saved in CSV with these columns:

| Column | Description | Units |
|--------|-------------|-------|
| `event_id` | Original event ID from input | string |
| `hypodd_id` | HypoDD integer ID | integer |
| `latitude` | Relocated latitude | decimal degrees |
| `longitude` | Relocated longitude | decimal degrees |
| `depth` | Relocated depth | km |
| `x_m`, `y_m`, `z_m` | Cartesian offsets from centroid | meters |
| `ex_m`, `ey_m`, `ez_m` | Location errors | meters |
| `year`, `month`, `day` | Origin date | integers |
| `hour`, `minute`, `second` | Origin time | integers, float |
| `n_cc_p`, `n_cc_s` | Number of CC observations | integer |
| `rms_cc` | RMS residual for CC data | milliseconds |
| `cluster_id` | Cluster index | integer |
| `origin_time` | ISO8601 formatted time | string |

### Reading Output in Python

```python
import pandas as pd

# Read relocated events
df = pd.read_csv('hypoDD_outputs/hypoDD_cc_cc.csv')

# Join with original detections
detections = pd.read_csv('input_csvs/detections.csv')
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
```

**Diagnosis:**
1. Check `ph2dt.log`: look for "weakly linked events"
2. High number = events don't have enough connections

**Solutions:**
1. **Lower MINLNK and MINOBS** (e.g., from 8 to 4-6)
2. **Lower OBSCC** in hypoDD.inp
3. **Increase MAXSEP** if events are far apart
4. **Check your CC data** - do events have lag times to neighbors?

### Problem: ERROR READING CONTROL PARAMETERS

**Symptoms:**
```
>>> ERROR READING CONTROL PARAMETERS IN LINE 11
```

**Cause:** Missing parameters in hypoDD v2.0 format

**Solution:** Your .inp file needs ALL required parameters:

```bash
# Event Clustering (Line 11) - needs 5 parameters:
* OBSCC  OBSCT    MINDIST  MAXDIST  MAXGAP
     4     0        -999     -999    -999

# Solution Control (Line 12) - needs 4 parameters:
*  ISTART  ISOLV  IAQ  NSET
    2        2     0     5
```

**Quick fix:**
```bash
cp HypoDD-2.1b/examples/example2/hypoDD.inp your_run/
# Then edit file paths and parameters
```

### Problem: hypoDD Runs But No Output

**Symptoms:**
```
starting hypoDD...
(no further output)
```

**Cause:** HypoDD cannot handle absolute paths for .inp file

**Solution:** The Python wrapper automatically handles this, but if running manually:
```bash
# WRONG:
/path/to/hypoDD /absolute/path/to/hypoDD.inp

# CORRECT:
cd /path/to/run_dir
/path/to/hypoDD hypoDD.inp
```

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

---

## Advanced Topics

### Running Multiple Parameter Tests

```python
# test_parameters.py
import subprocess
import os

param_sets = [
    {'name': 'aggressive', 'minlnk': 4, 'minobs': 4, 'obscc': 4},
    {'name': 'moderate',   'minlnk': 6, 'minobs': 6, 'obscc': 6},
    {'name': 'conservative', 'minlnk': 8, 'minobs': 8, 'obscc': 8},
]

for params in param_sets:
    print(f"Testing: {params['name']}")
    
    # Update parameters in .inp files
    # ... (edit files) ...
    
    # Run pipeline
    subprocess.run(['python', 'run_hypodd.py', 'ph2dt'])
    subprocess.run(['python', 'run_hypodd.py', 'hypodd'])
    
    # Save results
    os.rename('hypoDD.reloc', f'hypoDD_{params["name"]}.reloc')
```

### Understanding Star Topology

Template matching creates a **star network**:

```
Detection 1 ----\
Detection 2 -----\
Detection 3 -------> Template Event
Detection 4 -----/
Detection 5 ----/
```

**Limitation:** Events only connected to template, not to each other.

**Solutions:**
1. **Lower thresholds** to include weak links
2. **Cross-correlate detections** with each other (advanced)
3. **Use multiple templates** (if available)
4. **Accept fewer relocations** with high-quality constraints

### Comparing Methods

```bash
# Run full comparison
python run_hypodd.py compare

# Typical differences: 100-300m (acceptable)
```

### Batch Processing

```bash
# Process multiple datasets
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
4. **Don't expect 100% of events to relocate** (star topology)
5. **Don't modify .reloc files** manually
6. **Don't delete event_id_mapping.csv**

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
| `event_id_mapping.csv` | ID lookup | ❌ DO NOT DELETE |

### Parameter Quick Reference

| Want More Events? | ↓ Lower These | Values |
|-------------------|---------------|--------|
| MINLNK | ↓ | 4-8 |
| MINOBS | ↓ | 4-8 |
| OBSCC | ↓ | 4-8 |

| Want Higher Quality? | ↑ Raise These | Values |
|----------------------|---------------|--------|
| MINLNK | ↑ | 8-12 |
| MINOBS | ↑ | 8-12 |
| OBSCC | ↑ | 8-12 |

### Quick Commands

```bash
# Full workflow
python run_hypodd.py

# Individual steps
python run_hypodd.py prepare && \
python run_hypodd.py ph2dt && \
python run_hypodd.py hypodd && \
python run_hypodd.py convert

# Check event count
grep "events selected" data/runs/*/ph2dt.log
```

---

## References & Credits

- **HypoDD**: Waldhauser & Ellsworth (2000), *BSSA* - Double-Difference Earthquake Location
- **Template Matching**: Various (FMF, EQcorrscan, etc.)
- **Implementation**: Arif & Claude (October 2025)
- **HypoDD Manual**: See `HypoDD-2.1b/Doc/`

---

**Last Updated:** October 28, 2025  
**Version:** 3.0 (Consolidated)  
**Python Version:** 3.10+  
**Status:** ✅ Production Ready
