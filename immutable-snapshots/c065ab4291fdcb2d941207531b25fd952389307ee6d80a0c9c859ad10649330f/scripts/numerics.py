"""BK finite differences and constant-coefficient GTFK; float64 throughout.
GTFK source: Stedman & Capriotti (2024), equations 60,64,67,72,46.
"""
import numpy as np
from functools import lru_cache
from scipy.linalg.lapack import dgttrf,dgttrs
from scipy.special import roots_legendre
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq


def grid_for(c,n,width_scale=1):
    x=np.log(c['r0']); b=np.log(c['rbar'])
    width=max(abs(b-x)+9*c['sigma']/np.sqrt(2*c['a']),0.5)*width_scale
    return np.linspace(x-width,x+width,n)


def pde_curve(c,horizon,grid,steps,payoff=None):
    dx=grid[1]-grid[0]; mu=c['a']*(np.log(c['rbar'])-grid); d=c['sigma']**2/(2*dx*dx)
    lower=d-mu/(2*dx); upper=d+mu/(2*dx)
    bad=(lower<0)|(upper<0)
    lower[bad]=d+np.maximum(-mu[bad],0)/dx; upper[bad]=d+np.maximum(mu[bad],0)/dx
    upper[0]+=lower[0]; lower[0]=0; lower[-1]+=upper[-1]; upper[-1]=0
    diag=-lower-upper-np.exp(grid)
    v=np.ones(len(grid)) if payoff is None else np.asarray(payoff).copy()
    def make(dt,theta):
        dl,dd,du,du2,ipiv,info=dgttrf(-theta*dt*lower[1:],1-theta*dt*diag,-theta*dt*upper[:-1])
        if info: raise RuntimeError(('factor',info))
        def advance(v):
            rhs=v.copy()
            if theta<1:
                rhs+=(1-theta)*dt*diag[:,None]*v if v.ndim==2 else (1-theta)*dt*diag*v
                rhs[1:]+=(1-theta)*dt*(lower[1:,None]*v[:-1] if v.ndim==2 else lower[1:]*v[:-1])
                rhs[:-1]+=(1-theta)*dt*(upper[:-1,None]*v[1:] if v.ndim==2 else upper[:-1]*v[1:])
            val,info=dgttrs(dl,dd,du,du2,ipiv,np.asfortranarray(rhs.reshape(len(grid),-1)))
            if info: raise RuntimeError(('solve',info))
            return val if v.ndim==2 else val[:,0]
        return advance
    dt=horizon/steps
    half=make(dt/2,1)
    for _ in range(4): v=half(v)
    full=make(dt,0.5)
    for _ in range(steps-2): v=full(v)
    return v


@lru_cache(maxsize=64)
def _components(items,n,steps,width_scale):
    c=dict(items);g=grid_for(c,n,width_scale)
    bond=pde_curve(c,c['tenor'],g,steps)
    disc=pde_curve(c,c['expiry'],g,steps)
    total=pde_curve(c,c['expiry'],g,steps,bond)
    return g,bond,disc,total


def pde(c,n=1601,steps=800,width_scale=1,strikes=None):
    g,bond,disc,total=_components(tuple(sorted(c.items())),n,steps,width_scale);mid=n//2
    if strikes is None: strikes=np.array([c.get('strike',0.85)])
    strikes=np.asarray(strikes)
    calls=pde_curve(c,c['expiry'],g,steps,np.maximum(bond[:,None]-strikes,0))[mid]
    return dict(bond=float(total[mid]),discount=float(disc[mid]),calls=calls.tolist())


def alpha_fn(omega,T,sigma):
    f=omega*T/2
    delta=np.where(f<0.01,f/3-f**3/45+2*f**5/945,1/np.tanh(f)-1/f)
    return sigma*sigma/(2*omega)*delta


