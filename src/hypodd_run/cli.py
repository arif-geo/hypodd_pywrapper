"""Config-driven CLI.

Replaces the module-level constants in the old `run_hypodd.py` — including the
`# ******* POINTING TO NEW RUN DIR *****` that had to be hand-edited per project. A run is
described entirely by a YAML file, so two projects are two configs against one code path.

    hypodd-run --config runs_config/mtj_reviewed.yaml validate
    hypodd-run --config runs_config/mtj_reviewed.yaml prepare
    hypodd-run --config runs_config/mtj_reviewed.yaml ph2dt
    hypodd-run --config runs_config/mtj_reviewed.yaml hypodd --run cat
    hypodd-run --config runs_config/mtj_reviewed.yaml convert --run cat
    hypodd-run --config runs_config/mtj_reviewed.yaml all
"""
from __future__ import annotations

import os
import sys
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
    tables.load_stations(cfg['inputs']['stations'])
    print(tables.summarise(events, arrivals, pairs))
    print('\ncontract OK')


def cmd_prepare(cfg, _args):
    run_dir = cfg['run_dir']
    os.makedirs(run_dir, exist_ok=True)
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


def _runs(cfg, name):
    rs = cfg['runs']
    if name:
        rs = [r for r in rs if r['name'] == name]
        if not rs:
            raise SystemExit(f'no run named {name!r} in config '
                             f'(have: {[r["name"] for r in cfg["runs"]]})')
    return rs


def _reloc_name(cfg, r):
    """The .inp declares its own output name; the config never second-guesses it."""
    return runner.read_inp_outputs(os.path.join(cfg['run_dir'], r['inp'])).get(
        'reloc', 'hypoDD.reloc')


def cmd_hypodd(cfg, args):
    for r in _runs(cfg, args.run):
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
    for r in _runs(cfg, args.run):
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
    ap.add_argument('--run', default=None, help='limit to one named run from `runs:`')
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    COMMANDS[args.command](cfg, args)     # exceptions propagate: exit code must be honest
    return 0


if __name__ == '__main__':
    sys.exit(main())
