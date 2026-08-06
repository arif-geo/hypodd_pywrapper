# legacy/

The original FMF daughter-parent relocation path. **Superseded, kept as a working reference
until Stage H of the detection pipeline is verified end to end.**

| file | what it did |
|---|---|
| `run_hypodd.py` | one hardcoded script: master picks CSV -> `.pha`/`.cc` -> ph2dt -> hypoDD -> CSV |
| `csv_hypodd.py` | the converters it calls |
| `run_hypodd_relocation.slurm` | the SLURM job that ran it |

## Why it was replaced

It was written for exactly one job — relocating FMF detections against their template parents —
and the assumption is baked in everywhere. `RUN_DIR` carried a
`# ******* POINTING TO NEW RUN DIR *****` comment because it had to be hand-edited per run.
Input paths point straight at `Match-Filter-Event-Detection/.../results/stage_f_master_catalog/`.
`csv_to_cc` filters on `event_id != template_id`, which silently writes self-pairs for any
catalog whose events *are* their own templates.

The replacement splits that single script along the line where the domain knowledge actually
sits:

- **producers** know about picks, templates and detections, and emit four plain CSVs —
  `H_make_hypodd_tables.py` in the detection pipeline, `make_tables.py` in `mtj_template_reloc`
- **`hypodd_run`** knows about hypoDD's Fortran formats and nothing else

## Running it

Both files still work, but the imports assume `Arif-projects/` is on `sys.path` (namespace
package). `compare_utils` was deleted — `run_hypodd.py` imported it but never called it, so the
import was removed rather than the file restored. It is in git history at `00398fa` if wanted.

## When to delete this directory

Once Stage F -> G -> H has run and the daughter relocation it produces has been compared against
a `run_hypodd.py` result. Until that comparison exists, this is the only thing that proves the
new path computes the same answer.
