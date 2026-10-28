"""Independent spatial/time refinement, original strict convergence gates retained."""
import numpy as np
from numerics import pde

def certified_fixed(c,K,tol=1e-7):
 records=[];ns=[1601,3201,6401,12801,25601,51201];ts=[800,1600,3200,6400,12800];si=ti=0
 flat=lambda d:np.array([d['bond'],d['discount'],*d['calls']])
 for _ in range(len(ns)+len(ts)-1):
  n,steps=ns[si],ts[ti]
  base=pde(c,n,2*steps,strikes=K);sp=pde(c,2*n-1,steps,strikes=K);tm=pde(c,2*n-1,2*steps,strikes=K);wide=pde(c,3*(n-1)+1,2*steps,1.5,K)
  changes=[float(np.max(abs(flat(tm)-flat(base)))),float(np.max(abs(flat(tm)-flat(sp)))),float(np.max(abs(flat(wide)-flat(tm))))]
  rec={'n':n,'steps':steps,'space_time_domain':changes};records.append(rec)
  spatial=max(changes[0],changes[2])>tol;temporal=changes[1]>tol
  if not spatial and not temporal:
   s3=pde(c,4*n-3,2*steps,strikes=K);t3=pde(c,2*n-1,4*steps,strikes=K)
   es=float(np.max(abs(flat(s3)-flat(tm))));et=float(np.max(abs(flat(t3)-flat(tm))));rec.update(third_space=es,third_time=et)
   spatial=es>tol or es>changes[0]+1e-10;temporal=et>tol or et>changes[1]+1e-10
   if not spatial and not temporal and np.all(np.isfinite(flat(tm))):return dict(certified=True,reference=tm,strikes=list(K),checks=records,final_contract_checks=[changes[0],changes[1],es,et,changes[2]],third_space=es,third_time=et,n=2*n-1,steps=2*steps)
  if (spatial and si==len(ns)-1) or (temporal and ti==len(ts)-1):break
  si+=int(spatial);ti+=int(temporal)
 return dict(certified=False,checks=records,parameters=c)
