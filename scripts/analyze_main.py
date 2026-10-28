import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import pathlib,json,numpy as np,argparse,time,hashlib,tarfile
from formal_main import load_predict,metrics

def ridge_predict(X,y,Z):
 mean=X.mean(0);scale=np.maximum(X.std(0),1e-12);x=np.column_stack([np.ones(len(X)),(X-mean)/scale]);z=np.column_stack([np.ones(len(Z)),(Z-mean)/scale]);pen=np.eye(x.shape[1])*1e-6;pen[0,0]=0;coef=np.linalg.solve(x.T@x+pen,x.T@y);return z@coef,coef

def r2(y,p):return float(1-np.sum((y-p)**2)/max(np.sum((y-y.mean())**2),1e-20))

def geometry(data,method):
 x=data[:,:7].reshape(-1,5,7);y=data[:,7].reshape(-1,5);base=data[:,8 if method=='C' else 9].reshape(-1,5);res=y-base;K=x[:,:,6]
 grad=np.diff(res)/np.diff(K);curv=np.diff(grad)/((K[:,2:]-K[:,:-2])/2)
 return np.column_stack([np.log(np.maximum(np.mean(abs(res),axis=1),1e-12)),np.log(np.maximum(np.mean(abs(grad),axis=1),1e-12)),np.log(np.maximum(np.mean(abs(curv),axis=1),1e-12)),y.mean(1),x[:,0,0],x[:,0,1],x[:,0,4],x[:,0,5]])

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);root=pathlib.Path(cfg['main_root']);data=np.load(root/'data-all.npz');pred=np.load(root/'predictions.npz');sel=json.load(open(root/'selected.json'));test=data['test'];y=test[:,7];rows=[json.loads(l) for l in (root/'test.jsonl').read_text().splitlines()];bounds=np.repeat([r['reference']['bond']for r in rows],5)
 with tarfile.open(root/'models.tar.gz') as archive:archive.extractall(out/'expanded',filter='data')
 summary={'geometry':[],'financial_checks':[],'risk_regions':[]}
 for it in sel:
  if it['selection']!='tuned':continue
  fit=it['fit'];key='test-tuned-'+fit['tag'];pr=pred[key];pg=pr.reshape(-1,5);K=test[:,6].reshape(-1,5);slope=np.diff(pg)/np.diff(K)
  summary['financial_checks'].append({'tag':fit['tag'],'negative_fraction':float(np.mean(pr < -1e-6)),'bond_bound_fraction':float(np.mean(pr>bounds+1e-6)),'strike_increasing_fraction':float(np.mean(np.diff(pg)>1e-6)),'convexity_violation_fraction':float(np.mean(np.diff(slope)<-1e-6)),'note':'This main-price arm has no put model; independently trained puts and parity are assessed separately in E4.'})
  # All region cuts estimated on training parameters, before test performance is used.
  train=data['train'][:,:7].reshape(-1,5,7)[:,0,:];tx=test[:,:7].reshape(-1,5,7)[:,0,:];err=np.mean(abs(pg-y.reshape(-1,5)),axis=1)
  for dim,name in [(0,'log_a'),(1,'sigma'),(2,'log_r0'),(4,'expiry'),(5,'tenor')]:
   cuts=np.quantile(train[:,dim],[.25,.5,.75]);bins=np.digitize(tx[:,dim],cuts)
   for j in range(4):summary['risk_regions'].append({'tag':fit['tag'],'dimension':name,'quartile':j+1,'cuts':cuts.tolist(),'count':int(np.sum(bins==j)),'mae':float(np.mean(err[bins==j]))})
  if fit['budget']==4096 and fit['method'] in ['C','D']:
   method=fit['method'];v=data['val'];base=v[:,8 if method=='C' else 9];pv=load_predict(fit,out/'expanded/models',v[:,:7])+base
   outcome=np.log(np.maximum(np.mean(abs(pv-v[:,7]).reshape(-1,5),axis=1),1e-12));truth=np.log(np.maximum(err,1e-12));X=geometry(v,method);Z=geometry(test,method)
   full,coef=ridge_predict(X,outcome,Z);basecols=[0,3,4,5,6,7];simple,_=ridge_predict(X[:,basecols],outcome,Z[:,basecols]);summary['geometry'].append({'tag':fit['tag'],'test_r2_with_residual_shape':r2(truth,full),'test_r2_without_shape':r2(truth,simple),'standardized_coefficients':coef.tolist(),'interpretation':'Exploratory held-out prediction; features require reference residuals and are not deployable pre-pricing features.'})
 # Apply identical diagnostics to both numerical baselines.
 for label,index in [('A',8),('Dbase',9)]:
  A=test[:,index];Ag=A.reshape(-1,5);K=test[:,6].reshape(-1,5)
  summary['financial_checks'].append({'tag':label,'negative_fraction':float(np.mean(A < -1e-6)),'bond_bound_fraction':float(np.mean(A>bounds+1e-6)),'strike_increasing_fraction':float(np.mean(np.diff(Ag)>1e-6)),'convexity_violation_fraction':float(np.mean(np.diff(np.diff(Ag)/np.diff(K)) < -1e-6))})
 (out/'diagnostics.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'diagnostics.json').read_bytes()).hexdigest()+'  diagnostics.json\n');(out/'FROZEN').write_text('Exploratory diagnostic analysis.\n')
if __name__=='__main__':main()
