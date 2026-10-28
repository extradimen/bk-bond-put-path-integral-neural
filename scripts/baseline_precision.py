import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[v]='1'
import numpy as np,json,pathlib,time,hashlib,argparse,signal
from concurrent.futures import ProcessPoolExecutor
from numerics import pde,certified
from learning import MLP
from pilot_learning import arrays

def prices(task):
 row,n,steps=task;t=time.process_time();v=pde(row['parameters'],n,steps,strikes=row['strikes'])['calls'];return v,time.process_time()-t

def fine_test(job):
 row,previous=job
 if previous is not None and previous['certified']:
  assert np.array_equal(previous['strikes'],row['strikes']), 'Fine-label contract mismatch'
  return previous
 if previous is not None:assert previous['parameters']==row['parameters'], 'Failed-reference input mismatch'
 from reference_refinement import certified_fixed
 t=time.process_time();r=certified_fixed(row['parameters'],row['strikes'],tol=1e-7);r['cpu_seconds']=time.process_time()-t
 if previous is not None:r['previous_failed_cpu_seconds']=previous['cpu_seconds'];r['cpu_seconds']+=previous['cpu_seconds']
 return r

def train_predict(task):
 tag,X,y,V,vy,Z,basepred,seed=task;mean=X.mean(0);scale=X.std(0);ym=y.mean();ys=max(y.std(),1e-8)
 net=MLP(7,64,3,seed);fit=net.fit((X-mean)/scale,(y-ym)/ys,(V-mean)/scale,(vy-ym)/ys,.001,seed)
 pred=net.predict((Z-mean)/scale)*ys+ym+basepred;fit['tag']=tag
 return fit,pred,{**{f'W{i}':w for i,w in enumerate(net.W)},**{f'b{i}':b for i,b in enumerate(net.b)},'mean':mean,'scale':scale,'ym':ym,'ys':ys}

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def alarm(*_):raise TimeoutError('Supplement budget exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg['max_seconds']);start=time.perf_counter();rows={sp:[json.loads(s)for s in pathlib.Path(cfg['data_root'],sp+'.jsonl').read_text().splitlines()]for sp in ['train','val','test']};data={sp:arrays(r)for sp,r in rows.items()}
 fine=[];previous=[json.loads(s) for s in pathlib.Path(cfg['previous_fine']).read_text().splitlines()] if cfg.get('previous_fine') else [];assert len(previous)<=512;previous += [None]*(512-len(previous))
 with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
  for i,r in enumerate(pool.map(fine_test,zip(rows['test'][:512],previous))):
   fine.append(r)
   with (out/'fine-test.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
   if i%32==0:print(json.dumps({'stage':'fine_test','groups':i+1}),flush=True)
 if any(not r['certified']for r in fine):
  (out/'gate-failures.json').write_text(json.dumps({'failed_fine_test_groups':[i for i,r in enumerate(fine)if not r['certified']]}));return
 np.savez_compressed(out/'fine-test-reference.npz',reference=np.concatenate([r['reference']['calls']for r in fine]))
 candidates={};timing={}
 for n,steps in [(51,50),(101,100),(201,100),(401,200)]:
  with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:result=list(pool.map(prices,[(r,n,steps)for r in rows['val']]))
  candidates[str(n)]=np.asarray([r[0]for r in result]).reshape(-1);timing[str(n)]=sum(r[1]for r in result)
 target=np.mean(abs(data['val'][2]-data['val'][1]));errors={n:float(np.mean(abs(v-data['val'][1])))for n,v in candidates.items()}
 chosen=min(errors,key=lambda n:abs(np.log(max(errors[n],1e-15)/max(target,1e-15))));steps={51:50,101:100,201:100,401:200}[int(chosen)]
 matched={'val':candidates[chosen]};matched_times={}
 for sp in ['train','test']:
  source=rows[sp][:1024] if sp=='train' else rows[sp]
  with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:result=list(pool.map(prices,[(r,int(chosen),steps)for r in source]))
  matched[sp]=np.asarray([r[0]for r in result]).reshape(-1);matched_times[sp]=sum(r[1]for r in result)
 # E5 lower-precision labels are medium PDE, distinct from D's coarse baseline.
 with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:result=list(pool.map(prices,[(r,401,200)for r in rows['train']]))
 low=np.asarray([r[0]for r in result]).reshape(-1);cost=np.asarray([r[1]for r in result]);budget=sum(r['reference_cpu_seconds'] for r in rows['train'][:256]);maxgroups=int(np.sum(np.cumsum(cost)<=budget));maxgroups=min(len(rows['train']),maxgroups)
 if maxgroups<1:raise RuntimeError('label budget cannot cover one low-precision group')
 np.savez_compressed(out/'alternative-labels.npz',low=low,matched_train=matched['train'],matched_val=matched['val'],matched_test=matched['test'])
 jobs=[];tr=data['train'];va=data['val'];te=data['test']
 for seed in cfg['seeds']:
  jobs.append((f'E2-Dmatched-1024-{seed}',tr[0][:5120],tr[1][:5120]-matched['train'],va[0],va[1]-matched['val'],te[0],matched['test'],seed))
 for n in sorted(set([256,maxgroups])):
  n=min(n,len(rows['train']));N=n*5
  for m,idx in [('B',None),('C',2),('D',3)]:
   for seed in cfg['seeds']:
    jobs.append((f'E5-{m}-low-{n}-{seed}',tr[0][:N],low[:N]-(0 if idx is None else tr[idx][:N]),va[0],va[1]-(0 if idx is None else va[idx]),te[0],np.zeros(len(te[0]))if idx is None else te[idx],seed))
 fits=[];pred={}
 with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
  for fit,pr,params in pool.map(train_predict,jobs):
   fits.append(fit);pred[fit['tag']]=pr;np.savez_compressed(out/(fit['tag']+'.npz'),**params);print(json.dumps({'fit':fit['tag'],'seconds':fit['seconds']}),flush=True)
 np.savez_compressed(out/'predictions.npz',**pred,reference=te[1]);(out/'fits.json').write_text(json.dumps(fits,indent=2)+'\n')
 summary={'elapsed_seconds':time.perf_counter()-start,'E2':{'target_gt_mae':float(target),'candidate_errors':errors,'selected_grid':int(chosen),'candidate_label_seconds':timing,'matched_label_seconds':matched_times,'interpretation':'Global baseline-error matching selected on validation only; exact equality not imposed.'},'E5':{'independent_test_tolerance':1e-7,'independent_test_groups':512,'independent_test_cpu_seconds':sum(r['cpu_seconds']for r in fine),'high_precision_256_cpu_seconds':budget,'low_precision_max_groups':maxgroups,'low_precision_selected_cpu_seconds':float(cost[:maxgroups].sum()),'low_precision_all_generation_cpu_seconds':float(cost.sum()),'interpretation':'Common validation/test use certified labels; compare low-256, low-budget-max and existing high-256 fixed-capacity fits. Report auxiliary label generation cost separately.'}}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'checksums.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n'for f in out.iterdir()if f.is_file()and f.name!='checksums.sha256'));(out/'FROZEN').write_text('Baseline matching and label precision completed.\n')
if __name__=='__main__':main()
