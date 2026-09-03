"""Config-driven CLI.

Replaces the module-level constants in the old `run_hypodd.py` — including the
`# ******* POINTING TO NEW RUN DIR *****` that had to be hand-edited per project. A run is
described entirely by a YAML file, so two projects are two configs against one code path.

    hypodd-run --config path/to/run.yaml validate
    hypodd-run --config path/to/run.yaml prepare
    hypodd-run --config path/to/run.yaml ph2dt
    hypodd-run --config path/to/run.yaml hypodd
    hypodd-run --config path/to/run.yaml convert
    hypodd-run --config path/to/run.yaml all

`hypodd`/`convert` do every entry of the config's `runs:` list, in order. To run just one,
comment the others out — the config is the only place runs are selected. NAME is invented by
whoever wrote the config: it labels one hypoDD invocation, picks which `.inp` to use, and names
the output CSV. It does NOT select IDAT; that lives in the `.inp` itself (1 = cross correlation,
2 = catalog, 3 = both). A config with no `runs:` gets one default entry named `cat`, which is
only where that name in older examples came from.

    runs:
      - {name: cc,   inp: hypoDD_cc.inp}      # -> convert writes hypoDD_cc.csv
      - {name: ctcc, inp: hypoDD_ctcc.inp}    # -> convert writes hypoDD_ctcc.csv

The config may live anywhere — with the producing project is the norm, since it names that
project's tables. `examples/quickstart/example.yaml` is a complete runnable one.
"""
from __future__ import annotations

import os
import sys
import glob
import shutil
import argparse

import yaml

from . import tables, writers, runner


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    for key in ('run_dir', 'hypodd_root', 'inputs'):
        if key not in cfg:
            raise SystemExit(f'config: missing required key `{key}`')
    base = os.path.dirname(os.path.abspath(path))
    for k, v in list(cfg.items()):
        if isinstance(v, str) and k.endswith(('_dir', '_root')):
            cfg[k] = v if os.path.isabs(v) else os.path.normpath(os.path.join(base, v))
    for k, v in list(cfg['inputs'].items()):
        if isinstance(v, str) and not os.path.isabs(v):
            cfg['inputs'][k] = os.path.normpath(os.path.join(base, v))
    cfg.setdefault('outputs', {})
    cfg['outputs'].setdefault('pha', 'phase.pha')
    cfg['outputs'].setdefault('cc', 'dt_input.cc')
    cfg.setdefault('runs', [{'name': 'cat', 'inp': 'hypoDD.inp'}])
    return cfg


def _load_tables(cfg, need_pairs):
    inp = cfg['inputs']
    events = tables.load_events(inp['events'])
    arrivals = tables.load_arrivals(inp['arrivals'], events)
    pairs = None
    if need_pairs and inp.get('pairs'):
        pairs = tables.load_pairs(inp['pairs'], events)
    return events, arrivals, pairs


def cmd_validate(cfg, _args):
    events, arrivals, pairs = _load_tables(cfg, True)
    stations = tables.load_stations(cfg['inputs']['stations'])
    print(tables.summarise(events, arrivals, pairs, stations))
    print('\ncontract OK')


def _place_inp_files(cfg):
    """Copy the run's .inp templates into run_dir, then check they agree with `outputs`.

    The .inp files are hand-tuned science settings (IDAT, the weighting schedule, MAXNGH)
    and belong under version control in the producing project, not in a scratch run dir that
    gets wiped. Copying them here means a fresh run_dir is runnable.

    The cross-check exists because a config and an .inp that name different files is the
    failure that reads as "hypoDD succeeded but wrote nothing findable" — the binaries take
    the .inp's word and never see the config.
    """
    src_dir = cfg.get('inp_dir')
    if not src_dir:
        return
    if not os.path.isdir(src_dir):
        raise SystemExit(f'inp_dir does not exist: {src_dir}')
    found = sorted(glob.glob(os.path.join(src_dir, '*.inp')))
    if not found:
        raise SystemExit(f'inp_dir has no .inp files: {src_dir}')
    for f in found:
        shutil.copy2(f, os.path.join(cfg['run_dir'], os.path.basename(f)))
    print(f'inp files            {len(found)} copied from {src_dir}')

    declared = {}
    ph2dt = os.path.join(cfg['run_dir'], cfg.get('ph2dt_inp', 'ph2dt.inp'))
    if os.path.exists(ph2dt):
        declared['pha'] = (runner.read_ph2dt_inputs(ph2dt).get('pha'), os.path.basename(ph2dt))
    # Only when a pairs table is configured. hypoDD.inp names a dt.cc positionally even for an
    # IDAT=2 run that never opens it, so checking it on a catalog-only run would demand the
    # config name a file that is correctly never written.
    if cfg['inputs'].get('pairs'):
        for r in cfg['runs']:
            p = os.path.join(cfg['run_dir'], r['inp'])
            if os.path.exists(p):
                declared.setdefault('cc', (runner.read_inp_outputs(p).get('cc'), r['inp']))
    for slot, (name, where) in declared.items():
        want = cfg['outputs'][slot]
        if name and name != want:
            raise SystemExit(
                f'{where} expects {slot} file {name!r} but the config writes {want!r}. '
                f'Fix one of them — hypoDD reads the .inp and will never see the config.')


