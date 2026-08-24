# quickstart

A complete, runnable `hypodd_run` project. Everything the wrapper needs is here — four input
tables, two `.inp` files, one config — so you can see the whole shape before pointing it at your
own data.

```bash
hypodd-run --config examples/quickstart/example.yaml all
```

About 13 seconds. It writes into `examples/quickstart/run/` (gitignored).

## What it is

A 40-event subset of hypoDD's own Calaveras dataset, the one distributed in
`HypoDD-2.1b/examples/example2`. Deliberately not this project's seismology: a domain-agnostic
tool should demonstrate itself on data it knows nothing about.

The subset is chosen by cross-correlation connectivity rather than at random. hypoDD relocates
events relative to their neighbours, so an arbitrary 40 events would be poorly linked and mostly
discarded by ph2dt — an example that runs and demonstrates nothing.

`make_example.py` regenerates `tables/` from the source dataset, so the CSVs have visible
provenance instead of being four mystery files:

```bash
python examples/quickstart/make_example.py --events 40
```

## What to expect

```
events   :        40
arrivals :     2,748  (2,705 P / 43 S) across 184 stations
pairs    :    19,806  over 472 event pairs
contract OK
...
    ccct: 40 events -> .../run/results/hypoDD_ccct.csv
```

All 40 events relocate. Against the `hypoDD.reloc` that hypoDD ships, the result agrees to a
**median 44 m horizontally / 80 m in depth**. It is not identical, and should not be: this is a
40-event subset of their 308-event problem, so the clustering and neighbour sets differ. If you
see agreement within ~100 m, everything is working.

## Files

| | |
|---|---|
| `example.yaml` | the run config. Paths are relative to itself, so it works from any directory |
| `tables/` | the four contract CSVs — this is the interface a producer targets |
| `inp/ph2dt.inp` | pair formation. `MINLNK`/`MINOBS` relaxed to 4 for a 40-event set |
| `inp/hypoDD.inp` | `IDAT=3` (catalog + CC), Calaveras velocity model, `OBSCC`/`OBSCT` 4 |
| `make_example.py` | regenerates `tables/` from `HypoDD-2.1b/examples/example2` |

## Using it as a starting point

Copy `example.yaml`, then repoint `inputs` at wherever your producer writes its tables and
`inp_dir` at your own `.inp` files. Nothing else has to change. Absolute paths are fine and are
what you want once the tables live outside this repo — see **Using it from another project** in
the top-level README.
