"""Validation-fitted one-split selector among five fixed-put pricing methods."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse,hashlib,json,pathlib,tarfile,tempfile
import numpy as np
from fixed_put_evaluate import predict


def methods(split,cell,data,selected,modeldir,seeds,cache):
    pre=f'{split}_{cell}_';X=data[pre+'X'];out={'A':data[pre+'A'],'Dbase':data[pre+'Dbase']}
    for method in ('B','C','D'):
        preds=[]
        for seed in seeds:
            match=[entry['fit'] for entry in selected if entry['selection']=='tuned' and
                   entry['fit']['cell']==cell and entry['fit']['method']==method and
                   entry['fit']['budget']==4096 and entry['fit']['seed']==seed]
            if len(match)!=1:raise RuntimeError('selected network not unique')
            p=predict(match[0],modeldir,X,cache)
            p+=0 if method=='B' else out['A'] if method=='C' else out['Dbase']
            preds.append(p)
        out[method]=np.mean(preds,axis=0)
    return X,data[pre+'y'],out


def group_features(X):
    if len(X)%3:raise RuntimeError('strike grouping')
    return X.reshape(-1,3,X.shape[1]).mean(axis=1)


def group_errors(y,preds,method_names):
    return np.column_stack([abs(preds[m]-y).reshape(-1,3).mean(axis=1) for m in method_names])


def select_stump(features,loss,candidates):
    base=loss.mean(axis=0);default=int(np.argmin(base));best=(float(base[default]),None,None,None,default,default)
    for j in range(features.shape[1]):
        for q in candidates:
            threshold=float(np.quantile(features[:,j],q));mask=features[:,j]<=threshold
            if mask.sum()<30 or (~mask).sum()<30:continue
            left=int(np.argmin(loss[mask].mean(axis=0)));right=int(np.argmin(loss[~mask].mean(axis=0)))
            score=float((loss[mask,left].sum()+loss[~mask,right].sum())/len(loss))
            if score<best[0]-1e-15:best=(score,j,threshold,q,left,right)
    return best,default


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();cfg=json.loads(pathlib.Path(a.config).read_text())
    for path_key,hash_key in cfg['inputs']:
        if hashlib.sha256(pathlib.Path(cfg[path_key]).read_bytes()).hexdigest()!=cfg[hash_key]:
            raise RuntimeError('checksum mismatch '+path_key)
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    selected=json.loads(pathlib.Path(cfg['selected_file']).read_text())
    costs=json.loads(pathlib.Path(cfg['cost_file']).read_text())
    names=cfg['methods'];records=[]
    pathlib.Path(cfg['scratch_dir']).mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='e6-',dir=cfg['scratch_dir']) as scratch,\
         tarfile.open(cfg['models_file'],'r:gz') as archive, np.load(cfg['data_file']) as data:
        if any(not m.name.startswith('models/') and m.name!='models' for m in archive.getmembers()):
            raise RuntimeError('unexpected model archive member')
        archive.extractall(scratch,filter='data');modeldir=pathlib.Path(scratch)/'models';cache={}
        for cell in cfg['cells']:
            vx,vy,vp=methods('val',cell,data,selected,modeldir,cfg['seeds'],cache)
            tx,ty,tp=methods('test',cell,data,selected,modeldir,cfg['seeds'],cache)
            vf,tf=group_features(vx),group_features(tx)
            ve,te=group_errors(vy,vp,names),group_errors(ty,tp,names)
            if len(vf)!=cfg['val_groups'] or len(tf)!=cfg['test_groups']:
                raise RuntimeError('group count mismatch')
            raw={m:costs[cell][m]['median_seconds'] for m in names}
            five_seed_seconds={'A':raw['A'],'Dbase':raw['Dbase'],
                'B':5*raw['B'],'C':raw['A']+5*max(0,raw['C']-raw['A']),
                'D':raw['Dbase']+5*max(0,raw['D']-raw['Dbase'])}
            seconds=np.array([five_seed_seconds[m] for m in names])
            for lam in cfg['price_error_per_second']:
                loss=ve+lam*seconds
                best,default=select_stump(vf,loss,cfg['candidate_quantiles'])
                _,feature,threshold,quantile,left,right=best
                chosen=np.full(len(tf),default,dtype=int) if feature is None else np.where(tf[:,feature]<=threshold,left,right)
                test_errors=te[np.arange(len(te)),chosen]
                records.append(dict(cell=cell,lambda_price_error_per_second=lam,
                    rule=dict(feature=feature,threshold=threshold,quantile=quantile,
                              left=names[left],right=names[right],validation_objective=best[0]),
                    default=names[default],test_mae=float(test_errors.mean()),
                    test_median_seconds_per_group=float(np.median(seconds[chosen])),
                    test_mean_seconds_per_group=float(seconds[chosen].mean()),
                    chosen_counts={m:int(np.sum(chosen==i)) for i,m in enumerate(names)},
                    constant_test_mae=float(te[:,default].mean()),
                    constant_test_mean_seconds_per_group=float(seconds[default]),
                    method_test_mae={m:float(te[:,i].mean()) for i,m in enumerate(names)}))
    summary=dict(stage=cfg.get('study_label','fixed-put E6 conditional adaptive selection'),records=records,
        scope='Exploratory after primary test results; validation-fitted one-split rule, test evaluated once within this stage. Network candidate uses five-seed mean price; online timing is an implementation-level proxy from separate timing stage, with neural increment multiplied by five.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(stage=summary['stage'],records=len(records))),flush=True)


if __name__=='__main__':main()
