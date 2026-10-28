import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[v]='1'
import json,pathlib,time,hashlib,argparse,signal,tarfile,itertools,resource
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from pilot_learning import sample,one,arrays
from learning import MLP


def fit_job(args):
 datafile,outdir,method,budget,seed,layers,width,lr=args
 data=np.load(datafile);tr=data['train'];va=data['val'];tr=tr[:budget*5]
 X=tr[:,:7];V=va[:,:7];baseindex={'B':None,'C':8,'D':9}[method]
 yy=tr[:,7]-(0 if baseindex is None else tr[:,baseindex]);vy=va[:,7]-(0 if baseindex is None else va[:,baseindex])
 mean=X.mean(0);scale=X.std(0);ym=yy.mean();ys=max(yy.std(),1e-8)
 net=MLP(7,width,layers,seed);fit=net.fit((X-mean)/scale,(yy-ym)/ys,(V-mean)/scale,(vy-ym)/ys,lr,seed)
 val=net.predict((V-mean)/scale)*ys+ym+(0 if baseindex is None else va[:,baseindex])
 tag=f'{method}-{budget}-{seed}-{layers}-{width}-{lr}'
 payload={f'W{i}':w for i,w in enumerate(net.W)};payload.update({f'b{i}':b for i,b in enumerate(net.b)});payload.update(mean=mean,scale=scale,ym=ym,ys=ys)
 path=pathlib.Path(outdir)/(tag+'.npz');np.savez_compressed(path,**payload)
 result={'tag':tag,'method':method,'budget':budget,'seed':seed,'layers':layers,'width':width,'lr':lr,'val_mae':float(np.mean(abs(val-va[:,7]))),'training':fit,'model_file':path.name}
 return result


def load_predict(fit,outdir,X):
 pars=np.load(pathlib.Path(outdir)/fit['model_file']);net=MLP(7,fit['width'],fit['layers'],0)
 for i in range(len(net.W)):net.W[i]=pars[f'W{i}'];net.b[i]=pars[f'b{i}']
 return net.predict((X-pars['mean'])/pars['scale'])*pars['ys']+pars['ym']


def metrics(pred,y):
 e=np.abs(pred-y);return {'mae':float(e.mean()),'q95':float(np.quantile(e,.95)),'q99':float(np.quantile(e,.99)),'max':float(e.max()),'exceed_1e_minus4':float(np.mean(e>1e-4)),'normalized_mae':float(np.mean(e/np.maximum(y,.001)))}


def paired_ci(a,b,seed=20261020):
 delta=np.mean(abs(a),axis=1)-np.mean(abs(b),axis=1);rng=np.random.default_rng(seed)
 means=np.array([rng.choice(delta,len(delta),replace=True).mean() for _ in range(2000)])
 return {'mean':float(delta.mean()),'ci95':np.quantile(means,[.025,.975]).tolist()}


