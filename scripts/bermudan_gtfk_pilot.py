"""Governed P3b numerical pilot: GTFK Arrow-Debreu propagation for Bermudan puts."""
import argparse
import json
import pathlib
import time
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.special import roots_hermitenorm
from numerics import grid_for, gt_bond, mixture


def propagate(c, horizon, starts, curve_grid, values, nq, ny):
    weights, means, sd = mixture(c, horizon, starts, nq=nq)
    z,zw=roots_hermitenorm(ny)
    zw=zw/np.sqrt(2*np.pi)
    interp=PchipInterpolator(curve_grid,values,extrapolate=False)
    nodes=means[:,:,None]+sd[:,:,None]*z
    clipped=np.clip(nodes,curve_grid[0],curve_grid[-1])
    conditional=np.sum(interp(clipped)*zw,axis=-1)
    return np.sum(weights*conditional,axis=-1)


def price(c, exercise, maturity, strike, n, nq, ny):
    grid=grid_for(c,n,1.5)
    continuation=None
    previous=None
    for date in reversed(exercise):
        bond=gt_bond(c,maturity-date,grid,nq=nq)
        intrinsic=np.maximum(strike-bond,0)
        if continuation is None:
            continuation=intrinsic
        else:
            continuation=np.maximum(intrinsic,propagate(c,previous-date,grid,grid,continuation,nq,ny))
        previous=date
    return float(propagate(c,exercise[0],np.array([np.log(c['r0'])]),grid,continuation,nq,ny)[0])


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    cfg=json.loads(pathlib.Path(a.config).read_text());out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    records=[]
    for case in cfg['cases']:
        rows=[]
        for n,nq,ny in cfg['settings']:
            t=time.perf_counter()
            euro=price(case['model'],[case['exercise'][-1]],case['maturity'],case['strike'],n,nq,ny)
            berm=price(case['model'],case['exercise'],case['maturity'],case['strike'],n,nq,ny)
            rows.append({'n':n,'nq':nq,'ny':ny,'european':euro,'bermudan':berm,'seconds':time.perf_counter()-t,'bermudan_at_least_european':berm+1e-6>=euro})
        records.append({'name':case['name'],'settings':rows})
    result={'stage':'P3b numerical pilot','cases':records,'scope':'GTFK conditional propagation check only; not a formal method ranking'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if any(not row['bermudan_at_least_european'] for case in records for row in case['settings']):
        raise AssertionError('Bermudan inequality failed; see preserved results')


if __name__=='__main__':main()
