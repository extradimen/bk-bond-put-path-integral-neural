"""Governed P3a fixed-coefficient Bermudan contract and PDE pilot."""
import argparse
import json
import pathlib
import time
import numpy as np
from numerics import grid_for, pde_curve


def value(c, exercise, maturity, strike, n, steps_per_year, option_type, width_scale=1.0):
    grid = grid_for(c, n, width_scale)
    continuation = None
    previous = maturity
    for date in reversed(exercise):
        bond = pde_curve(c, maturity-date, grid, max(4, round((maturity-date)*steps_per_year)))
        intrinsic = np.maximum((bond-strike) if option_type=='call' else (strike-bond), 0)
        if continuation is None:
            continuation = intrinsic
        else:
            continuation = pde_curve(c, previous-date, grid, max(4, round((previous-date)*steps_per_year)), continuation)
            continuation = np.maximum(intrinsic, continuation)
        previous = date
    today = pde_curve(c, exercise[0], grid, max(4, round(exercise[0]*steps_per_year)), continuation)
    return float(today[n//2])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    cfg=json.loads(pathlib.Path(args.config).read_text())
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False)
    records=[]
    violations=[]
    for case in cfg['cases']:
        prices={}
        for n,rate in cfg['grids']:
            start=time.perf_counter()
            european=value(case['model'],[case['exercise'][-1]],case['maturity'],case['strike'],n,rate,cfg['option_type'])
            bermudan=value(case['model'],case['exercise'],case['maturity'],case['strike'],n,rate,cfg['option_type'])
            prices[str(n)]={'european':european,'bermudan':bermudan,'seconds':time.perf_counter()-start}
            if bermudan+1e-6<european:
                violations.append({'case':case['name'],'grid':n,'gap':european-bermudan})
        records.append({'name':case['name'],'prices':prices})
    result={'stage':'P3a','cases':records,'violations_above_1e-6':violations,'scope':'fixed-coefficient Bermudan PDE pilot only; not a method comparison'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if violations:raise AssertionError('Bermudan inequality violated beyond 1e-6; see results.json')


if __name__=='__main__':main()
