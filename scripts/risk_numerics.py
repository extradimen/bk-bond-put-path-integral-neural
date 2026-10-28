"""Adaptive derivative certification; same1e-4 gate, fixed option contracts."""
import numpy as np,time
from numerics import pde,gt_price,grid_for,pde_curve
H0=np.array([.004,.001,.004,.004])
def calls_only(c,K,n,nt,width=1):
 # Identical call PDE; omit discount/total-bond solves unused by derivatives.
 g=grid_for(c,n,width);bond=pde_curve(c,c['tenor'],g,nt)
 return pde_curve(c,c['expiry'],g,nt,np.maximum(bond[:,None]-np.asarray(K),0))[n//2]

def shift(c,dim,h):
 d=c.copy()
 if dim==0:d['a']*=np.exp(h)
 elif dim==1:d['sigma']+=h
 elif dim==2:d['r0']*=np.exp(h)
 else:d['rbar']*=np.exp(h)
 return d

def reference(c,K,tol=1e-4):
 cache={};records=[]
 def derivative(dim,h,n,nt,width=1):
  key=(dim,float(h),n,nt,width)
  if key not in cache:cache[key]=(calls_only(shift(c,dim,h),K,n,nt,width)-calls_only(shift(c,dim,-h),K,n,nt,width))/(2*h)
  return cache[key]
 space_level=time_level=0
 for attempt in range(7):
  n=[1601,3201,6401,12801][space_level];nt=[800,1600,3200,6400][time_level]
  nf=2*n-1;tf=2*nt;hs=[];cols=[];step_errors=[];space=[];time_errors=[];space3=[];time3=[];domain=[]
  for j,hstart in enumerate(H0):
   h=float(hstart);large=derivative(j,h,nf,tf)
   for _ in range(6):
    small=derivative(j,h/2,nf,tf);err=float(np.max(abs(small-large)));h/=2
    if err<=tol:break
    large=small
   hs.append(h);cols.append(small);step_errors.append(err)
   # Every check uses precisely the accepted h and identical strike vector.
   space.append(float(np.max(abs(small-derivative(j,h,n,tf)))))
   time_errors.append(float(np.max(abs(small-derivative(j,h,nf,nt)))))
   space3.append(float(np.max(abs(small-derivative(j,h,4*n-3,tf)))))
   time3.append(float(np.max(abs(small-derivative(j,h,nf,4*nt)))))
   domain.append(float(np.max(abs(small-derivative(j,h,3*(n-1)+1,tf,1.5)))))
  errors=[max(v)for v in [space,step_errors,space3,time_errors,time3,domain]];record=dict(n=nf,steps=tf,h=hs,errors=errors,by_coordinate=dict(space=space,step=step_errors,space3=space3,time=time_errors,time3=time3,domain=domain));records.append(record)
  if np.all(np.isfinite(cols)) and max(errors)<=tol:return dict(certified=True,values=np.array(cols).T,h=hs,errors=errors,records=records)
  spatial=max(errors[0],errors[1],errors[2],errors[5])>tol;temporal=max(errors[3],errors[4])>tol
  if (spatial and space_level==3) or (temporal and time_level==3):break
  if spatial:space_level+=1
  if temporal:time_level+=1
 return dict(certified=False,values=np.array(cols).T,h=hs,errors=errors,records=records)

def baselines(c,K,h,tol=1e-4):
 gt=[];coarse=[];qerr=[];gstep=[];dstep=[];meta=[]
 def gd(j,hh,nq):return (np.asarray(gt_price(shift(c,j,hh),K,nq,nq*2//3)['calls'])-np.asarray(gt_price(shift(c,j,-hh),K,nq,nq*2//3)['calls']))/(2*hh)
 def dd(j,hh):return (calls_only(shift(c,j,hh),K,201,100)-calls_only(shift(c,j,-hh),K,201,100))/(2*hh)
 for j,hh0 in enumerate(h):
  hh=hh0;order=384;small=gd(j,hh,192);large=gd(j,hh,order);qe=float(np.max(abs(large-small)))
  if qe>tol:small=large;order=768;large=gd(j,hh,order);qe=float(np.max(abs(large-small)))
  for _ in range(5):
   finer=gd(j,hh/2,order);se=float(np.max(abs(finer-large)));hh/=2
   if se<=tol:break
   large=finer
  # Recheck quadrature at final step; no error cancellation across refinements.
  qfinal=float(np.max(abs(finer-gd(j,hh,order//2))));qerr.append(max(qe,qfinal));gstep.append(se);gt.append(finer)
  hd=hh0;v=dd(j,hd)
  for _ in range(16):
   f=dd(j,hd/2);de=float(np.max(abs(f-v)));hd/=2
   if de<=tol:break
   v=f
  coarse.append(f);dstep.append(de);meta.append(dict(gt_h=hh,gt_order=order,coarse_h=hd))
 return dict(gt=np.array(gt).T,coarse=np.array(coarse).T,quadrature=qerr,gt_step=gstep,coarse_step=dstep,meta=meta,certified=bool(np.all(np.isfinite(gt))and np.all(np.isfinite(coarse))and max(qerr+gstep+dstep)<=tol))
