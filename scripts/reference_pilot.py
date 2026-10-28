"""Deployment pilot. Monotone implicit PDE; never certifies formal labels."""
import argparse, json, math, pathlib, time, hashlib, platform, signal

def stepper(grid, a, b, sigma, dt):
    n=len(grid); h=grid[1]-grid[0]; d=sigma*sigma/(2*h*h)
    lo=[]; up=[]; diag=[]
    for i,x in enumerate(grid):
        drift=a*(b-x)
        l=d-drift/(2*h); u=d+drift/(2*h)
        if min(l,u)<0: l=d+max(-drift,0)/h; u=d+max(drift,0)/h
        # reflecting truncated generator; domain expansion must be checked
        if i==0: u+=l; l=0
        if i==n-1: l+=u; u=0
        lo.append(-dt*l); up.append(-dt*u); diag.append(1+dt*(l+u+math.exp(x)))
    for i in range(1,n):
        lo[i]/=diag[i-1]; diag[i]-=lo[i]*up[i-1]
    def solve(rhs):
        v=rhs[:]
        for i in range(1,n): v[i]-=lo[i]*v[i-1]
        v[-1]/=diag[-1]
        for i in range(n-2,-1,-1): v[i]=(v[i]-up[i]*v[i+1])/diag[i]
        return v
    return solve

def price(c,n,steps,width):
    x0=math.log(c['r0']); b=math.log(c['rbar']); center=(x0+b)/2
    grid=[center-width+2*width*i/(n-1) for i in range(n)]
    def evolve(v,horizon):
        solve=stepper(grid,c['a'],b,c['sigma'],horizon/steps)
        for _ in range(steps): v=solve(v)
        return v
    bond=evolve([1.0]*n,c['tenor'])
    call=evolve([max(v-c['strike'],0) for v in bond],c['expiry'])
    fullbond=evolve(bond,c['expiry'])
    z=(x0-grid[0])/(grid[1]-grid[0]); i=int(z); w=z-i
    return {'bond':fullbond[i]*(1-w)+fullbond[i+1]*w,'call':call[i]*(1-w)+call[i+1]*w}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--out',required=True); args=p.parse_args()
    raw=pathlib.Path(args.config).read_bytes(); cfg=json.loads(raw)
    def timeout(*_): raise TimeoutError('pilot wall-clock budget exceeded')
    signal.signal(signal.SIGALRM,timeout); signal.alarm(cfg['max_seconds'])
    out=pathlib.Path(args.out); out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter(); rows=[]
    for c in cfg['cases']:
        prices=[price(c,n,t,cfg['domain_halfwidth']) for n,t in cfg['levels']]
        n,t=cfg['levels'][-1]
        # Preserve dx when expanding the domain, avoiding a confounded domain test.
        ne=round((n-1)*cfg['expanded_halfwidth']/cfg['domain_halfwidth'])+1
        expanded=price(c,ne,t,cfg['expanded_halfwidth'])
        row={'parameters':c,'levels':prices,'expanded':expanded,
             'fine_change':{k:abs(prices[-1][k]-prices[-2][k]) for k in ['bond','call']},
             'domain_change':{k:abs(prices[-1][k]-expanded[k]) for k in ['bond','call']}}
        rows.append(row); print(json.dumps(row),flush=True)
    result={'stage':'P0','status':'screening_only','formal_labels_certified':False,'rows':rows,
            'elapsed_seconds':time.perf_counter()-start,'python':platform.python_version(),
            'platform':platform.platform(),'config_sha256':hashlib.sha256(raw).hexdigest(),
            'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    target=out/'results.json'; target.write_text(json.dumps(result,indent=2)+'\n')
    (out/'checksums.sha256').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  results.json\n')
    (out/'FROZEN').write_text('P0 screening only; no training or formal reference certification.\n')
    print(json.dumps({'elapsed_seconds':result['elapsed_seconds'],'output':str(out)}),flush=True)
if __name__=='__main__': main()
