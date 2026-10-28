"""Frozen paired F-E/F-B put data; no network fits or test selection here."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import pathlib
import signal
import time

import numpy as np

from fb_data_pilot import one, sample


def pack(rows, cell):
    x, y, a, d, group = [], [], [], [], []
    for row in rows:
        c = row['contract']['model']
        e1, e2, e3 = row['contract']['exercise']
        maturity = row['contract']['maturity']
        for r in row['rows']:
            common = [np.log(c['a']), c['sigma'], np.log(c['r0']), np.log(c['rbar'])]
            contract = ([e3, maturity, r['strike']] if cell == 'FE'
                        else [e1, e2, e3, maturity, r['strike']])
            x.append(common+contract)
            y.append(r['european_reference']['price'] if cell == 'FE' else r['reference']['price'])
            a.append(r['gtfk_european'] if cell == 'FE' else r['gtfk_bermudan'])
            d.append(r['coarse_european_pde'] if cell == 'FE' else r['coarse_pde'])
            group.append(row['group'])
    return dict(X=np.asarray(x, dtype=np.float64), y=np.asarray(y, dtype=np.float64),
                A=np.asarray(a, dtype=np.float64), Dbase=np.asarray(d, dtype=np.float64),
                group=np.asarray(group, dtype=np.int32))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    cfg = json.loads(pathlib.Path(args.config).read_text())
    available_cpu = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count()
    if available_cpu < cfg['workers']:
        raise RuntimeError('frozen worker count exceeds available CPU affinity')
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    def alarm(*_):
        raise TimeoutError('frozen data generation exceeded its wall-clock budget')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(cfg['max_seconds'])
    arrays, failures, timing = {}, [], {}
    for split in cfg['splits']:
        name, count, seed, region = split['name'], split['groups'], split['seed'], split['region']
        contracts = sample(count, seed, region)
        rows = []
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=cfg['workers']) as pool, (out/(name+'.jsonl')).open('w') as ledger:
            for row in pool.map(one, enumerate(contracts)):
                rows.append(row)
                ledger.write(json.dumps(row)+'\n')
                ledger.flush()
                if not row['certified']:
                    failures.append(dict(split=name, group=row['group'], error=row.get('error'),
                                         failed_strikes=[i for i, r in enumerate(row['rows'])
                                                         if not (r['reference']['certified'] and
                                                                 r['european_reference']['certified'] and
                                                                 r['gtfk_numerical_indicator'] <= 1e-6 and
                                                                 r['gtfk_european_numerical_indicator'] <= 1e-6 and
                                                                 r['monotonic'] and r['bounds'])]))
                if len(rows) % 64 == 0:
                    print(json.dumps(dict(split=name, groups=len(rows), failures=len(failures),
                                          elapsed_seconds=time.perf_counter()-start)), flush=True)
        timing[name] = dict(wall_seconds=time.perf_counter()-started,
                            group_cpu_seconds_sum=sum(r['cpu_seconds'] for r in rows),
                            groups=len(rows))
        if failures:
            (out/'gate-failures.json').write_text(json.dumps(failures, indent=2)+'\n')
            break
        for cell in ('FE', 'FB'):
            packed = pack(rows, cell)
            for key, value in packed.items():
                arrays[name+'_'+cell+'_'+key] = value
    summary = dict(stage='formal fixed-coefficient paired put labels',
                   elapsed_seconds=time.perf_counter()-start, timing=timing,
                   failures=len(failures), complete=not failures and len(timing)==len(cfg['splits']),
                   scope='F-E and F-B labels and numerical baselines; no training')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    if not summary['complete']:
        return
    fit = {k:v for k,v in arrays.items() if k.startswith('train_') or k.startswith('val_')}
    np.savez_compressed(out/'data-fit.npz', **fit)
    np.savez_compressed(out/'data-all.npz', **arrays)
    checks = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [out/'data-fit.npz', out/'data-all.npz']}
    (out/'data-sha256.json').write_text(json.dumps(checks, indent=2)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
