"""Preselected OU-split crosschecks for frozen F-E/F-B numerical labels."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import pathlib
import time

import numpy as np

from bermudan_split_crosscheck import value as split_value


def check(item):
    split, group, strike_index, cell, c, exercise, maturity, strike, reference, settings = item
    started=time.perf_counter()
    dates=[exercise[-1]] if cell=='FE' else exercise
    prices=[]
    try:
        for n,steps,order,width in settings:
            prices.append(split_value(c,dates,maturity,strike,n,steps,order,width))
        return dict(split=split,group=group,strike_index=strike_index,cell=cell,
                    reference=reference,settings=settings,prices=prices,
                    difference=prices[-1]-reference,
                    refinement_change=prices[-1]-prices[-2],
                    seconds=time.perf_counter()-started)
    except Exception as exc:
        return dict(split=split,group=group,strike_index=strike_index,cell=cell,
                    reference=reference,settings=settings,prices=prices,
                    error=type(exc).__name__+': '+str(exc),
                    seconds=time.perf_counter()-started)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    cfg=json.loads(pathlib.Path(args.config).read_text())
    if hashlib.sha256(pathlib.Path(cfg['data_file']).read_bytes()).hexdigest()!=cfg['data_all_sha256']:
        raise RuntimeError('formal data checksum mismatch')
    out=pathlib.Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    items=[]
    with np.load(cfg['data_file']) as data:
        for split,groups in cfg['selected_groups'].items():
            for group in groups:
                strike_indices=[0,1,2] if group==0 else [1]
                for j in strike_indices:
                    row=3*group+j
                    features=data[split+'_FB_X'][row]
                    c=dict(a=float(np.exp(features[0])),sigma=float(features[1]),
                           r0=float(np.exp(features[2])),rbar=float(np.exp(features[3])))
                    exercise=[float(x) for x in features[4:7]]
                    maturity=float(features[7])
                    strike=float(features[8])
                    for cell in ('FE','FB'):
                        reference=float(data[split+'_'+cell+'_y'][row])
                        items.append((split,group,j,cell,c,exercise,maturity,strike,
                                      reference,cfg['settings']))
    started=time.perf_counter()
    rows=[]
    with ProcessPoolExecutor(max_workers=cfg['workers']) as pool, (out/'checks.jsonl').open('w') as ledger:
        for row in pool.map(check,items):
            rows.append(row)
            ledger.write(json.dumps(row)+'\n')
            ledger.flush()
            print(json.dumps(dict(split=row['split'],group=row['group'],cell=row['cell'],
                                  strike_index=row['strike_index'],
                                  difference=row.get('difference'),error=row.get('error'))),flush=True)
    failures=[dict(split=r['split'],group=r['group'],cell=r['cell'],
                   strike_index=r['strike_index'],difference=r.get('difference'),
                   refinement_change=r.get('refinement_change'),error=r.get('error'))
              for r in rows if r.get('error') or abs(r['difference'])>cfg['tolerance']
              or abs(r['refinement_change'])>cfg['tolerance']]
    summary=dict(stage='independent OU split check of frozen fixed-put labels',
                 cases=len(rows),failures=failures,passed=not failures,
                 elapsed_seconds=time.perf_counter()-started,
                 tolerance=cfg['tolerance'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),passed=not failures,failures=len(failures))),flush=True)


if __name__=='__main__':
    main()
