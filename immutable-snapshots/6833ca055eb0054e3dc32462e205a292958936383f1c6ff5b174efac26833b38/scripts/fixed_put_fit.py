"""Frozen F-E/F-B network fitting using train/validation data only."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
import pathlib
import signal
import tarfile
import time

import numpy as np

from learning import MLP


def fit_job(args):
    datafile, modeldir, cell, method, budget, seed, layers, width, lr = args
    with np.load(datafile) as data:
        X = data['train_'+cell+'_X'][:3*budget]
        truth = data['train_'+cell+'_y'][:3*budget]
        A = data['train_'+cell+'_A'][:3*budget]
        Dbase = data['train_'+cell+'_Dbase'][:3*budget]
        V = data['val_'+cell+'_X']
        vtruth = data['val_'+cell+'_y']
        vA = data['val_'+cell+'_A']
        vDbase = data['val_'+cell+'_Dbase']
    base = np.zeros_like(truth) if method == 'B' else A if method == 'C' else Dbase
    vbase = np.zeros_like(vtruth) if method == 'B' else vA if method == 'C' else vDbase
    target = truth-base
    vtarget = vtruth-vbase
    mean = X.mean(axis=0)
    scale = np.maximum(X.std(axis=0), 1e-10)
    ym = target.mean()
    ys = max(target.std(), 1e-8)
    net = MLP(X.shape[1], width, layers, seed)
    fit = net.fit((X-mean)/scale, (target-ym)/ys,
                  (V-mean)/scale, (vtarget-ym)/ys, lr, seed)
    prediction = net.predict((V-mean)/scale)*ys+ym+vbase
    tag = f'{cell}-{method}-{budget}-{seed}-{layers}-{width}-{lr}'
    params = {f'W{i}':w for i,w in enumerate(net.W)}
    params.update({f'b{i}':b for i,b in enumerate(net.b)})
    params.update(mean=mean, scale=scale, ym=ym, ys=ys)
    path = pathlib.Path(modeldir)/(tag+'.npz')
    np.savez_compressed(path, **params)
    return dict(tag=tag, cell=cell, method=method, budget=budget, seed=seed,
                layers=layers, width=width, lr=lr,
                validation_mae=float(np.mean(abs(prediction-vtruth))),
                fit=fit, model_file=path.name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--data')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    cfg = json.loads(pathlib.Path(args.config).read_text())
    datafile = args.data or cfg['data_file']
    actual_sha = hashlib.sha256(pathlib.Path(datafile).read_bytes()).hexdigest()
    if actual_sha != cfg['data_fit_sha256']:
        raise RuntimeError('fit data checksum does not match frozen config')
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    models = out/'models'
    models.mkdir()
    def alarm(*_):
        raise TimeoutError('paired-put fitting exceeded frozen wall-clock budget')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(cfg['max_seconds'])
    jobs = [(datafile, str(models), cell, method, budget, seed, layers, width, lr)
            for cell, method, budget, seed, layers, width, lr in itertools.product(
                cfg['cells'], cfg['methods'], cfg['budgets'], cfg['seeds'],
                cfg['layers'], cfg['widths'], cfg['learning_rates'])]
    if len(jobs) != 720:
        raise RuntimeError('candidate count differs from frozen protocol')
    started = time.perf_counter()
    fits = []
    with ProcessPoolExecutor(max_workers=cfg['workers']) as pool, (out/'fits.jsonl').open('w') as ledger:
        for fit in pool.map(fit_job, jobs):
            fits.append(fit)
            ledger.write(json.dumps(fit)+'\n')
            ledger.flush()
            if len(fits)%24 == 0:
                print(json.dumps(dict(completed=len(fits), total=len(jobs),
                                      elapsed_seconds=time.perf_counter()-started)), flush=True)
    selected = []
    for cell, method, budget, seed in itertools.product(cfg['cells'], cfg['methods'],
                                                        cfg['budgets'], cfg['seeds']):
        candidates = [f for f in fits if (f['cell'],f['method'],f['budget'],f['seed']) ==
                      (cell,method,budget,seed)]
        best = min(candidates, key=lambda f:(f['validation_mae'],f['tag']))
        fixed = next(f for f in candidates if f['layers']==3 and f['width']==64 and f['lr']==.001)
        selected += [dict(selection='tuned', fit=best), dict(selection='fixed_capacity', fit=fixed)]
    (out/'selected.json').write_text(json.dumps(selected, indent=2)+'\n')
    with tarfile.open(out/'models.tar.gz', 'w:gz') as archive:
        archive.add(models, arcname='models')
    summary = dict(stage='formal '+('/'.join(cfg['cells']))+' B/C/D fits', fits=len(fits),
                   selected=len(selected), elapsed_seconds=time.perf_counter()-started,
                   fit_cpu_seconds_sum=sum(f['fit']['cpu_seconds'] for f in fits),
                   data_fit_sha256=actual_sha)
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    checks = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [out/'selected.json',out/'models.tar.gz',out/'fits.jsonl']}
    (out/'checksums.json').write_text(json.dumps(checks, indent=2)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