def cmd_prepare(cfg, _args):
    run_dir = cfg['run_dir']
    os.makedirs(run_dir, exist_ok=True)
    # Placed and checked FIRST: a name mismatch should cost a second, not the half-minute it
    # takes to write a 200 MB dt.cc that the run would then ignore.
    _place_inp_files(cfg)
    events, arrivals, pairs = _load_tables(cfg, True)
    stations = tables.load_stations(cfg['inputs']['stations'])

    ids = writers.assign_ids(events, os.path.join(run_dir, 'event_id_mapping.csv'))
    n = writers.write_station_dat(stations, os.path.join(run_dir, 'station.dat'))
    print(f'station.dat          {n} stations')

    pha = os.path.join(run_dir, cfg['outputs']['pha'])
    n_ev, n_ph = writers.write_pha(events, arrivals, ids, pha)
    print(f'{os.path.basename(pha):20s} {n_ev:,} events / {n_ph:,} phases')

    if pairs is not None:
        cc = os.path.join(run_dir, cfg['outputs']['cc'])
        n_pair, n_obs = writers.write_cc(pairs, ids, cc)
        print(f'{os.path.basename(cc):20s} {n_pair:,} pairs / {n_obs:,} observations')
    else:
        print('(no pairs table configured — catalog-only run)')


def cmd_ph2dt(cfg, _args):
    runner.run_ph2dt(cfg['hypodd_root'], cfg['run_dir'],
                     cfg.get('ph2dt_inp', 'ph2dt.inp'),
                     os.path.join(cfg['run_dir'], 'ph2dt.stdout'))
    print('ph2dt OK -> dt.ct')


def _reloc_name(cfg, r):
    """The .inp declares its own output name; the config never second-guesses it."""
    return runner.read_inp_outputs(os.path.join(cfg['run_dir'], r['inp'])).get(
        'reloc', 'hypoDD.reloc')


def cmd_hypodd(cfg, args):
    for r in cfg['runs']:
        reloc = _reloc_name(cfg, r)
        print(f'--- run {r["name"]}: {r["inp"]} -> {reloc}')
        runner.run_hypodd(cfg['hypodd_root'], cfg['run_dir'], r['inp'], reloc,
                          archive=f'archive_{r["name"]}',
                          log_path=os.path.join(cfg['run_dir'], f'hypoDD_{r["name"]}.stdout'))
        print(f'    OK')


def cmd_convert(cfg, args):
    events = tables.load_events(cfg['inputs']['events'])
    ids = writers.assign_ids(events)
    out_dir = cfg.get('results_dir', cfg['run_dir'])
    os.makedirs(out_dir, exist_ok=True)
    for r in cfg['runs']:
        reloc = os.path.join(cfg['run_dir'], _reloc_name(cfg, r))
        if not os.path.exists(reloc):
            print(f'    {r["name"]}: {reloc} not found, skipping')
            continue
        df, skipped = writers.read_reloc(reloc, ids)
        out = os.path.join(out_dir, f'hypoDD_{r["name"]}.csv')
        df.to_csv(out, index=False)
        print(f'    {r["name"]}: {len(df):,} events -> {out}'
              + (f'  ({skipped} unconstrained, dropped)' if skipped else ''))


def cmd_all(cfg, args):
    cmd_validate(cfg, args); print()
    cmd_prepare(cfg, args); print()
    cmd_ph2dt(cfg, args); print()
    cmd_hypodd(cfg, args); print()
    cmd_convert(cfg, args)


COMMANDS = {'validate': cmd_validate, 'prepare': cmd_prepare, 'ph2dt': cmd_ph2dt,
            'hypodd': cmd_hypodd, 'convert': cmd_convert, 'all': cmd_all}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='hypodd-run', description=__doc__.split('\n')[0])
    ap.add_argument('--config', required=True)
    ap.add_argument('command', choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    COMMANDS[args.command](cfg, args)     # exceptions propagate: exit code must be honest
    return 0


if __name__ == '__main__':
    sys.exit(main())
