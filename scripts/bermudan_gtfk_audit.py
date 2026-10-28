"""Governed GTFK quadrature and approximate-semigroup diagnostics."""
import argparse
import json
import pathlib
import time
import numpy as np
from numerics import grid_for, gt_bond, mixture
from bermudan_gtfk_pilot import price, propagate


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    cfg=json.loads(pathlib.Path(a.config).read_text());out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    records=[]
    for case in cfg['cases']:
        c=case['model'];x0=np.array([np.log(c['r0'])]);rows=[]
        for n,nq,ny in cfg['settings']:
            t=time.perf_counter();g=grid_for(c,n,1.5)
            direct=gt_bond(c,case['maturity'],x0,nq=nq)[0]
            after=gt_bond(c,case['maturity']-case['exercise'][0],g,nq=nq)
            composed=propagate(c,case['exercise'][0],x0,g,after,nq,ny)[0]
            mass=float(mixture(c,case['exercise'][0],x0,nq=nq,kill=0)[0].sum())
            european=price(c,[case['exercise'][-1]],case['maturity'],case['strike'],n,nq,ny)
            bermudan=price(c,case['exercise'],case['maturity'],case['strike'],n,nq,ny)
            rows.append({'n':n,'nq':nq,'ny':ny,'european_put':european,'bermudan_put':bermudan,
                'direct_bond':float(direct),'composed_bond':float(composed),'semigroup_defect':float(composed-direct),
                'zero_killing_mass_error':mass-1,'seconds':time.perf_counter()-t})
        records.append({'name':case['name'],'settings':rows})
    result={'stage':'P3b GTFK numerical audit','cases':records,'scope':'quadrature versus approximate-kernel composition; no formal method ranking'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
