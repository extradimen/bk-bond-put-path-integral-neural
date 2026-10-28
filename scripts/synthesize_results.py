"""Governed, frozen analysis of completed E1--E5, no model fitting."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json,pathlib,hashlib,time
import numpy as np
from formal_main import metrics

def readrows(path):return [json.loads(s) for s in path.read_text().splitlines()]
def agg(v):
 a=np.asarray(v);return dict(mean=float(a.mean()),min=float(a.min()),max=float(a.max()),seed_values=a.tolist())
def paired(a,b,seed=20261025):
 # a,b: seeds x groups x contracts; seed-average paired group effect.
 d=np.mean(abs(a)-abs(b),axis=(0,2));r=np.random.default_rng(seed)
 bs=[float(r.choice(d,len(d),replace=True).mean()) for _ in range(2000)]
 return dict(mean=float(d.mean()),ci95=np.quantile(bs,[.025,.975]).tolist(),groups=len(d),note='Group bootstrap of seed-average absolute-error differences; fixed five seeds, pointwise interval.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
 # Resolve analysis inputs within the preserved snapshot containing this config.
 snapshot_root=pathlib.Path(a.config).resolve().parents[1]
 for key in ['main_root','risk_root','baseline_root','diagnostics_root','runtime_crosscheck']:
  cfg[key]=str(snapshot_root/cfg[key])
 cfg['duplicate_input_paths']=[str(snapshot_root/p)for p in cfg.get('duplicate_input_paths',[])]
 root=pathlib.Path(cfg['main_root']);rr=pathlib.Path(cfg['risk_root']);br=pathlib.Path(cfg['baseline_root']);data=np.load(root/'data-all.npz');pred=np.load(root/'predictions.npz');selected=json.load(open(root/'selected.json'));scores=json.load(open(root/'scores.json'));fits=readrows(root/'fits.jsonl');seeds=[11,23,37,53,71]
 summary={'scope':'Classical Black-Karasinski zero-coupon bond calls; simulated parameter space, no market calibration','main':[],'paired':[],'risk':{},'E2':{},'E5':{},'economics':{},'cost':{},'reconciliation':{}}
 def mainpred(method,budget,seed,selection='fixed_capacity',split='test'):
  fit=next(s['fit'] for s in selected if s['selection']==selection and s['fit']['method']==method and s['fit']['budget']==budget and s['fit']['seed']==seed)
  return pred[split+'-'+selection+'-'+fit['tag']]
 for split in ['test','ood_vol','ood_expiry']:
  y=data[split][:,7]
  for method,idx in [('A',8),('Dbase',9)]:summary['main'].append(dict(split=split,method=method,selection='none',budget=0,metrics=metrics(data[split][:,idx],y)))
  for selection in ['fixed_capacity','tuned']:
   for budget in [256,1024,4096]:
    for m in ['B','C','D']:
     mm=[metrics(mainpred(m,budget,s,selection,split),y) for s in seeds]
     summary['main'].append(dict(split=split,method=m,selection=selection,budget=budget,metrics={k:agg([v[k] for v in mm]) for k in mm[0]}))
    err={m:np.array([(mainpred(m,budget,s,selection,split)-y).reshape(-1,5) for s in seeds]) for m in ['B','C','D']}
    err['A']=np.broadcast_to((data[split][:,8]-y).reshape(-1,5),err['B'].shape);err['Dbase']=np.broadcast_to((data[split][:,9]-y).reshape(-1,5),err['B'].shape)
    for l,r in [('B','C'),('B','D'),('A','C'),('A','B'),('Dbase','D'),('C','D')]:summary['paired'].append(dict(split=split,selection=selection,budget=budget,contrast=l+'-'+r,**paired(err[l],err[r])))
 # Summarize already-computed held-out diagnostics without changing their definitions.
 diag=json.load(open(pathlib.Path(cfg['diagnostics_root'])/'diagnostics.json'));summary['diagnostics']={'financial':[],'geometry':[]}
 for m in ['A','B','C','D','Dbase']:
  ff=[r for r in diag['financial_checks']if r['tag']==m or r['tag'].startswith(m+'-4096-')]
  summary['diagnostics']['financial'].append({'method':m,**{k:agg([r[k]for r in ff])for k in ['negative_fraction','bond_bound_fraction','strike_increasing_fraction','convexity_violation_fraction']}})
 for m in ['C','D']:
  gg=[r for r in diag['geometry']if r['tag'].startswith(m+'-4096-')]
  summary['diagnostics']['geometry'].append({'method':m,'r2_with_shape':agg([r['test_r2_with_residual_shape']for r in gg]),'r2_without_shape':agg([r['test_r2_without_shape']for r in gg]),'r2_difference':agg([r['test_r2_with_residual_shape']-r['test_r2_without_shape']for r in gg])})
 # Input reproduction must match even though timing naturally differs.
 for split,n in [('train',256),('val',128),('test',128)]:
  one=readrows(root/(split+'.jsonl'))[:n];two=readrows(rr/(split+'-inputs.jsonl'))
  assert len(one)==len(two)==n
  differences={}
  for field in ['parameters','strikes','reference','gt','coarse']:
   def flat(v):
    if isinstance(v,dict):return [x for k in sorted(v) for x in flat(v[k])]
    if isinstance(v,list):return [x for q in v for x in flat(q)]
    return [float(v)]
   differences[field]=max(float(np.max(abs(np.asarray(flat(x[field]))-flat(z[field])))) for x,z in zip(one,two))
  summary['reconciliation'][split]=differences
  if max(differences.values())>1e-10:raise RuntimeError('Main/risk inputs disagree beyond cross-platform rounding allowance')
 risks={sp:readrows(rr/(sp+'-risk.jsonl'))for sp in ['train','val','test']};rp=np.load(rr/'risk-predictions.npz');pp=np.load(rr/'price-predictions.npz');rfit=json.load(open(rr/'fits.json'));summary['risk']['fits']=rfit;summary['risk']['put_fits']=json.load(open(rr/'put-fits.json'));summary['risk']['contrasts']=[]
 for m in ['B','C','D']:
  pr=np.array([(pp[f'{m}-price-{s}']-pp['reference']).reshape(-1,5)for s in seeds]);dr=np.array([(pp[f'{m}-price_derivatives-{s}']-pp['reference']).reshape(-1,5)for s in seeds])
  item={'method':m,'price_supervision_minus_derivative_supervision_price_error':paired(pr,dr),'derivatives':[]}
  for j in range(4):
   pr=np.array([(rp[f'{m}-price-{s}'][:,j]-rp['reference'][:,j]).reshape(-1,5)for s in seeds]);dr=np.array([(rp[f'{m}-price_derivatives-{s}'][:,j]-rp['reference'][:,j]).reshape(-1,5)for s in seeds]);item['derivatives'].append(paired(pr,dr))
  summary['risk']['contrasts'].append(item)
 summary['risk']['baselines']=[]
 baseline_rows=readrows(rr/'test-inputs.jsonl');baseline_truth=np.concatenate([r['reference']['calls']for r in baseline_rows])
 for label,pricekey,riskkey in [('A','gt','gt_derivatives'),('Dbase','coarse','coarse_derivatives')]:
  price_values=np.concatenate([r[pricekey]for r in baseline_rows]);risk_values=np.concatenate([r[riskkey]for r in risks['test']])
  summary['risk']['baselines'].append({'method':label,'price_mae':float(np.mean(abs(price_values-baseline_truth))),'risk_mae':np.mean(abs(risk_values-rp['reference']),axis=0).tolist()})
 summary['risk']['aggregated']=[]
 for method in ['B','C','D']:
  for supervision in ['price','price_derivatives']:
   ff=[f for f in rfit if f['tag'].startswith(method+'-'+supervision+'-') and (supervision!='price' or 'derivatives' not in f['tag'])]
   summary['risk']['aggregated'].append(dict(method=method,supervision=supervision,price_mae=agg([f['price_mae']for f in ff]),risk_mae=[agg([f['risk_mae'][j]for f in ff])for j in range(4)]))
 rows=readrows(rr/'test-inputs.jsonl');raw=np.concatenate([r['reference_derivatives']for r in risks['test']]);fixed=np.concatenate([r['stationary_mean_fixed_derivatives']for r in risks['test']]);fixedt=np.concatenate([r['expiry_mean_fixed_derivatives']for r in risks['test']]);price=np.concatenate([r['reference']['calls']for r in rows]);tail=np.concatenate([r['low_rate_tail_contribution']for r in risks['test']]);valid=price>1e-6
 ratio=tail[valid]/price[valid];ae=abs(np.concatenate([r['gt']for r in rows])-price)
 def corr(a,b):return None if min(np.std(a),np.std(b))<1e-15 else float(np.corrcoef(a,b)[0,1])
 summary['economics']={'price_threshold_for_tail_ratio':1e-6,'tail_ratio_contract_count':int(valid.sum()),'tail_ratio_quantiles':np.quantile(ratio,[0,.25,.5,.75,1]).tolist(),'tail_grid_change_max':max(r['tail_grid_change']for r in risks['test']),'tail_ratio_vs_gt_error_correlation':corr(ratio,ae[valid]),'raw_sensitivity_mean_abs':np.mean(abs(raw),0).tolist(),'fixed_stationary_mean_sensitivity_mean_abs':np.mean(abs(fixed),0).tolist(),'fixed_expiry_mean_sensitivity_mean_abs':np.mean(abs(fixedt),0).tolist(),'stationary_control_sign_change_fraction':np.mean(np.sign(raw[:,:2])!=np.sign(fixed),0).tolist(),'expiry_control_sign_change_fraction':np.mean(np.sign(raw[:,:2])!=np.sign(fixedt),0).tolist(),'gt_independent_put_parity_mae':float(np.mean(abs(np.concatenate([r['gt_parity_gap']for r in risks['test']])))),'gt_independent_put_parity_max':float(np.max(abs(np.concatenate([r['gt_parity_gap']for r in risks['test']])))),'limitation':'Risk-neutral synthetic associations, not empirical causation; mean controls do not fix full initial yield curve.'}
 # Economic-coordinate diagnostics use the already planned fourth derivative.
 aa=np.repeat([r['parameters']['a']for r in rows],5);ss=np.repeat([r['parameters']['sigma']for r in rows],5);tt=np.repeat([r['parameters']['expiry']for r in rows],5);x0=np.repeat([np.log(r['parameters']['r0'])for r in rows],5);bb=np.repeat([np.log(r['parameters']['rbar'])for r in rows],5);EE=np.exp(-aa*tt)
 db_da=(aa*tt*(x0-bb)*EE+ss**2/(4*aa)*(1-EE*EE)-ss**2*tt/2*EE*EE)/(1-EE)
 def mean_coordinates(g):return np.column_stack([g[:,0]+ss**2/(4*aa)*g[:,3],g[:,1]-ss/(2*aa)*g[:,3]]),np.column_stack([g[:,0]+db_da*g[:,3],g[:,1]-ss/(2*aa)*(1+EE)*g[:,3]])
 summary['risk']['mean_controlled']=[]
 for method,supervision in [('A','none'),('Dbase','none')]+[(m,sup)for m in ['B','C','D']for sup in ['price','price_derivatives']]:
  if method in ['A','Dbase']:
   key='gt_derivatives'if method=='A'else 'coarse_derivatives';gs=[np.concatenate([r[key]for r in risks['test']])]
  else:gs=[rp[f'{method}-{supervision}-{seed}']for seed in seeds]
  transformed=[mean_coordinates(g)for g in gs]
  summary['risk']['mean_controlled'].append({'method':method,'supervision':supervision,'seed_count':len(gs),'stationary_mae':[agg([np.mean(abs(g[0][:,j]-fixed[:,j]))for g in transformed])for j in range(2)],'expiry_mae':[agg([np.mean(abs(g[1][:,j]-fixedt[:,j]))for g in transformed])for j in range(2)]})
 summary['risk']['mean_controlled_note']='Exploratory chain-rule transformation of the four stored derivatives. Coefficients can amplify original numerical derivative uncertainty; no independent absolute error bound in the transformed coordinates is claimed.'
 bp=np.load(br/'predictions.npz');bs=json.load(open(br/'summary.json'));y=data['test'][:,7];summary['E2']['design']=bs['E2'];summary['E2']['matched_mae']=agg([metrics(bp[f'E2-Dmatched-1024-{s}'],y)['mae']for s in seeds]);summary['E2']['contrasts']=[]
 er=np.array([(bp[f'E2-Dmatched-1024-{s}']-y).reshape(-1,5)for s in seeds])
 for m in ['B','C','D']:
  other=np.array([(mainpred(m,1024,s)-y).reshape(-1,5)for s in seeds]);summary['E2']['contrasts'].append(dict(contrast=m+'-Dmatched',**paired(other,er)))
 fy=np.load(br/'fine-test-reference.npz')['reference'];N=len(fy);summary['E5']['design']=bs['E5'];summary['E5']['reference_change']=metrics(y[:N],fy);summary['E5']['metrics']=[];summary['E5']['contrasts']=[]
 for m in ['B','C','D']:
  high=np.array([(mainpred(m,256,s)[:N]-fy).reshape(-1,5) for s in seeds]);summary['E5']['metrics'].append(dict(method=m,label='high',groups=256,mae=agg([np.mean(abs(e))for e in high])))
  for n in sorted(set([256,bs['E5']['low_precision_max_groups']])):
   low=np.array([(bp[f'E5-{m}-low-{n}-{s}'][:N]-fy).reshape(-1,5)for s in seeds]);summary['E5']['metrics'].append(dict(method=m,label='low',groups=n,mae=agg([np.mean(abs(e))for e in low])));summary['E5']['contrasts'].append(dict(method=m,contrast=f'low{n}-high256',**paired(low,high)))
 rawrows={sp:readrows(root/(sp+'.jsonl'))for sp in ['train','val','test','ood_vol','ood_expiry']};cost={sp:{key:sum(r[key]for r in rows)for key in ['reference_cpu_seconds','gt_cpu_seconds','coarse_cpu_seconds']}for sp,rows in rawrows.items()};summary['cost']['label_cpu_seconds']=cost
 summary['economics']['risk_neutral_rate_mean_ranges']={}
 for split,rs in rawrows.items():
  means=[];expirymeans=[]
  for row in rs:
   p=row['parameters'];E=np.exp(-p['a']*p['expiry']);b=np.log(p['rbar']);v=p['sigma']**2/(4*p['a'])
   means.append(np.exp(b+v));expirymeans.append(np.exp(b+(np.log(p['r0'])-b)*E+v*(1-E*E)))
  summary['economics']['risk_neutral_rate_mean_ranges'][split]={'stationary_median_p95_max':np.quantile(means,[.5,.95,1]).tolist(),'expiry_median_p95_max':np.quantile(expirymeans,[.5,.95,1]).tolist(),'note':'Descriptive model-implied risk-neutral means under synthetic parameters, not observed market rates.'}
 bench=json.load(open(root/'online-benchmark.json'));summary['cost']['online_benchmark']=bench;summary['cost']['training_cpu_seconds']=[];summary['cost']['break_even_vs_A']=[]
 for m in ['B','C','D']:
  for budget in [256,1024,4096]:
   fs=[f for f in fits if f['method']==m and f['budget']==budget];summary['cost']['training_cpu_seconds'].append(dict(method=m,budget=budget,all_candidates=sum(f['training']['cpu_seconds']for f in fs),candidate_count=len(fs),epoch_ceiling_hits=sum(f['training']['epochs']==500 for f in fs)))
  fs=[f for f in fits if f['method']==m and f['budget']==4096];label=sum(r['reference_cpu_seconds']+(r['gt_cpu_seconds']if m=='C'else r['coarse_cpu_seconds']if m=='D'else 0)for sp in ['train','val']for r in rawrows[sp]);offline=label+sum(f['training']['cpu_seconds']for f in fs)
  for mode in ['single','surface']:
   base=bench['samples'][mode]['A']['median'];hy=bench['samples'][mode]['tuned-'+m]['median'];saving=base-hy
   summary['cost']['break_even_vs_A'].append(dict(method=m,mode=mode,offline_cpu_seconds_with_five_seed_tuning=offline,per_request_saving_seconds=saving,queries=None if saving<=0 else float(offline/saving),note='Compute-time amortization estimate, conditional on acceptable pricing accuracy; validation labels and all five-seed candidates counted, model deployment/loading omitted. CPU work divided by serial request wall time, not parallel wall-clock payback.'))
 summary['E5']['budget_scope']='Conditional label-work ceiling on the already fixed contract pool. Strikes were constructed from certified forward bonds in the main study; common input-contract construction and validation/test reference work are not charged to this E5 label ceiling. This is not an end-to-end equal-total-cost comparison.'
 summary['E5']['low_budget_used_fraction']=bs['E5']['low_precision_selected_cpu_seconds']/bs['E5']['high_precision_256_cpu_seconds']
 summary['cost']['risk_duplicate_input_generation_cpu_seconds']=sum(r['reference_cpu_seconds']+r['gt_cpu_seconds']+r['coarse_cpu_seconds']for path in cfg.get('duplicate_input_paths',[])for r in readrows(pathlib.Path(path)))
 summary['cost']['risk_derivative_cpu_seconds_by_split']={sp:sum(r['cpu_seconds']for r in rs)for sp,rs in risks.items()}
 summary['cost']['risk_derivative_generation_cpu_seconds']=sum(r['cpu_seconds']for rs in risks.values()for r in rs)
 summary['cost']['interrupted_run_accounting']={'stages':['risk-followup-v2','baseline-precision-v1'],'note':'Failed derivative and strict-convergence branches retained. Recorded wall time and completed partial records are available; CPU consumed by interrupted in-flight tasks was not completely recorded and is not invented. Successful-method amortization excludes research debugging failures. Reused certified fine references and completed failed-reference work subsequently repaired are included in the fine-reference accounting; interrupted unfinished work is not.'}
 summary['cost']['risk_reference_runtime_crosscheck']=json.load(open(cfg['runtime_crosscheck']))
 summary['cost']['risk_reference_runtime_note']='Training/test risk labels on registered campus CPUs, validation labels on Mac after three fixed-case cross-runtime checks. Risk CPU seconds are descriptive aggregate work, not hardware-equivalent time or a controlled speed comparison.'
 summary['cost']['risk_derivative_generation_wall_seconds_sum']=sum(r['seconds']for rs in risks.values()for r in rs);summary['cost']['risk_training_cpu_seconds']=sum(r['cpu_seconds']for r in rfit+summary['risk']['put_fits']);summary['elapsed_seconds']=time.perf_counter()-start
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'summary.json').read_bytes()).hexdigest()+'  summary.json\n');(out/'FROZEN').write_text('Synthesis complete; interpretation must preserve scope and uncertainty.\n')
if __name__=='__main__':main()
