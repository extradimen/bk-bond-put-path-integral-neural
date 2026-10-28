import time,numpy as np
from numerics import gt_price,pde
from learning import MLP

def network(fit,modeldir):
 p=np.load(modeldir/fit['model_file']);net=MLP(7,fit['width'],fit['layers'],0)
 for i in range(len(net.W)):net.W[i]=p[f'W{i}'];net.b[i]=p[f'b{i}']
 mean=p['mean'];scale=p['scale'];ym=p['ym'];ys=p['ys']
 return lambda X:net.predict((X-mean)/scale)*ys+ym

def adaptive_gt(c,K):
 a=gt_price(c,K,96,64);b=gt_price(c,K,192,128)
 if np.max(abs(np.asarray(a['calls'])-b['calls']))>1e-6:b=gt_price(c,K,384,256)
 return np.asarray(b['calls'])

def run(rows,selection,modeldir,data):
 funcs={it['selection']+'-'+it['fit']['method']:network(it['fit'],modeldir)for it in selection if it['fit']['budget']==4096 and it['fit']['seed']==11}
 result={'units':'seconds per request; single=1 strike, surface=5 strikes','scope':'serial CPU after training pool exits; models preloaded, 3 repetitions, first 16 preselected test groups','samples':{}}
 for mode in ['single','surface']:
  records={k:[] for k in ['A','D_baseline',*funcs]}
  for group,row in enumerate(rows[:16]):
   c=row['parameters'];K=row['strikes'][:1]if mode=='single'else row['strikes'];X=data[group*5:group*5+len(K),:7]
   for f in funcs.values():f(X)
   adaptive_gt(c,K);pde(c,201,100,strikes=K)
   for _ in range(3):
    # Cold PDE component cache avoids using reference-generation cache as free work.
    from numerics import _components
    _components.cache_clear();start=time.perf_counter();ap=adaptive_gt(c,K);at=time.perf_counter()-start;records['A'].append(at)
    _components.cache_clear();start=time.perf_counter();dp=np.array(pde(c,201,100,strikes=K)['calls']);dt=time.perf_counter()-start;records['D_baseline'].append(dt)
    for name,f in funcs.items():
     start=time.perf_counter();f(X);nt=time.perf_counter()-start
     # Add independently measured baseline call from the same request.
     records[name].append(nt+(at if name.endswith('-C')else dt if name.endswith('-D')else 0))
  result['samples'][mode]={name:{'median':float(np.median(v)),'q10':float(np.quantile(v,.1)),'q90':float(np.quantile(v,.9)),'observations':len(v),'raw':v}for name,v in records.items()}
 return result