def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);args=p.parse_args();cfg=json.load(open(args.config));assert os.cpu_count()>=cfg['workers'],'worker count exceeds detected CPU count';out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False);models=out/'models';models.mkdir()
 def alarm(*_):raise TimeoutError('Formal main budget exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg['max_seconds']);start=time.perf_counter();datasets={};times={};failure=[]
 for split,n,seed in cfg['splits']:
  cs=sample(n,seed)
  if split=='ood_vol':
   for c in cs:c['sigma']=.8+(c['sigma']-.05)/.75*.2
  if split=='ood_expiry':
   for c in cs:c['expiry']=10+(c['expiry']-.25)/9.75*5
  rows=[];ts=time.perf_counter()
  with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
   for i,row in enumerate(pool.map(one,cs)):
    rows.append(row)
    with (out/(split+'.jsonl')).open('a') as f:f.write(json.dumps(row)+'\n')
    if not row['certified'] or row.get('gt_quadrature_error',0)>1e-6:failure.append({'split':split,'group':i,'certified':row['certified'],'quadrature_error':row.get('gt_quadrature_error')})
    if i%128==0:print(json.dumps({'stage':'data','split':split,'groups':i+1,'elapsed':time.perf_counter()-start}),flush=True)
  times[split]=time.perf_counter()-ts
  if not failure:datasets[split]=np.column_stack(arrays(rows))
 if failure:
  (out/'gate-failures.json').write_text(json.dumps(failure,indent=2));return
 # Freeze labels before any fitting. No test/ood matrices are passed to fit workers.
 np.savez_compressed(out/'data-all.npz',**datasets)
 np.savez_compressed(out/'data-fit.npz',train=datasets['train'],val=datasets['val'])
 (out/'data-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [out/'data-all.npz',out/'data-fit.npz']},indent=2))
 fits=[];jobs=[(str(out/'data-fit.npz'),str(models),m,b,s,l,w,lr) for m,b,s,l,w,lr in itertools.product(['B','C','D'],cfg['budgets'],cfg['seeds'],[3,5],[64,128],[.001,.0003])]
 with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
  for f in pool.map(fit_job,jobs):
   fits.append(f)
   with (out/'fits.jsonl').open('a') as h:h.write(json.dumps(f)+'\n')
   print(json.dumps({'stage':'fit','completed':len(fits),'total':len(jobs),'last':f['tag'],'seconds':f['training']['seconds']}),flush=True)
 selected=[]
 for m,b,s in itertools.product(['B','C','D'],cfg['budgets'],cfg['seeds']):
  pool=[f for f in fits if f['method']==m and f['budget']==b and f['seed']==s]
  best=min(pool,key=lambda x:(x['val_mae'],x['tag']));fixed=next(f for f in pool if f['layers']==3 and f['width']==64 and f['lr']==.001)
  selected.extend([{'selection':'tuned','fit':best},{'selection':'fixed_capacity','fit':fixed}])
 predictions={};scores=[]
 for split in ['test','ood_vol','ood_expiry']:
  data=datasets[split];y=data[:,7];scores.append({'split':split,'method':'A','metrics':metrics(data[:,8],y)})
  for item in selected:
   f=item['fit'];m=f['method'];base=0 if m=='B' else data[:,8 if m=='C' else 9]
   t=time.perf_counter();prediction=load_predict(f,models,data[:,:7])+base;elapsed=time.perf_counter()-t
   key=split+'-'+item['selection']+'-'+f['tag'];predictions[key]=prediction
   scores.append({'split':split,'selection':item['selection'],'method':m,'budget':f['budget'],'seed':f['seed'],'tag':f['tag'],'metrics':metrics(prediction,y),'batch_inference_with_load_seconds':elapsed})
 np.savez_compressed(out/'predictions.npz',**predictions)
 (out/'selected.json').write_text(json.dumps(selected,indent=2)+'\n');(out/'scores.json').write_text(json.dumps(scores,indent=2)+'\n')
 # Paired group-level effects, every strike kept in its parameter group.
 cis=[]
 for split,b,s in itertools.product(['test','ood_vol','ood_expiry'],cfg['budgets'],cfg['seeds']):
  chosen={it['fit']['method']:it['fit'] for it in selected if it['selection']=='tuned' and it['fit']['budget']==b and it['fit']['seed']==s}
  y=datasets[split][:,7];err={m:(predictions[split+'-tuned-'+f['tag']]-y).reshape(-1,5) for m,f in chosen.items()}
  err['A']=(datasets[split][:,8]-y).reshape(-1,5);err['Dbase']=(datasets[split][:,9]-y).reshape(-1,5)
  for left,right in [('B','C'),('B','D'),('A','C'),('A','B'),('Dbase','D'),('C','D')]:cis.append({'split':split,'budget':b,'seed':s,'contrast':left+'_minus_'+right,**paired_ci(err[left],err[right])})
 (out/'paired-ci.json').write_text(json.dumps(cis,indent=2)+'\n')
 from benchmark_online import run as benchmark
 testrows=[json.loads(line) for line in (out/'test.jsonl').read_text().splitlines()]
 (out/'online-benchmark.json').write_text(json.dumps(benchmark(testrows,selected,models,datasets['test']),indent=2)+'\n')
 summary={'stage':'formal_main','data_seconds':times,'fit_seconds_sum':sum(f['training']['seconds'] for f in fits),'fit_cpu_seconds_sum':sum(f['training']['cpu_seconds'] for f in fits),'elapsed_seconds':time.perf_counter()-start,'fits':len(fits),'peak_rss_self':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'experiment_scope':'E1 and inputs for E2-E5; E6 conditional, not yet authorized by gate.'}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 with tarfile.open(out/'models.tar.gz','w:gz') as tar:tar.add(models,arcname='models')
 (out/'checksums.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in out.iterdir() if f.is_file() and f.name!='checksums.sha256'))
 (out/'FROZEN').write_text('Formal main completed; follow-up experiment groups remain.\n')
if __name__=='__main__':main()