def mixture(c,T,x0,nq=96,kill=1,rate_kind="exponential"):
    # c integrates centroid shifted by b, with support based on exact OU centroid.
    a=c['a']; s=c['sigma']; b=np.log(c['rbar']); q=np.atleast_1d(x0)-b
    z,w=roots_legendre(nq); at=a*T
    # quadrature of centroid covariance is stable even for small a*T
    t,tw=roots_legendre(32); u=(t+1)*T/2
    var=np.sum(tw*(s*(-np.expm1(-a*u))/a/T)**2)*T/2
    mean=q*(-np.expm1(-at))/at
    cent=mean[:,None]+10*np.sqrt(var)*z
    weights=10*np.sqrt(var)*w
    lower=np.full_like(cent,a)
    upper=np.sqrt(a*a+kill*s*s*np.exp(b+cent+alpha_fn(lower,T,s)/2)) if rate_kind=="exponential" else lower.copy()
    # The residual is monotone increasing: alpha decreases with omega.
    for _ in range(100):
        omega=(lower+upper)/2
        residual=omega*omega-a*a-(kill*s*s*np.exp(b+cent+alpha_fn(omega,T,s)/2) if rate_kind=="exponential" else 0)
        lower=np.where(residual<0,omega,lower)
        upper=np.where(residual>=0,omega,upper)
        if np.max((upper-lower)/np.maximum(upper,1.))<1e-13:break
    else:raise RuntimeError('GTFK bracketed root not converged')
    omega=(lower+upper)/2
    al=alpha_fn(omega,T,s); f=omega*T/2; wc=omega/np.tanh(f)
    rate_average=np.exp(b+cent+al/2) if rate_kind=="exponential" else b+cent
    pot=a*a*(cent*cent+al)/(2*s*s)-a/2+kill*rate_average-omega*omega*al/(2*s*s)
    A=1/(8*al)+wc/(4*s*s)+a/(2*s*s)
    B=(cent-q[:,None]/2)/(2*al)+wc*q[:,None]/(2*s*s)
    C=-(q[:,None]/2-cent)**2/(2*al)-wc*q[:,None]**2/(4*s*s)+a*q[:,None]**2/(2*s*s)-T*pot
    logsinh=f+np.log(-np.expm1(-2*f))-np.log(2)
    logpref=-0.5*np.log(2*np.pi*s*s*T)+np.log(f)-logsinh-0.5*np.log(2*np.pi*al)
    weight=np.exp(logpref+C+B*B/(4*A)+0.5*np.log(np.pi/A))*weights
    return weight,b+B/(2*A),np.sqrt(1/(2*A))


def gt_bond(c,T,x0,nq=96,kill=1):
    if c['sigma']==0:
        z,w=roots_legendre(96);u=(z+1)*T/2;b=np.log(c['rbar']);x=np.atleast_1d(x0)
        rate=np.exp(b+(x[:,None]-b)*np.exp(-c['a']*u))
        return np.exp(-kill*(rate@w)*T/2)
    return mixture(c,T,x0,nq,kill)[0].sum(axis=1)


def gt_price(c,strikes,nq=96,ny=64,both=False):
    x0=np.log(c['r0']); strikes=np.asarray(strikes)
    if c['sigma']==0:
        b=np.log(c['rbar']);xt=b+(x0-b)*np.exp(-c['a']*c['expiry'])
        disc=gt_bond(c,c['expiry'],x0,nq)[0];bond=gt_bond(c,c['tenor'],xt,nq)[0]
        return dict(bond=float(disc*bond),discount=float(disc),calls=(disc*np.maximum(bond-strikes,0)).tolist(),puts=(disc*np.maximum(strikes-bond,0)).tolist() if both else None)
    w,mu,sd=mixture(c,c['expiry'],x0,nq)
    w=w[0]; mu=mu[0]; sd=sd[0]
    keep=w>1e-14/len(w); w=w[keep];mu=mu[keep];sd=sd[keep]
    if not len(w):return dict(bond=0.,discount=0.,calls=[0. for _ in strikes],puts=[0. for _ in strikes] if both else None)
    # independent outer payoff curve, no PDE label enters this method
    lo=float(np.min(mu-12*sd)); hi=float(np.max(mu+12*sd))
    yg=np.linspace(lo,hi,4*nq+1)
    bg=gt_bond(c,c['tenor'],yg,nq)
    interp=PchipInterpolator(yg,bg)
    z,zw=roots_legendre(ny); vals=[];putvals=[]
    for K in strikes:
        roots=interp.solve(y=K,extrapolate=False)
        edges=np.unique(np.r_[lo,roots[(roots>lo)&(roots<hi)],hi])
        value=0.;putvalue=0.
        for leftedge,rightedge in zip(edges[:-1],edges[1:]):
            call_interval=interp((leftedge+rightedge)/2)>K
            if not call_interval and not both:continue
            left=np.maximum(mu-10*sd,leftedge);right=np.minimum(mu+10*sd,rightedge)
            right=np.maximum(right,left)
            yy=(left[:,None]+right[:,None])/2+(right-left)[:,None]*z/2
            pdf=np.exp(-0.5*((yy-mu[:,None])/sd[:,None])**2)/(np.sqrt(2*np.pi)*sd[:,None])
            payoff=np.maximum(interp(yy)-K,0) if call_interval else np.maximum(K-interp(yy),0)
            expectation=np.sum(zw*pdf*payoff,axis=1)*(right-left)/2
            if call_interval:value+=float(w@expectation)
            else:putvalue+=float(w@expectation)
        vals.append(value);putvals.append(putvalue)
    return dict(bond=float(gt_bond(c,c['tenor']+c['expiry'],x0,nq)[0]),discount=float(w.sum()),calls=vals,puts=putvals if both else None)

