import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[v]='1'
import numpy as np,json,time,pathlib,argparse,hashlib,signal
from concurrent.futures import ProcessPoolExecutor
from numerics import pde,gt_price,grid_for,pde_curve
from learning import MLP
from pilot_learning import arrays,sample,one

def risk_one(row):
 from risk_numerics import reference,baselines
 c=row['parameters'];K=row['strikes'];t=time.perf_counter();cpu=time.process_time()
 ref=reference(c,K);base=baselines(c,K,ref['h']);gtder=base['gt'].T;dder=base['coarse'].T;gt_precision=base['quadrature']
 tail=[]
 from scipy.special import ndtri
 x0=np.log(c['r0']);bb=np.log(c['rbar']);aa=c['a'];tt=c['expiry']
 cutoff=bb+(x0-bb)*np.exp(-aa*tt)+c['sigma']*np.sqrt(-np.expm1(-2*aa*tt)/(2*aa))*ndtri(.05)
 for n in [3201,6401]:
  g=grid_for(c,n);bond=pde_curve(c,c['tenor'],g,1600);h=g[1]-g[0]
  # Cell-average indicator removes arbitrary inclusion of the cutoff grid node.
  indicator=np.clip((cutoff-(g-h/2))/h,0,1)
  payoff=np.maximum(bond[:,None]-np.asarray(K),0)*indicator[:,None]
  tail.append(pde_curve(c,c['expiry'],g,1600,payoff)[n//2])
 errors=ref['errors']
 gp=gt_price(c,K,192,128,both=True);cp=pde(c,201,100,strikes=K)
 refputs=np.array(row['reference']['calls'])-row['reference']['bond']+np.array(K)*row['reference']['discount']
 coarseputs=np.array(cp['calls'])-cp['bond']+np.array(K)*cp['discount']
 der=ref['values'];stationary_fixed=np.column_stack([der[:,0]+c['sigma']**2/(4*c['a'])*der[:,3],der[:,1]-c['sigma']/(2*c['a'])*der[:,3]])
 E=np.exp(-c['a']*c['expiry']);db_da=(c['a']*c['expiry']*(np.log(c['r0'])-np.log(c['rbar']))*E+c['sigma']**2/(4*c['a'])*(1-E*E)-c['sigma']**2*c['expiry']/2*E*E)/(1-E)
 expiry_fixed=np.column_stack([der[:,0]+db_da*der[:,3],der[:,1]-c['sigma']/(2*c['a'])*(1+E)*der[:,3]])
 return {'stationary_mean_fixed_derivatives':stationary_fixed.tolist(),'expiry_mean_fixed_derivatives':expiry_fixed.tolist(),'reference_puts':refputs.tolist(),'gt_puts':gp['puts'],'coarse_puts':coarseputs.tolist(),'gt_parity_gap':(np.array(gp['calls'])-gp['puts']-gp['bond']+np.array(K)*gp['discount']).tolist(),'low_rate_tail_cutoff':float(cutoff),'low_rate_tail_contribution':tail[-1].tolist(),'tail_grid_change':float(np.max(abs(tail[-1]-tail[0]))),'reference_derivatives':ref['values'].tolist(),'gt_derivatives':np.array(gtder).T.tolist(),'coarse_derivatives':np.array(dder).T.tolist(),'gt_derivative_quadrature_change':gt_precision,'discretization_step_errors':errors,'reference_refinement':ref['records'],'baseline_refinement':base['meta'],'gt_step_change':base['gt_step'],'coarse_step_change':base['coarse_step'],'certified':bool(ref['certified'] and base['certified']),'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu}

def train_auxiliary(job):
 # Each fixed-seed fit receives training/validation labels only; no test targets.
 net=MLP(7,64,3,job['seed']);fit=net.fit(job['X'],job['y'],job['V'],job['vy'],.001,job['seed'],derivatives=job.get('derivatives'))
 pred=net.predict(job['Z'])*job['ys']+job['ym'];gradient=net.input_gradient(job['Z'])[:,:4]*job['ys']/job['scale'][:4] if job['need_gradient'] else None
 params={**{f'W{i}':w for i,w in enumerate(net.W)},**{f'b{i}':b for i,b in enumerate(net.b)},'mean':job['mean'],'scale':job['scale'],'ym':job['ym'],'ys':job['ys']}
 return fit,pred,gradient,params

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);args=p.parse_args();cfg=json.load(open(args.config));out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False)
 def alarm(*_):raise TimeoutError('Risk followup budget exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg['max_seconds']);start=time.perf_counter();sets={};risks={};failed=[]
 for split,num in [('train',256),('val',128),('test',128)]:
  if split in cfg.get('input_paths',{}):
   rows=[json.loads(s) for s in pathlib.Path(cfg['input_paths'][split]).read_text().splitlines()][:num]
   (out/(split+'-inputs.jsonl')).write_text(''.join(json.dumps(r)+'\n'for r in rows))
  elif cfg.get('regenerate_frozen_prefix',False):
   seed={'train':20261017,'val':20261018,'test':20261019}[split]
   with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:rows=list(pool.map(one,sample(num,seed)))
   (out/(split+'-inputs.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
   if any(not r['certified'] or r.get('gt_quadrature_error',0)>1e-6 for r in rows):raise RuntimeError('Regenerated prefix failed price certification')
  else:rows=[json.loads(s) for s in pathlib.Path(cfg['data_root'],split+'.jsonl').read_text().splitlines()][:num]
  sets[split]=rows;result=[]
  (out/(split+'-inputs.jsonl')).write_text(''.join(json.dumps(r)+'\n'for r in rows))
  if split in cfg.get('risk_paths',{}):
   result=[json.loads(line)for path in cfg['risk_paths'][split]for line in pathlib.Path(path).read_text().splitlines()]
   source_rows=[json.loads(line)for path in cfg['risk_paths'][split]for line in (pathlib.Path(path).parent/'inputs.jsonl').read_text().splitlines()]
   assert len(result)==num and len(source_rows)==num
   assert all(x['parameters']==y['parameters'] and np.max(abs(np.array(x['strikes'])-y['strikes']))<1e-10 for x,y in zip(rows,source_rows)), 'Shard input/label alignment mismatch'
   (out/(split+'-risk.jsonl')).write_text(''.join(json.dumps(r)+'\n'for r in result))
   for i,r in enumerate(result):
    if not r['certified']:failed.append({'split':split,'group':i,'error':'reused shard did not certify'})
  else:
   with ProcessPoolExecutor(max_workers=cfg['workers']) as pool:
    for i,r in enumerate(pool.map(risk_one,rows)):
     result.append(r)
     with (out/(split+'-risk.jsonl')).open('a') as f:f.write(json.dumps(r)+'\n')
     if not r['certified']:failed.append({'split':split,'group':i,'reference_errors':r['discretization_step_errors'],'gt_errors':r['gt_derivative_quadrature_change'],'gt_step':r['gt_step_change'],'coarse_step':r['coarse_step_change']})
     if i%16==0:print(json.dumps({'split':split,'done':i+1,'elapsed':time.perf_counter()-start}),flush=True)
  risks[split]=result
 if failed:
  (out/'gate-failures.json').write_text(json.dumps(failed,indent=2));return
 data={k:arrays(rows)for k,rows in sets.items()};tr=data['train'];va=data['val'];te=data['test'];mean=tr[0].mean(0);scale=tr[0].std(0)
 X=(tr[0]-mean)/scale;V=(va[0]-mean)/scale;Z=(te[0]-mean)/scale;fits=[];predictions={};gradients={}
 ref={sp:np.concatenate([r['reference_derivatives']for r in rows])for sp,rows in risks.items()}
 basegr={m:{sp:np.concatenate([r[key]for r in rows])for sp,rows in risks.items()}for m,key in [('C','gt_derivatives'),('D','coarse_derivatives')]}
 jobs=[];metadata=[]
 for method,base in [('B',None),('C',2),('D',3)]:
  y=tr[1]-(0 if base is None else tr[base]);vy=va[1]-(0 if base is None else va[base]);ym=y.mean();ys=max(y.std(),1e-8)
  dy=(ref['train']-(0 if method=='B' else basegr[method]['train']))*scale[:4]/ys
  for supervision in ['price','price_derivatives']:
   for seed in cfg['seeds']:
    der=None if supervision=='price' else {'weight':.1,'values':dy,'dims':[0,1,2]}
    jobs.append(dict(X=X,y=(y-ym)/ys,V=V,vy=(vy-ym)/ys,Z=Z,seed=seed,derivatives=der,need_gradient=True,mean=mean,scale=scale,ym=ym,ys=ys));metadata.append((f'{method}-{supervision}-{seed}',method,base))
 with ProcessPoolExecutor(max_workers=cfg['workers'])as pool:
  for (tag,method,base),(fit,pred,dg,params)in zip(metadata,pool.map(train_auxiliary,jobs)):
   pred=pred+(0 if base is None else te[base]);dg=dg+(0 if method=='B'else basegr[method]['test']);predictions[tag]=pred;gradients[tag]=dg
   np.savez_compressed(out/(tag+'.npz'),**params);fit.update(tag=tag,price_mae=float(np.mean(abs(pred-te[1]))),risk_mae=np.mean(abs(dg-ref['test']),axis=0).tolist());fits.append(fit)
   print(json.dumps({'fit':tag,'seconds':fit['seconds']}),flush=True)
 # Independently fit put networks; parity is not imposed as an identity.
 putfits=[];putpred={};jobs=[];metadata=[]
 py={sp:np.concatenate([r['reference_puts']for r in rr])for sp,rr in risks.items()}
 for method,key in [('B',None),('C','gt_puts'),('D','coarse_puts')]:
  pb={sp:(np.zeros(len(py[sp])) if key is None else np.concatenate([r[key]for r in rr]))for sp,rr in risks.items()}
  yy=py['train']-pb['train'];vv=py['val']-pb['val'];ym=yy.mean();ys=max(yy.std(),1e-8)
  for seed in cfg['seeds']:
   jobs.append(dict(X=X,y=(yy-ym)/ys,V=V,vy=(vv-ym)/ys,Z=Z,seed=seed,need_gradient=False,mean=mean,scale=scale,ym=ym,ys=ys));metadata.append((f'{method}-put-price-{seed}',method,seed,pb['test']))
 bond=np.repeat([r['reference']['bond']for r in sets['test']],5);disc=np.repeat([r['reference']['discount']for r in sets['test']],5)
 with ProcessPoolExecutor(max_workers=cfg['workers'])as pool:
  for (tag,method,seed,baseline),(fit,pr,_,params)in zip(metadata,pool.map(train_auxiliary,jobs)):
   pr=pr+baseline;putpred[tag]=pr;gap=predictions[f'{method}-price-{seed}']-pr-bond+te[0][:,6]*disc
   fit.update(tag=tag,put_mae=float(np.mean(abs(pr-py['test']))),parity_mae=float(np.mean(abs(gap))),parity_q99=float(np.quantile(abs(gap),.99)));putfits.append(fit);np.savez_compressed(out/(tag+'.npz'),**params)
   print(json.dumps({'fit':tag,'seconds':fit['seconds']}),flush=True)
 np.savez_compressed(out/'put-predictions.npz',**putpred)
 (out/'put-fits.json').write_text(json.dumps(putfits,indent=2)+'\n')
 np.savez_compressed(out/'risk-predictions.npz',**gradients,reference=ref['test'])
 np.savez_compressed(out/'price-predictions.npz',**predictions,reference=te[1])
 (out/'fits.json').write_text(json.dumps(fits,indent=2)+'\n')
 (out/'summary.json').write_text(json.dumps({'elapsed_seconds':time.perf_counter()-start,'scope':'E3 sensitivities and E4 derivative supervision; fixed model capacity, no additional tuning','derivative_coordinates':['log(a)','sigma','log(r0)','log(rbar)'],'supervised_derivative_coordinates':['log(a)','sigma','log(r0)'],'validation_rule':'price MAE, identical across supervision arms'},indent=2)+'\n')
 (out/'checksums.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n'for f in out.iterdir() if f.is_file() and f.name!='checksums.sha256'));(out/'FROZEN').write_text('Risk experiment complete.\n')
if __name__=='__main__':main()
