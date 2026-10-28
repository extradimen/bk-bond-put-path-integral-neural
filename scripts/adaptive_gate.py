"""Conditional E6, rule fixed before evaluating the policy on test/OOD."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json,pathlib,tarfile,hashlib,itertools
import numpy as np
from formal_main import load_predict,metrics,paired_ci

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);root=pathlib.Path(cfg['main_root']);data=np.load(root/'data-all.npz');pred=np.load(root/'predictions.npz');selected=json.load(open(root/'selected.json'));seeds=[11,23,37,53,71];methods=['B','C','D']
 with tarfile.open(root/'models.tar.gz')as tar:tar.extractall(out/'expanded',filter='data')
 chosen={(m,s):next(it['fit']for it in selected if it['selection']=='tuned'and it['fit']['method']==m and it['fit']['seed']==s and it['fit']['budget']==4096)for m,s in itertools.product(methods,seeds)}
 val=data['val'];V=val[:,:7].reshape(-1,5,7)[:,0,:];truth=val[:,7];vp={m:np.array([load_predict(chosen[m,s],out/'expanded/models',val[:,:7])+(0 if m=='B'else val[:,8 if m=='C'else 9])for s in seeds])for m in methods};err={m:abs(pr-truth).reshape(5,-1,5).mean(2)for m,pr in vp.items()}
 # Validation first half builds one stump; second half is a disjoint gate.
 cuts=np.quantile(data['train'][:,:7].reshape(-1,5,7)[:,0,:6],[.25,.5,.75],axis=0);half=len(V)//2;options=[]
 for dim,j,l,r in itertools.product(range(6),range(3),methods,methods):
  if l==r:continue
  cut=cuts[j,dim];mask=V[:,dim]<=cut;errors=np.where(mask[None,:],err[l],err[r]);score=float(errors[:,:half].mean());options.append((score,dim,float(cut),l,r))
 best=min(options);score,dim,cut,l,r=best;mask=V[:,dim]<=cut;policyerr=np.where(mask[None,:],err[l],err[r]);constant=min(methods,key=lambda m:float(err[m][:,:half].mean()));gate=[]
 for i,s in enumerate(seeds):
  ci=paired_ci(err[constant][i,half:,None],policyerr[i,half:,None]);ratio=float(policyerr[i,half:].mean()/max(err[constant][i,half:].mean(),1e-15));gate.append(dict(seed=s,ratio=ratio,**ci))
 # The left and right branches must each have >=64 held-out validation groups.
 support=[int(mask[half:].sum()),int((~mask[half:]).sum())];enabled=min(support)>=64 and all(g['ratio']<=.9 and g['ci95'][0]>0 for g in gate)
 result={'status':'enabled'if enabled else 'not_enabled','rule':{'dimension':int(dim),'cut':cut,'left':l,'right':r,'constant_selected_on_first_validation_half':constant},'gate':gate,'heldout_branch_support':support,'requirements':'Each branch >=64 groups; >=10% MAE improvement and positive pointwise paired 95% lower bound for all five seeds on held-out validation half.','scope':'Exploratory extension, not independently preregistered confirmatory discovery. No reference prices used as prediction-time gate features.','evaluations':[]}
 if enabled:
  for split in ['test','ood_vol','ood_expiry']:
   test=data[split];mask=np.repeat(test[:,:7].reshape(-1,5,7)[:,0,dim]<=cut,5)
   for s in seeds:
    key=lambda m:split+'-tuned-'+chosen[m,s]['tag'];q=np.where(mask,pred[key(l)],pred[key(r)]);c=pred[key(constant)];result['evaluations'].append(dict(split=split,seed=s,policy=metrics(q,test[:,7]),constant=metrics(c,test[:,7]),contrast=paired_ci((c-test[:,7]).reshape(-1,5),(q-test[:,7]).reshape(-1,5)),left_fraction=float(mask.mean())))
  np.savez_compressed(out/'validation-policy.npz',policy_error=policyerr,constant_error=err[constant])
 (out/'gate.json').write_text(json.dumps(result,indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'gate.json').read_bytes()).hexdigest()+'  gate.json\n');(out/'FROZEN').write_text('Conditional gate assessed; not_enabled is a completed negative gate, not a missing run.\n')
if __name__=='__main__':main()