def independent_split(c,n=3201,steps=800,order=16):
    """Exact OU Gaussian propagation + Strang killing, cubic interpolation.
    Independent of PDE stencils/time stepper; convergence still required.
    """
    from scipy.special import roots_hermitenorm
    from scipy.interpolate import CubicSpline
    g=grid_for(c,n); b=np.log(c['rbar']);a=c['a'];s=c['sigma'];z,w=roots_hermitenorm(order);w=w/np.sqrt(2*np.pi)
    def evolve(v,T):
        dt=T/steps;discount=np.exp(-np.exp(g)*dt/2)
        nodes=b+(g[:,None]-b)*np.exp(-a*dt)+s*np.sqrt(-np.expm1(-2*a*dt)/(2*a))*z
        nodes=np.clip(nodes,g[0],g[-1])
        for _ in range(steps):
            v=discount*(CubicSpline(g,v*discount)(nodes)@w)
        return v
    bond=evolve(np.ones(n),c['tenor']);call=evolve(np.maximum(bond-c['strike'],0),c['expiry']);total=evolve(bond,c['expiry'])
    return {'bond':float(total[n//2]),'calls':[float(call[n//2])]}


def certified(c,moneyness=(.8,.9,1,1.1,1.2),tol=1e-6,fixed_strikes=None):
    """Certify one ACTUAL contract on independent spatial/time/domain sequences.
    Forward strikes are constructed from the candidate fine bond pair first;
    all option checks then use exactly those strikes, avoiding redundant solves.
    """
    records=[]
    flat=lambda d:np.array([d['bond'],d['discount'],*d['calls']])
    for n,steps in [(1601,800),(3201,1600),(6401,3200),(12801,6400)]:
        _,_,disc,total=_components(tuple(sorted(c.items())),2*n-1,2*steps,1)
        strikes=np.asarray(moneyness)*total[n-1]/disc[n-1] if fixed_strikes is None else np.asarray(fixed_strikes)
        base=pde(c,n,2*steps,strikes=strikes)
        sp=pde(c,2*n-1,steps,strikes=strikes)
        tm=pde(c,2*n-1,2*steps,strikes=strikes)
        wide=pde(c,3*(n-1)+1,2*steps,1.5,strikes)
        changes=[float(np.max(abs(flat(tm)-flat(base)))),float(np.max(abs(flat(tm)-flat(sp)))),float(np.max(abs(flat(wide)-flat(tm))))]
        record={'n':n,'steps':steps,'space_time_domain':changes};records.append(record)
        if max(changes)>tol:continue
        s3=pde(c,4*n-3,2*steps,strikes=strikes)
        t3=pde(c,2*n-1,4*steps,strikes=strikes)
        err_s=float(np.max(abs(flat(s3)-flat(tm))));err_t=float(np.max(abs(flat(t3)-flat(tm))))
        record.update(third_space=err_s,third_time=err_t)
        if err_s<=tol and err_t<=tol and err_s<=changes[0]+1e-10 and err_t<=changes[1]+1e-10:
            return {'certified':True,'reference':tm,'strikes':strikes.tolist(),'checks':records,'final_contract_checks':[changes[0],changes[1],err_s,err_t,changes[2]],'third_space':err_s,'third_time':err_t,'n':2*n-1,'steps':2*steps}
    return {'certified':False,'checks':records,'parameters':c}
