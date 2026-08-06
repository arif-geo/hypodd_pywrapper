# hypodd_run

A domain-agnostic bridge between tabular earthquake data and hypoDD.

It knows nothing about templates, daughter detections, match-filter output, or any particular
catalog's column names. It takes three flat tables, writes hypoDD's fixed-format text files,
runs `ph2dt`/`hypoDD`, and reads the results back. Everything domain-specific lives in whichever
project *produces* the tables.

## The contract

```
events.csv    event_id, origin_time, latitude, longitude, depth[, magnitude, eh, ez, rms]
arrivals.csv  event_id, station, phase, travel_time[, weight]
pairs.csv     ev1, ev2, station, phase, dt_sec[, weight]     (optional -> dt.cc)
stations.csv  station, latitude, longitude[, elevation]
```

`arrivals` is **long form** — one row per event/station/phase. The old wide shape
(`travel_time_p` + `travel_time_s` on one row) forced every station into a P/S pair and made an
S-only station awkward; long form handles P-only, S-only and any future phase identically.

In `pairs`, **`dt_sec` is a time, and `weight` is where a correlation coefficient goes.** A
cross-correlation `dt.cc` is a differential *time* measured by correlation; the coefficient only
weights it.

## Usage

```bash
pip install -e .        # or: export PYTHONPATH=<repo>/src

hypodd-run --config runs_config/mtj_reviewed.yaml validate
hypodd-run --config runs_config/mtj_reviewed.yaml prepare
hypodd-run --config runs_config/mtj_reviewed.yaml ph2dt
hypodd-run --config runs_config/mtj_reviewed.yaml hypodd  --run cat
hypodd-run --config runs_config/mtj_reviewed.yaml convert --run cat
hypodd-run --config runs_config/mtj_reviewed.yaml all
```

Two projects are two YAML files against one code path. See `runs_config/mtj_reviewed.yaml`.

## What changed, and why

**Validation is strict.** The predecessor substituted hardcoded coordinates
(`lat, lon, depth = 40.5, -124.0, 10.0`) for events it could not resolve, printed a warning, and
carried on — relocating an event from a fabricated starting point while reporting success.
Mendocino coordinates in a general-purpose tool is the clearest possible sign that domain
knowledge had leaked in. A missing location is now an error.

**Self-pairs are rejected.** `csv_to_cc` filtered on `event_id != template_id`; for catalog
events those are equal by construction, so it matched nothing, fell through to
`detections = df.copy()`, and wrote `# 1 1` — an event differenced against itself.

**Failures propagate.** The predecessor printed the error and returned, wrapped in a blanket
`except Exception: print(...)`, so a non-zero exit produced a friendly message and exit code 0.
`srun ... ph2dt && srun ... hypodd` would then run hypoDD on a `dt.ct` that was never written.

**The `.inp` is the single source of truth for output filenames.** A run config that also names
them is just a way for the two to disagree, which surfaces as "hypoDD succeeded but wrote
nothing". `read_inp_outputs()` parses them from the `.inp` instead.

**No module-level constants.** The old `RUN_DIR` carried
`# ******* POINTING TO NEW RUN DIR *****` and had to be hand-edited per project.

## Verification

Against the MTJ reviewed-pick relocation (4,508 events, 61,408 arrivals, 6.73M pairs):

- `.pha` content is **identical** to the legacy `csv_to_pha` output — 61,408 phase observations,
  exact match on (event, station, phase, travel_time, weight).
- `.cc` line format is byte-identical to the legacy `daughter_csv_to_cc` f-string.
- End-to-end relocation agrees with the legacy path to **median 4.4 m horizontally / 5.0 m in
  depth**, against formal 2σ errors of ~10 m. Not byte-identical, and it should not be: event
  ordering differs, which changes which 15 neighbours `MAXNGH` selects.

`tests/test_contract.py` covers the contract. Note `legacy_master_to_tables` lives in the test
file, not the package — it exists only to replay old inputs as a regression check, and should be
deleted once Stage F/G emits the three tables directly.
