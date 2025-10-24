# HypoDD Workflow - Organized Structure

## Philosophy

**Manual editing of `.inp` files is easier and more flexible than programmatic generation.**

This setup allows you to:
- Edit `.inp` files directly as text (easier to understand)
- Keep each run organized in its own directory
- Version control your configuration files
- Easily compare different parameter choices

## Directory Structure

```
hypodd_pywrapper/
├── config/
│   └── hypoDD_templates/           # Template .inp files
│       ├── ph2dt.inp.template      # ph2dt configuration template
│       └── hypoDD.inp.template     # hypoDD configuration template
│
├── data/
│   ├── input_csvs/                 # Raw CSV input data
│   │   ├── nc73818801_fmf_detections_phase_picks.csv
│   │   ├── stations_2000_onshore_permanent_50km_cleaned_2022.csv
│   │   └── yoon_shelly_ferndale-2022-12-01.csv
│   │
│   └── runs/                       # Each run in its own directory
│       ├── run_detections_2020/    # Example run
│       │   ├── station.dat         # Input: station locations
│       │   ├── detections.pha      # Input: phase picks
│       │   ├── detections.cc       # Input: cross-correlation data
│       │   ├── event_id_mapping.csv # ID mapping reference
│       │   ├── ph2dt.inp           # Config: edit manually!
│       │   ├── hypoDD.inp          # Config: edit manually!
│       │   ├── dt.ct               # Output: differential times
│       │   ├── event.dat           # Output: event list
│       │   ├── hypoDD.reloc        # Output: relocated events
│       │   └── hypoDD.loc          # Output: original locations
│       │
│       └── run_example2/           # Another run with different parameters
│
├── scripts/
│   ├── csv_to_hypodd.py           # Format conversion functions
│   └── run_hypodd.py              # Workflow automation
│
└── HypoDD-2.1b/                   # HypoDD source code
```

## Workflow

### Step 1: Setup a New Run

This converts your CSV data and creates a run directory with all needed files:

```bash
cd scripts
python3 run_hypodd.py --setup run_detections_2020
```

**What it does:**
1. Creates `data/runs/run_detections_2020/`
2. Converts CSV → HypoDD formats (station.dat, detections.pha, detections.cc)
3. Copies template .inp files to the run directory
4. Saves event ID mapping for reference

**Output:**
```
data/runs/run_detections_2020/
├── station.dat              ✓ Ready
├── detections.pha           ✓ Ready
├── detections.cc            ✓ Ready
├── event_id_mapping.csv     ✓ Ready
├── ph2dt.inp                📝 Edit this!
└── hypoDD.inp               📝 Edit this!
```

### Step 2: Edit Configuration Files

**Now manually edit the .inp files** in your run directory:

```bash
cd ../data/runs/run_detections_2020
nano ph2dt.inp      # Adjust MAXSEP, MINLNK, etc.
nano hypoDD.inp     # Adjust NITER, DAMP, velocity model, etc.
```

**Why manual editing?**
- Easier to understand what each parameter does
- Faster than Python function calls for tweaking
- Comments in the file explain each parameter
- Can copy/paste from other successful runs

### Step 3: Run HypoDD Workflow

Once you're happy with the `.inp` files:

```bash
cd ../../scripts
python3 run_hypodd.py --run run_detections_2020
```

**What it does:**
1. Runs `ph2dt` to create differential times (dt.ct)
2. Runs `hypoDD` to relocate events
3. Reports which output files were created

**Output files created in run directory:**
- `dt.ct` - Differential travel times
- `event.dat` - Event list for relocation
- `hypoDD.reloc` - Relocated event positions ⭐
- `hypoDD.loc` - Original event positions
- `hypoDD.res` - Residuals
- `hypoDD.sta` - Station information

### Step 4: Analyze Results

```bash
cd ../data/runs/run_detections_2020

# View relocated events
head hypoDD.reloc

# Compare before/after
head hypoDD.loc
head hypoDD.reloc

# Check residuals
head hypoDD.res
```

## Common Use Cases

### Try Different Parameters

Create multiple runs with different settings:

