# HypoDD Input File Generator 

## Overview

Python module to programmatically create HypoDD input files (.inp) instead of manually editing text files.

## Module: `create_hypodd_inputs.py`

### Main Functions

#### 1. `create_ph2dt_inp()` - Create ph2dt configuration

```python
from create_hypodd_inputs import create_ph2dt_inp

create_ph2dt_inp(
    output_file='ph2dt.inp',
    station_file='station.dat',
    phase_file='detections.pha',
    minwght=0.0,      # Min pick weight [0-1]
    maxdist=500.0,    # Max distance (km) between event-station
    maxsep=15.0,      # Max separation (km) between event pairs
    maxngh=15,        # Max neighbors per event
    minlnk=8,         # Min links to define neighbor
    minobs=8,         # Min links per pair saved
    maxobs=50         # Max links per pair saved
)
```

**Key Parameters:**
- `maxsep`: Larger = more distant events can be paired (but less similar)
- `minlnk`: Smaller = more events included (but weaker links)
- `maxdist`: Station distance cutoff

#### 2. `create_hypodd_inp()` - Create hypoDD configuration

```python
from create_hypodd_inputs import create_hypodd_inp

create_hypodd_inp(
    output_file='hypoDD.inp',
    data_files={
        'dt_ct': 'dt.ct',
        'dt_cc': 'dt.cc',  # Optional
        'event': 'event.dat',
        'station': 'station.dat'
    },
    output_dir='.',
    obscc=0,          # Use cross-correlation (0=no, 1=yes)
    obsct=1,          # Use catalog data (0=no, 1=yes)
    wtccp=1.0,        # Weight for CC P-waves
    wtccs=0.5,        # Weight for CC S-waves
    wtctp=1.0,        # Weight for catalog P-waves
    wtcts=0.5,        # Weight for catalog S-waves
    niter=5,          # Number of iterations
    damp=100.0,       # Damping parameter
    mod_v=[6.0],      # P-wave velocity (km/s)
    mod_ratio=[1.73]  # Vp/Vs ratio
)
```

### Preset Configurations

Quick-start presets for common scenarios:

```python
from create_hypodd_inputs import (
    create_ph2dt_inp_default,
    create_ph2dt_inp_loose,
    create_hypodd_inp_catalog_only,
    create_hypodd_inp_cc_only,
    create_hypodd_inp_both
)

# Conservative defaults (strict linking)
create_ph2dt_inp_default('ph2dt.inp', 'station.dat', 'detections.pha')

# Loose parameters (for sparse data)
create_ph2dt_inp_loose('ph2dt.inp', 'station.dat', 'detections.pha')

# Catalog data only
create_hypodd_inp_catalog_only('hypoDD.inp', data_files, output_dir='.')

# Cross-correlation only
create_hypodd_inp_cc_only('hypoDD.inp', data_files, output_dir='.')

# Both catalog and CC
create_hypodd_inp_both('hypoDD.inp', data_files, output_dir='.')
```

## Usage Examples

### Example 1: Basic Workflow

```python
from create_hypodd_inputs import create_ph2dt_inp, create_hypodd_inp_catalog_only

# Step 1: Create ph2dt.inp
create_ph2dt_inp(
    output_file='data/hypoDD_inputs/ph2dt.inp',
    station_file='station.dat',
    phase_file='detections.pha',
    maxdist=500,
    maxsep=15,
    minlnk=8
)

# Step 2: Run ph2dt (in terminal)
# $ cd data/hypoDD_inputs
# $ ../../HypoDD-2.1b/src/ph2dt/ph2dt ph2dt.inp

# Step 3: Create hypoDD.inp
create_hypodd_inp_catalog_only(
    output_file='data/hypoDD_inputs/hypoDD.inp',
    data_files={
        'dt_ct': 'dt.ct',
        'event': 'event.dat',
        'station': 'station.dat'
    }
)

# Step 4: Run hypoDD (in terminal)
# $ ../../HypoDD-2.1b/src/hypoDD/hypoDD hypoDD.inp
```

### Example 2: Adjust Parameters Programmatically

```python
from create_hypodd_inputs import create_ph2dt_inp

# Try different MAXSEP values to see effect
for maxsep in [5, 10, 15, 20]:
    create_ph2dt_inp(
        output_file=f'ph2dt_sep{maxsep}.inp',
        station_file='station.dat',
        phase_file='detections.pha',
        maxsep=maxsep,
        minlnk=8
    )
```

### Example 3: Multi-Layer Velocity Model

```python
from create_hypodd_inputs import create_hypodd_inp

create_hypodd_inp(
    output_file='hypoDD.inp',
    data_files={'dt_ct': 'dt.ct', 'event': 'event.dat', 'station': 'station.dat'},
    mod_v=[5.5, 6.3, 8.0],      # P-wave velocities for 3 layers
    mod_ratio=[1.73, 1.73, 1.78],  # Vp/Vs ratios
    mod_top=[0.0, 15.0, 35.0]      # Top depths of layers (km)
)
```

## Advantages Over Manual Editing

✅ **Type safety**: Function parameters are validated  
✅ **Reproducibility**: Script documents exact parameters used  
✅ **Automation**: Easy to test multiple configurations  
✅ **Version control**: Python scripts in git, not .inp files  
✅ **No typos**: F-string formatting handles spacing correctly  
✅ **Documentation**: Docstrings explain each parameter  

## Parameter Tuning Guide

### ph2dt Parameters

| Parameter | Effect when INCREASED | Typical Range |
|-----------|----------------------|---------------|
| `maxdist` | More stations included | 200-500 km |
| `maxsep` | More distant events paired | 5-20 km |
| `minlnk` | Fewer events selected (stricter) | 4-10 |
| `minobs` | Fewer pairs saved (stricter) | 4-10 |

**Rule of thumb:**
- **Sparse data**: Use loose parameters (maxsep=20, minlnk=4)
- **Dense data**: Use strict parameters (maxsep=10, minlnk=8)

### hypoDD Parameters

| Parameter | Purpose | Typical Values |
|-----------|---------|----------------|
| `niter` | Iterations | 5-10 |
| `damp` | Regularization | 50-200 |
| `wtccp` | P-wave weight (CC) | 0.8-1.0 |
| `wtccs` | S-wave weight (CC) | 0.4-0.6 |

**Rule of thumb:**
- **High damp** (100-200) = more stable, less movement
- **Low damp** (50-80) = more movement, may be unstable

## File Organization Recommendation

```
project/
├── scripts/
│   ├── create_hypodd_inputs.py  # The module
│   ├── run_workflow.py          # Your workflow script
│   └── example_create_inputs.py # Examples
├── data/
│   └── hypoDD_inputs/
│       ├── station.dat
│       ├── detections.pha
│       ├── ph2dt.inp       # Generated
│       ├── dt.ct           # Generated by ph2dt
│       ├── event.dat       # Generated by ph2dt
│       └── hypoDD.inp      # Generated
└── HypoDD-2.1b/
    └── src/
```

## Quick Reference

```python
# Import
from create_hypodd_inputs import create_ph2dt_inp, create_hypodd_inp_catalog_only

# Create ph2dt.inp
create_ph2dt_inp('ph2dt.inp', 'station.dat', 'phase.pha', maxsep=15, minlnk=8)

# Create hypoDD.inp
create_hypodd_inp_catalog_only(
    'hypoDD.inp',
    {'dt_ct': 'dt.ct', 'event': 'event.dat', 'station': 'station.dat'}
)
```

That's it! No more manual text editing. 🎉
