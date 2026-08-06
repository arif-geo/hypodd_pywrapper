"""Running ph2dt and hypoDD.

Every failure raises. The predecessor printed the error and returned, and wrapped `main` in a
blanket `except Exception: print(...)`, so a non-zero exit produced a friendly message and an
exit code of 0 — which meant `srun ... ph2dt && srun ... hypodd` happily ran hypoDD on a dt.ct
that was never written. Chained shell commands and `set -e` can only be trusted if failures
propagate.
"""
from __future__ import annotations

import os
import glob
import shutil
import subprocess


class HypoDDError(RuntimeError):
    pass


def _binary(hypodd_root, name):
    p = os.path.join(hypodd_root, 'src', name, name)
    if not os.path.exists(p):
        raise HypoDDError(f'{name} binary not found at {p} — build it with `make` in '
                          f'{os.path.join(hypodd_root, "src")}')
    if not os.access(p, os.X_OK):
        raise HypoDDError(f'{name} at {p} is not executable')
    return p


def _run(binary, inp, run_dir, log_path=None):
    """hypoDD and ph2dt resolve their .inp relative to CWD and reject absolute paths,
    so the run directory must be the working directory and `inp` a bare filename."""
    inp = os.path.basename(inp)
    if not os.path.exists(os.path.join(run_dir, inp)):
        raise HypoDDError(f'{inp} not found in {run_dir}')
    proc = subprocess.run([binary, inp], cwd=run_dir, capture_output=True,
                          text=True, errors='replace')
    if log_path:
        with open(log_path, 'w') as f:
            f.write(proc.stdout)
            if proc.stderr:
                f.write('\n--- stderr ---\n' + proc.stderr)
    if proc.returncode != 0:
        tail = '\n'.join((proc.stdout or '').splitlines()[-15:])
        raise HypoDDError(f'{os.path.basename(binary)} exited {proc.returncode}\n'
                          f'--- last output ---\n{tail}\n--- stderr ---\n{proc.stderr}')
    return proc.stdout


def run_ph2dt(hypodd_root, run_dir, inp='ph2dt.inp', log_path=None):
    out = _run(_binary(hypodd_root, 'ph2dt'), inp, run_dir, log_path)
    produced = os.path.join(run_dir, 'dt.ct')
    if not os.path.exists(produced) or os.path.getsize(produced) == 0:
        raise HypoDDError(f'ph2dt reported success but {produced} is missing or empty')
    return out


# hypoDD.inp is positional: line 1 is the log file, then nine filenames in a fixed order.
INP_FILE_SLOTS = ['log', 'cc', 'ct', 'eve', 'sta', 'loc', 'reloc', 'stares', 'res', 'srcpar']


def read_inp_outputs(path):
    """Which files a hypoDD.inp declares.

    The .inp is the single source of truth for output names — duplicating them in a run config
    just creates a way for the two to disagree, which reads as "hypoDD succeeded but wrote
    nothing".
    """
    lines = [ln.strip() for ln in open(path)
             if ln.strip() and not ln.lstrip().startswith('*')]
    return dict(zip(INP_FILE_SLOTS, lines[:len(INP_FILE_SLOTS)]))


def run_hypodd(hypodd_root, run_dir, inp='hypoDD.inp', reloc=None,
               archive=None, log_path=None):
    """Run hypoDD, then move the per-iteration hypoDD.reloc.NNN.NNN files aside.

    hypoDD writes those on every iteration; left in place they accumulate across runs and make
    it impossible to tell which belong to which run.

    `reloc` defaults to whatever the .inp declares — pass it only to override.
    """
    reloc = reloc or read_inp_outputs(os.path.join(run_dir, inp)).get('reloc', 'hypoDD.reloc')
    out = _run(_binary(hypodd_root, 'hypoDD'), inp, run_dir, log_path)
    final = os.path.join(run_dir, reloc)
    if not os.path.exists(final) or os.path.getsize(final) == 0:
        raise HypoDDError(f'hypoDD reported success but {final} is missing or empty — check '
                          f'the log; this usually means every event was discarded by the '
                          f'clustering or weighting settings')
    if archive:
        dest = os.path.join(run_dir, archive)
        os.makedirs(dest, exist_ok=True)
        for f in glob.glob(os.path.join(run_dir, f'{reloc}.*')):
            shutil.move(f, os.path.join(dest, os.path.basename(f)))
    return out
