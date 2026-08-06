# hypodd_run

A domain-agnostic bridge between tabular earthquake data and hypoDD.

It knows nothing about templates, daughter detections, match-filter output, or any particular
catalog's column names. It takes flat tables, writes hypoDD's fixed-format text files, runs
`ph2dt`/`hypoDD`, and reads the results back. Everything domain-specific lives in whichever
project *produces* the tables.

```
producer project                     this package
────────────────                     ────────────
reviewed picks    ─┐
FMF detections    ─┼─> four CSVs ─>  validate ─> .pha/.cc/station.dat ─> ph2dt ─> hypoDD ─> CSV
some other catalog─┘
```

Two known producers, sharing no code with each other or with this package:

| producer | project |
|---|---|
| `make_tables.py` | `mtj_template_reloc` — relocating a reviewed-pick catalog |
| `H_make_hypodd_tables.py` | `Match-Filter-Event-Detection` — FMF daughters + parents |

## Setup

Every command below runs from the **repo root** — the directory holding `pyproject.toml`.

```bash
cd /N/u/mdaislam/Quartz/Arif-projects/hypodd_pywrapper

( cd HypoDD-2.1b/src && make )       # builds ph2dt + hypoDD. Parentheses = subshell, so
                                     # the cd is undone and you stay at the repo root.
python -m pip install -e . --no-deps # `.` is the repo root — that is why the cd matters
pytest tests/ -q                     # ~14 s, includes a real hypoDD inversion
```

`python -m pip` rather than `pip`: a conda env that has been moved or copied keeps a stale
shebang in `bin/pip` and fails with `bad interpreter`. `--no-deps` because pandas/numpy/pyyaml
are already present, and letting pip resolve them can upgrade numpy out from under obspy/numba.

**Once per env** — the `hypodd-run` command is written into that env's `bin/`, so a new env has
no `hypodd-run` until you install into it. `-e` points the env at this source tree rather than
copying it, so every env stays in sync and editing the code takes effect immediately.

If you would rather not install at all, this needs nothing and works from any directory:

```bash
( cd /N/u/.../hypodd_pywrapper/HypoDD-2.1b/src && make )

PYTHONPATH=/N/u/mdaislam/Quartz/Arif-projects/hypodd_pywrapper/src \
  python -m hypodd_run.cli --config <run>.yaml validate
```

You get the code but not the `hypodd-run` command; use `python -m hypodd_run.cli` in its place.

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
weights it. Putting the coefficient in `dt_sec` produces a run that converges to nonsense.

**Known gap:** hypoDD's `dt.cc` supports a per-pair origin-time correction (OTC) that this
contract has no column for. Every current producer measures differential times against observed
picks, where OTC is zero by construction. `readers.read_cc` returns any non-zero OTC it finds as
a separate value rather than dropping it silently.

## Usage

```bash
hypodd-run --config <run>.yaml validate     # contract check — cheap, run it first
hypodd-run --config <run>.yaml prepare      # -> .pha, .cc, station.dat, mapping, .inp
hypodd-run --config <run>.yaml ph2dt        # -> dt.ct
hypodd-run --config <run>.yaml hypodd  --run cat
hypodd-run --config <run>.yaml convert --run cat
hypodd-run --config <run>.yaml all          # all of the above
```

Two projects are two YAML files against one code path. Run configs live with the **producer**,
not here — see `mtj_template_reloc/configs/hypodd_run.yaml` for a documented example. A config
names `run_dir`, `hypodd_root`, the four input tables, an `inp_dir` of hand-tuned `.inp`
templates, and one or more named `runs`.

## Layout

```
src/hypodd_run/     the package
  tables.py         the contract and its validation
  writers.py        tables -> hypoDD fixed-format text, and .reloc -> table
  readers.py        hypoDD fixed-format text -> tables (the inverse; for existing datasets)
  runner.py         running ph2dt/hypoDD, honestly
  cli.py            config-driven commands
tests/              pytest, including hypoDD's own Calaveras example
legacy/             the superseded FMF-specific path — see legacy/README.md
HypoDD-2.1b/        upstream hypoDD source, binaries and examples
```

`runs/` is gitignored working space. Nothing in the repo requires it to exist; `run_dir` in a run
config points wherever you like.

---

# Reference

## `.pha` vs `.ct` vs `.cc`

- **`.pha`** — absolute arrival times of P and S at each station, per event. Input to `ph2dt`.
- **`.ct`** — catalog differential times. `ph2dt` reads the `.pha` and subtracts arrival times
  for event pairs at common stations: `dt = TT₁ − TT₂`. Its precision is bounded by **pick
  accuracy**.
- **`.cc`** — cross-correlation differential times, measured directly between waveforms and fed
  to hypoDD without passing through `ph2dt`. Its precision is bounded by **waveform coherence**,
  typically one to two samples.

That precision gap, not the correlation values themselves, is why adding `dt.cc` sharpens
locations.

`IDAT` in `hypoDD.inp` selects which are used: **1** = CC only, **2** = catalog only, **3** =
both.

## Why catalog-only fails for match-filter detections

Template-matching detections inherit their announced travel times from the template:

```
template event:  origin 00:00:00, arrival at station A 00:00:08  ->  TT = 8.00 s
detected event:  origin 00:00:00, arrival at station A 00:00:08  ->  TT = 8.00 s
```

