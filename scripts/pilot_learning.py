import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[v]='1'
import argparse,json,pathlib,time,signal,hashlib,platform
import numpy as np
from numerics import certified,pde,gt_price,independent_split
from learning import MLP
from concurrent.futures import ProcessPoolExecutor

def sample(n,seed):
 rng=np.random.default_rng(seed);u=rng.random((n,6)); arr=[]
 for v in u:
  log=lambda lo,hi,z:float(np.exp(np.log(lo)+(np.log(hi)-np.log(lo))*z))
  arr.append(dict(a=log(.05,2,v[0]),sigma=float(.05+.75*v[1]),r0=log(.005,.10,v[2]),rbar=log(.005,.10,v[3]),expiry=float(.25+9.75*v[4]),tenor=float(.25+19.75*v[5])))
 return arr

def _one(c):
 start=time.perf_counter();cpu=time.process_time();r=certified(c);r['parameters']=c;r['reference_seconds']=time.perf_counter()-start;r['reference_cpu_seconds']=time.process_time()-cpu
 if not r['certified']:return r
 gt_start=time.perf_counter();gt_cpu=time.process_time();t=time.perf_counter();a=gt_price(c,r['strikes'],96,64);r['gt_seconds']=time.perf_counter()-t
 # convergence of baseline quadrature is distinct from GTFK approximation error
 t=time.perf_counter();a2=gt_price(c,r['strikes'],192,128);r['gt_check_seconds']=time.perf_counter()-t
 r['gt_quadrature_error']=float(np.max(abs(np.asarray(a['calls'])-a2['calls'])))
 if r['gt_quadrature_error']>1e-6:
  a3=gt_price(c,r['strikes'],384,256);r['gt_quadrature_error']=float(np.max(abs(np.asarray(a2['calls'])-a3['calls'])));a2=a3
 r['gt']=a2['calls'];r['gt_total_seconds']=time.perf_counter()-gt_start;r['gt_cpu_seconds']=time.process_time()-gt_cpu
 if not np.all(np.isfinite(r['gt'])) or not np.isfinite(r['gt_quadrature_error']):raise FloatingPointError('nonfinite GTFK output')
 t=time.perf_counter();cpu=time.process_time();r['coarse']=pde(c,201,100,strikes=r['strikes'])['calls'];r['coarse_seconds']=time.perf_counter()-t;r['coarse_cpu_seconds']=time.process_time()-cpu
 return r

def one(c):
 try:return _one(c)
 except Exception as exc:return {'parameters':c,'certified':False,'failure_stage':'pricing','error':type(exc).__name__+': '+str(exc)}

def arrays(rows):
 X=[];Y=[];A=[];D=[]
 for row in rows:
  c=row['parameters']
  for j,K in enumerate(row['strikes']):
   X.append([np.log(c['a']),c['sigma'],np.log(c['r0']),np.log(c['rbar']),c['expiry'],c['tenor'],K]);Y.append(row['reference']['calls'][j]);A.append(row['gt'][j]);D.append(row['coarse'][j])
 return tuple(np.asarray(v) for v in [X,Y,A,D])

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);args=p.parse_args();cfg=json.load(open(args.config));out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False)
 def alarm(*_):raise TimeoutError('P2 budget exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg['max_seconds']);start=time.perf_counter()
 checks=[]
 for c in cfg['independent_cases']:
  q1=independent_split(c,3201,400);q2=independent_split(c,6401,800);ref=pde(c,6401,1600)
  delta={k:float(np.max(abs(np.asarray(q2[k])-ref[k]))) for k in ['bond','calls']}
  checks.append({'parameters':c,'coarse':q1,'fine':q2,'pde':ref,'difference':delta})
 (out/'independent-check.json').write_text(json.dumps(checks,indent=2)+'\n')
 cs=sample(cfg['train_groups'],20261017)+sample(cfg['validation_groups'],20261018)
 rows=[]
 with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
  for i,row in enumerate(pool.map(one,cs)):
   rows.append(row)
   with (out/'data.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
   if i%16==0: print(json.dumps({'groups_done':i+1,'elapsed':time.perf_counter()-start}),flush=True)
 failures=[i for i,r in enumerate(rows) if not r['certified']]
 qbad=[i for i,r in enumerate(rows) if r.get('gt_quadrature_error',0)>1e-6]
 summary={'failures':failures,'quadrature_failures':qbad,'stage':'P2','fits':[],'data_seconds':time.perf_counter()-start}
 if not failures and not qbad and all(max(c['difference'].values())<=1e-6 for c in checks):
  tr=arrays(rows[:cfg['train_groups']]);va=arrays(rows[cfg['train_groups']:]);mean=tr[0].mean(0);scale=tr[0].std(0);X=(tr[0]-mean)/scale;V=(va[0]-mean)/scale
  for method,idx in [('B',None),('C',2),('D',3)]:
   y=tr[1]-(0 if idx is None else tr[idx]);vy=va[1]-(0 if idx is None else va[idx]);ym=y.mean();ys=max(y.std(),1e-8)
   model=MLP(7,64,3,11);fit=model.fit(X,(y-ym)/ys,V,(vy-ym)/ys,.001,11,epochs=500)
   pred=model.predict(V)*ys+ym+(0 if idx is None else va[idx]);fit.update(method=method,validation_mae=float(np.mean(abs(pred-va[1]))));summary['fits'].append(fit)
   print(json.dumps({'method':method,'seconds':fit['seconds'],'epochs':fit['epochs']}),flush=True)
 summary['elapsed_seconds']=time.perf_counter()-start
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 (out/'checksums.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in out.iterdir() if f.is_file() and f.name!='checksums.sha256'))
 (out/'FROZEN').write_text('P2 timing and validation; final test not accessed.\n')
if __name__=='__main__':main()
