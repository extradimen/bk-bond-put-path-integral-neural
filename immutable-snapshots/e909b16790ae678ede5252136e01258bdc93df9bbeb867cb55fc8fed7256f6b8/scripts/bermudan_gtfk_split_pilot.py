"""Governed kink-split integration of GTFK conditional densities."""
import argparse
import json
import pathlib
import time
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.special import roots_legendre
from numerics import grid_for, gt_bond, mixture


def crossings(grid, difference):
    idx=np.flatnonzero(difference[:-1]*difference[1:]<0)
    return [float(grid[i]-difference[i]*(grid[i+1]-grid[i])/(difference[i+1]-difference[i])) for i in idx]


def propagate(c, horizon, starts, grid, values, kinks, nq, ny):
    if c['sigma']==0:
        b=np.log(c['rbar']);starts=np.atleast_1d(starts)
        endpoints=b+(starts-b)*np.exp(-c['a']*horizon)
        interp=PchipInterpolator(grid,values,extrapolate=True)
        return gt_bond(c,horizon,starts,nq=nq)*interp(endpoints)
    weights,means,sd=mixture(c,horizon,starts,nq=nq)
    z,w=roots_legendre(ny)
    interp=PchipInterpolator(grid,values,extrapolate=False)
    total=np.zeros_like(means)
    edges=[grid[0],*sorted(v for v in kinks if grid[0]<v<grid[-1]),grid[-1]]
    for low,high in zip(edges[:-1],edges[1:]):
        left=np.maximum(means-10*sd,low)
        right=np.minimum(means+10*sd,high)
        width=np.maximum(right-left,0)
        mid=(left+right)/2
        nodes=np.clip(mid[:,:,None]+width[:,:,None]*z/2,grid[0],grid[-1])
        pdf=np.exp(-.5*((nodes-means[:,:,None])/sd[:,:,None])**2)/(np.sqrt(2*np.pi)*sd[:,:,None])
        total+=np.sum(interp(nodes)*pdf*w,axis=-1)*width/2
    return np.sum(weights*total,axis=-1)


def price(c,exercise,maturity,strike,n,nq,ny,width_scale=1.5):
    grid=grid_for(c,n,width_scale)
    curve=None;kinks=[];previous=None
    for date in reversed(exercise):
        bond=gt_bond(c,maturity-date,grid,nq=nq)
        raw=strike-bond
        intrinsic=np.maximum(raw,0)
        if curve is None:
            curve=intrinsic;kinks=crossings(grid,raw)
        else:
            continuation=propagate(c,previous-date,grid,grid,curve,kinks,nq,ny)
            curve=np.maximum(intrinsic,continuation)
            kinks=crossings(grid,intrinsic-continuation)
        previous=date
    return float(propagate(c,exercise[0],np.array([np.log(c['r0'])]),grid,curve,kinks,nq,ny)[0])


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    cfg=json.loads(pathlib.Path(a.config).read_text());out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    records=[]
    for case in cfg['cases']:
        rows=[]
        for setting in cfg['settings']:
            n,nq,ny=setting[:3]
            width_scale=setting[3] if len(setting)>3 else 1.5
            start=time.perf_counter()
            e=price(case['model'],[case['exercise'][-1]],case['maturity'],case['strike'],n,nq,ny,width_scale)
            b=price(case['model'],case['exercise'],case['maturity'],case['strike'],n,nq,ny,width_scale)
            rows.append({'n':n,'nq':nq,'ny':ny,'width_scale':width_scale,'european_put':e,'bermudan_put':b,'seconds':time.perf_counter()-start})
        records.append({'name':case['name'],'settings':rows})
    result={'stage':'P3b kink-split GTFK pilot','cases':records,'scope':'numerical quadrature validation; no formal method ranking'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