`ph2dt` then computes `dt = 8.00 − 8.00 = 0.00` and there is nothing to invert. Either put the
measured lag times directly into `dt.cc` (IDAT=1), or apply the lag correction to the travel
times before writing the `.pha`. This does **not** apply to an ordinary catalog whose picks were
measured independently per event — there, IDAT=2 is meaningful, and `mtj_template_reloc` uses it
as the baseline against which `dt.cc` is judged.

## Parameters that matter most

### `ph2dt.inp` — pair formation

```
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
   0      500     15     15     8      8     50
```

| Parameter | Effect | Notes |
|---|---|---|
| **MINLNK** | min. common stations for two events to be neighbours | Highest-impact knob. 8 is standard; drop to 4–6 when events have few stations |
| **MINOBS** | min. observations for a pair to be kept | Same magnitude of effect as MINLNK |
| **MAXSEP** | max. event separation (km) | 15–30 typical |
| **MAXDIST** | max. station distance (km) | 100–500 |
| **MAXNGH** | max. neighbours per event | Interacts with event ordering — see below |

Lower MINLNK/MINOBS admit more events at lower link quality. With a star topology (every event
linked only to a template and not to each other) high values silently discard the weakly
connected majority. Check how many events have few stations before choosing: in the MTJ run, 494
events had exactly 3 stations, i.e. at most 6 links, so MINLNK=8 would have dropped all of them.

### `hypoDD.inp` — clustering and weighting

```
*--- event clustering:
* OBSCC  OBSCT    MINDIST  MAXDIST  MAXGAP
    8     0        -999     -999    -999

* NITER WTCCP WTCCS WRCC WDCC WTCTP WTCTS WRCT WDCT DAMP
  5     1.0   0.5   -9   -9    0.0   0.0    -9   -9   80
```

| Parameter | Effect | Notes |
|---|---|---|
| **OBSCC / OBSCT** | min. CC / catalog observations per pair | Set OBSCT=0 for a CC-only run |
| **WTCCP / WTCCS** | weight on CC P / S data | Higher trusts CC more |
| **WTCTP / WTCTS** | weight on catalog P / S | 0.0 for CC-only |
| **WRCC / WRCT** | residual cutoff (s) | −9 = no limit; tighten in later iteration sets |
| **WDCC / WDCT** | max. pair distance (km) | −9 = no limit |
| **DAMP** | LSQR damping | 70–100; higher is more stable and slower |

The weighting block is one line per iteration set, applied in order — the usual pattern is loose
early sets that let events move, then tight residual and distance cutoffs once they are roughly
in place.

## Relocated CSV columns

`convert` writes `hypoDD_<run>.csv` with the `.reloc` columns plus the producer's original ID:

| column | meaning |
|---|---|
| `event_id` | the producer's own identifier, joined back via `event_id_mapping.csv` |
| `hypodd_id` | the synthetic integer hypoDD required |
| `latitude`, `longitude`, `depth` | relocated position (degrees, km) |
| `x_m`, `y_m`, `z_m` | Cartesian offset from the cluster centroid (m) |
| `ex_m`, `ey_m`, `ez_m` | formal errors (m) |
| `n_cc_p`, `n_cc_s`, `n_cat_p`, `n_cat_s` | observation counts behind each event |
| `rms_cc`, `rms_cat` | RMS residuals |
| `cluster_id` | hypoDD cluster membership |

Events hypoDD could not constrain appear in `.reloc` with `*` or `NaN`; `read_reloc` drops and
counts them rather than coercing them to a number.

---

# Design rules

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
nothing". `prepare` copies the `.inp` files in and refuses to continue if they disagree with
`outputs`.

**No module-level constants.** The old `RUN_DIR` carried
`# ******* POINTING TO NEW RUN DIR *****` and had to be hand-edited per project.

# Tests

`tests/test_contract.py` covers the contract — each test corresponds to a specific failure the
predecessor produced silently.

`tests/test_calaveras.py` runs against **hypoDD's own bundled example2** (308 Calaveras events,
13,769 arrivals, 1,961 stations). A domain-agnostic tool should be tested on data it knows
nothing about, and this is data hypoDD itself ships and validates against. It covers a `.pha`
round-trip and the full chain, comparing the result to the distributed `hypoDD.reloc`. The
end-to-end test skips automatically if the binaries are not built.

# Verification

Against the MTJ reviewed-pick relocation (4,508 events, 61,408 arrivals, 6.73M CC observations),
this package vs. the shell + `csv_hypodd.py` path it replaced:

- Input tables reproduce the legacy build **exactly** — all four tables, all values.
- `dt.cc` and the event-ID mapping are **byte-identical**; `.pha` and `station.dat` are identical
  up to line order.
- Relocated positions agree to a **median 8.4 m** in 3-D, with median nearest-neighbour distance
  matching to 0.7 m (0.1385 vs 0.1392 km).

Against hypoDD's own published Calaveras result, a catalog-only run here lands within a **median
36 m** of the distributed `hypoDD.reloc` — which itself used catalog + CC, so exact agreement was
never the expectation.

**Runs are not bit-reproducible across paths, and that is expected.** `assign_ids` sorts by
`(origin_time, event_id)`; the legacy mapping did not, so no synthetic IDs coincide. Different
IDs change pair ordering out of ph2dt, LSQR walks a different path, and a few events land on
opposite sides of a clustering threshold. Judge agreement on location, never on file hashes.
