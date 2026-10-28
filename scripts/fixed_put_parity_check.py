"""Frozen European put-call parity check against independently certified put labels."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse, hashlib, json, pathlib, time
import numpy as np
from numerics import grid_for, pde_curve


def one(x, reference, n, rate):
    c={'a':float(np.exp(x[0])),'sigma':float(x[1]),'r0':float(np.exp(x[2])),
       'rbar':float(np.exp(x[3]))}
    expiry,maturity,strike=map(float,x[4:7]);g=grid_for(c,n);mid=n//2
    bond=pde_curve(c,maturity-expiry,g,max(4,round((maturity-expiry)*rate)))
    terminal=np.column_stack((np.maximum(bond-strike,0),np.maximum(strike-bond,0),bond,np.ones(n)))
    today=pde_curve(c,expiry,g,max(4,round(expiry*rate)),terminal)[mid]
    call,put,zcb,disc=map(float,today)
    implied=call-zcb+strike*disc
    return dict(call=call,direct_put=put,parity_put=implied,reference_put=float(reference),
                bond=zcb,discount=disc,parity_gap=implied-put,
                reference_gap=implied-float(reference))


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();cfg=json.loads(pathlib.Path(a.config).read_text())
    source=pathlib.Path(cfg['data_file'])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=cfg['data_sha256']:
        raise RuntimeError('frozen data hash mismatch')
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    rows=[];start=time.perf_counter()
    with np.load(source) as d:
        for split,groups in cfg['groups'].items():
            X=d[split+'_FE_X'];Y=d[split+'_FE_y']
            for group in groups:
                for strike_index in range(3):
                    i=3*group+strike_index;settings=[]
                    for n,rate in cfg['settings']:
                        settings.append(dict(n=n,steps_per_year=rate,**one(X[i],Y[i],n,rate)))
                    fine=settings[-1];coarse=settings[-2]
                    rows.append(dict(split=split,group=group,strike_index=strike_index,
                                     settings=settings,passed=abs(fine['parity_gap'])<=cfg['algebra_tolerance']
                                     and abs(fine['reference_gap'])<=cfg['reference_tolerance']
                                     and abs(fine['parity_put']-coarse['parity_put'])<=cfg['refinement_tolerance']))
    failures=[dict(split=r['split'],group=r['group'],strike_index=r['strike_index']) for r in rows if not r['passed']]
    summary=dict(stage='fixed European put-call parity',cases=len(rows),failures=failures,
                 passed=not failures,max_algebra_gap=max(abs(r['settings'][-1]['parity_gap']) for r in rows),
                 max_reference_gap=max(abs(r['settings'][-1]['reference_gap']) for r in rows),
                 max_refinement_change=max(abs(r['settings'][-1]['parity_put']-r['settings'][-2]['parity_put']) for r in rows),
                 elapsed_seconds=time.perf_counter()-start,
                 scope='European F-E only; call/put/bond/discount use same PDE propagator, so algebraic parity is an implementation check; independently certified formal put labels provide the separate reference check')
    (out/'checks.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