```bash
# Setup base run
python3 run_hypodd.py --setup run_maxsep10

# Copy to new run with different params
cp -r ../data/runs/run_maxsep10 ../data/runs/run_maxsep15

# Edit the new run's parameters
cd ../data/runs/run_maxsep15
nano ph2dt.inp  # Change MAXSEP from 10 to 15

# Run both
cd ../../../scripts
python3 run_hypodd.py --run run_maxsep10
python3 run_hypodd.py --run run_maxsep15

# Compare results
diff ../data/runs/run_maxsep10/hypoDD.reloc ../data/runs/run_maxsep15/hypoDD.reloc
```

### Work on Different Datasets

```bash
# Detection events from template nc73818801
python3 run_hypodd.py --setup run_template_nc73818801

# Detection events from different template
python3 run_hypodd.py --setup run_template_nc73890906

# Each run is completely independent!
```

## Key Parameters to Adjust

### In `ph2dt.inp`:

| Parameter | Effect | Typical Range | Adjust When |
|-----------|--------|---------------|-------------|
| MAXDIST | Max station distance | 200-500 km | Sparse stations → increase |
| MAXSEP | Max event separation | 5-20 km | Sparse events → increase |
| MINLNK | Min links per pair | 4-10 | Sparse data → decrease |
| MINOBS | Min observations | 4-10 | Sparse data → decrease |

**Rule of thumb:**
- Sparse/few events → Use loose parameters (maxsep=20, minlnk=4)
- Dense/many events → Use strict parameters (maxsep=10, minlnk=8)

### In `hypoDD.inp`:

| Parameter | Effect | Typical Range | Adjust When |
|-----------|--------|---------------|-------------|
| IDAT | Data type | 0-2 | 0=CC only, 1=CT only, 2=both |
| NITER | Iterations | 5-10 | More = more refined |
| DAMP | Damping | 50-200 | High = stable, Low = more movement |
| Velocity model | Vp, Vp/Vs | Regional | Use local model |

## Tips & Best Practices

### 1. Always Keep the Original Data

The `data/input_csvs/` directory should never be modified. All conversions happen in `data/runs/`.

### 2. Name Runs Descriptively

Good names:
- `run_detections_2020_maxsep15`
- `run_template_nc73818801_strict`
- `run_experiment_damping100`

Bad names:
- `run1`
- `test`
- `final` (there's always another "final")

### 3. Document What You Changed

Add comments to your `.inp` files:

```
* MAXSEP increased to 20 km because events are sparse - John, 2025-10-20
```

### 4. Version Control Your Runs

```bash
git add data/runs/run_detections_2020/*.inp
git add data/runs/run_detections_2020/*.csv
git commit -m "Setup run with maxsep=15, minlnk=8"
```

### 5. Keep Successful Runs

Don't delete runs that worked well! They're your reference for future work.

## Troubleshooting

### "Only 8 out of 23 events selected"

This is normal! ph2dt filters events based on:
- MINLNK: Need enough connections
- MAXSEP: Events too far apart excluded

**Solutions:**
- Decrease MINLNK (e.g., from 8 to 4)
- Increase MAXSEP (e.g., from 10 to 20 km)
- Check if your events are actually clustered

### "No output files created"

Check the terminal output for errors. Common issues:
- Format error in .inp file
- Missing input files (station.dat, etc.)
- hypoDD crashed (needs recompile)

### "hypoDD crashes with library error"

You need to recompile hypoDD:

```bash
cd HypoDD-2.1b/src
make clean
make
```

## Quick Reference

```bash
# Setup new run
python3 run_hypodd.py --setup <run_name>

# Run workflow
python3 run_hypodd.py --run <run_name>

# Setup and run in one command
python3 run_hypodd.py --setup <run_name> --run <run_name>

# Run official example
python3 run_hypodd.py --example example2

# Compile HypoDD
python3 run_hypodd.py --compile
```

## Philosophy: Why This Organization?

✅ **Clear separation** - Input data vs. processing runs
✅ **Self-contained runs** - Each directory has everything
✅ **Easy comparison** - Just diff two run directories
✅ **Version control friendly** - Track .inp files in git
✅ **Reproducible** - Copy entire run directory to repeat
✅ **Manual-editing friendly** - Edit .inp files as text
✅ **No magic** - Everything is visible and transparent

This is how real seismologists work! 🎯
