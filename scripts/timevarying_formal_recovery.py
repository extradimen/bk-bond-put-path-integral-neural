"""Resume certified time-varying put ledgers after a verified terminal run.

This runner is inert until a new, explicitly frozen config supplies SHA-pinned
terminal-run ledgers. It never reads or modifies an active remote deployment.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np

from timevarying_data_pilot import sample
from timevarying_formal_data import evaluate, pack


def prior_rows(spec, cases, split):
    if spec is None:
        return []
    source=Path(spec['path'])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=spec['sha256']:
        raise RuntimeError(f'{split} source ledger SHA-256 mismatch')
    rows=[]
    with source.open() as ledger:
        for index,line in enumerate(ledger):
            row=json.loads(line)
            expected=json.loads(json.dumps(cases[index])) if index<len(cases) else None
            if index>=len(cases) or row.get('group')!=index or row.get('contract')!=expected:
                raise RuntimeError(f'{split} source group/contract identity mismatch at {index}')
            if not row.get('certified') or len(row.get('rows',[]))!=3 or not all(
                    item.get('formal_certified') for item in row['rows']):
                raise RuntimeError(f'{split} source includes an uncertified group at {index}')
            rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    if cfg.get('status')!='frozen' or not cfg.get('source_os_wait_receipt_sha256'):
        raise RuntimeError('terminal-run OS wait receipt and frozen recovery config required')
    receipt=Path(cfg['source_os_wait_receipt'])
    if hashlib.sha256(receipt.read_bytes()).hexdigest()!=cfg['source_os_wait_receipt_sha256']:
        raise RuntimeError('terminal-run OS wait receipt SHA-256 mismatch')
    state=json.loads(receipt.read_text())
    if state.get('termination_evidence')!='os_child_wait_status' or state.get('status')=='running':
        raise RuntimeError('source run not proven terminal by node OS child wait')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    available=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count()
    if available<cfg['workers']:
        raise RuntimeError('frozen worker count exceeds CPU affinity')
    def alarm(*_):raise TimeoutError('time-varying recovery wall budget exceeded')
    signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg['max_seconds'])
    started=time.perf_counter();arrays={};failures=[];timing={}
    for split in cfg['splits']:
        name=split['name'];cases=sample(split['groups'],split['seed'],split['region'])
        rows=prior_rows(cfg['source_ledgers'].get(name),cases,name)
        reused=len(rows);began=time.perf_counter()
        with (out/(name+'.jsonl')).open('w') as ledger:
            for row in rows:
                ledger.write(json.dumps(row)+'\n')
            ledger.flush()
            if reused<len(cases):
                with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
                    for row in pool.map(evaluate,enumerate(cases[reused:],start=reused)):
                        rows.append(row);ledger.write(json.dumps(row)+'\n');ledger.flush()
                        if not row.get('certified'):
                            failures.append(dict(split=name,group=row.get('group'),error=row.get('error')))
                        if len(rows)%64==0:
                            print(json.dumps(dict(split=name,groups=len(rows),reused=reused,
                                                  failures=len(failures),elapsed=time.perf_counter()-started)),flush=True)
        timing[name]=dict(groups=len(rows),reused_groups=reused,new_groups=len(rows)-reused,
                          wall_seconds=time.perf_counter()-began)
        if failures:
            (out/'gate-failures.json').write_text(json.dumps(failures,indent=2)+'\n')
            break
        for cell in ('TE','TB'):
            for key,value in pack(rows,cell).items():
                arrays[name+'_'+cell+'_'+key]=value
    complete=not failures and len(timing)==len(cfg['splits'])
    summary=dict(stage='time-varying formal ledger recovery',complete=complete,
                 failures=len(failures),timing=timing,elapsed_seconds=time.perf_counter()-started,
                 source_os_wait_receipt_sha256=cfg['source_os_wait_receipt_sha256'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if not complete:
        print(json.dumps(summary),flush=True);return
    np.savez_compressed(out/'data-fit.npz',**{k:v for k,v in arrays.items()
                                             if k.startswith('train_') or k.startswith('val_')})
    np.savez_compressed(out/'data-all.npz',**arrays)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (out/'data-fit.npz',out/'data-all.npz')}
    (out/'data-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
