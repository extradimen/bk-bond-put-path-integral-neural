"""Blind paired evaluation of frozen fixed-coefficient put models."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

import argparse
import hashlib
import json
import pathlib
import tarfile
import tempfile
import time

import numpy as np

from learning import MLP


def metrics(prediction, truth):
    e = abs(prediction-truth)
    return dict(mae=float(e.mean()), q95=float(np.quantile(e,.95)),
                q99=float(np.quantile(e,.99)), maximum=float(e.max()),
                exceed_1e_minus4=float(np.mean(e>1e-4)),
                normalized_mae=float(np.mean(e/np.maximum(truth,.001))),
                near_zero_mae=float(e[truth<.001].mean()) if np.any(truth<.001) else None,
                near_zero_fraction=float(np.mean(truth<.001)))


def predict(fit, modeldir, X, cache):
    if fit['model_file'] not in cache:
        with np.load(modeldir/fit['model_file']) as pars:
            net=MLP(X.shape[1],fit['width'],fit['layers'],0)
            for i in range(len(net.W)):
                net.W[i]=pars[f'W{i}'].copy()
                net.b[i]=pars[f'b{i}'].copy()
            cache[fit['model_file']]=(net,pars['mean'].copy(),pars['scale'].copy(),
                                      float(pars['ym']),float(pars['ys']))
    net,mean,scale,ym,ys=cache[fit['model_file']]
    return net.predict((X-mean)/scale)*ys+ym


def group_error(prediction, truth):
    if len(truth)%3:
        raise RuntimeError('group strike count is not three')
    return abs(prediction-truth).reshape(-1,3).mean(axis=1)


def bootstrap_ci(delta, rng, reps):
    draws=np.empty(reps)
    for i in range(0,reps,128):
        size=min(128,reps-i)
        indices=rng.integers(len(delta),size=(size,len(delta)))
        draws[i:i+size]=delta[indices].mean(axis=1)
    return np.quantile(draws,[.025,.975]).tolist()


def signflip_p(delta, rng, reps):
    observed=abs(delta.mean())
    extreme=0
    for i in range(0,reps,128):
        size=min(128,reps-i)
        signs=rng.choice(np.array([-1.,1.]),size=(size,len(delta)))
        extreme+=int(np.sum(abs((signs*delta).mean(axis=1))>=observed))
    return (extreme+1)/(reps+1)


def holm(rows):
    m=len(rows)
    order=sorted(range(m),key=lambda i:rows[i]['p_raw'])
    running=0.
    for rank,i in enumerate(order):
        running=max(running,min(1.,(m-rank)*rows[i]['p_raw']))
        rows[i]['p_holm']=running


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    cfg=json.loads(pathlib.Path(args.config).read_text())
    for key,pathkey in [('data_all_sha256','data_file'),('selected_sha256','selected_file'),
                        ('models_sha256','models_file')]:
        if hashlib.sha256(pathlib.Path(cfg[pathkey]).read_bytes()).hexdigest()!=cfg[key]:
            raise RuntimeError('frozen input checksum mismatch: '+pathkey)
    out=pathlib.Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    selected=json.loads(pathlib.Path(cfg['selected_file']).read_text())
    if len(selected)!=180:
        raise RuntimeError('selected model count differs from frozen plan')
    scores=[]
    predictions={}
    primary={}
    started=time.perf_counter()
    work=pathlib.Path('work')
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fixed-put-eval-',dir=work) as tempdir, \
         np.load(cfg['data_file']) as data, tarfile.open(cfg['models_file'],'r:gz') as archive:
        if any(not m.name.startswith('models/') and m.name!='models' for m in archive.getmembers()):
            raise RuntimeError('model archive has unexpected member path')
        archive.extractall(tempdir,filter='data')
        modeldir=pathlib.Path(tempdir)/'models'
        cache={}
        for split in cfg['splits']:
            for cell in cfg['cells']:
                prefix=split+'_'+cell+'_'
                X=data[prefix+'X']; y=data[prefix+'y']
                A=data[prefix+'A']; Dbase=data[prefix+'Dbase']
                group=data[prefix+'group']
                if len(y)!=3*cfg['groups'][split] or not np.array_equal(group,np.repeat(np.arange(cfg['groups'][split]),3)):
                    raise RuntimeError('group identity or split size mismatch: '+prefix)
                for method,pred in [('A',A),('Dbase',Dbase)]:
                    scores.append(dict(split=split,cell=cell,method=method,
                                       selection='numerical_baseline',metrics=metrics(pred,y)))
                if split=='test':
                    primary[(cell,'A')]=group_error(A,y)
                    primary[(cell,'Dbase')]=group_error(Dbase,y)
                for entry in selected:
                    fit=entry['fit']
                    if fit['cell']!=cell:
                        continue
                    t=time.perf_counter()
                    netvalue=predict(fit,modeldir,X,cache)
                    base=np.zeros_like(y) if fit['method']=='B' else A if fit['method']=='C' else Dbase
                    pred=netvalue+base
                    elapsed=time.perf_counter()-t
                    key=split+'_'+entry['selection']+'_'+fit['tag']
                    predictions[key]=pred
                    scores.append(dict(split=split,cell=cell,method=fit['method'],
                                       selection=entry['selection'],budget=fit['budget'],
                                       seed=fit['seed'],tag=fit['tag'],
                                       neural_prediction_seconds=elapsed,metrics=metrics(pred,y)))
                    if split=='test' and entry['selection']=='tuned' and fit['budget']==4096:
                        primary[(cell,fit['method'],fit['seed'])]=group_error(pred,y)
        for cell in cfg['cells']:
            for method in cfg['methods']:
                primary[(cell,method)]=np.mean([primary[(cell,method,seed)] for seed in cfg['seeds']],axis=0)
        rng=np.random.default_rng(cfg['analysis_seed'])
        contrasts=[]
        for cell in cfg['cells']:
            for left,right in cfg['contrasts']:
                delta=primary[(cell,left)]-primary[(cell,right)]
                contrasts.append(dict(cell=cell,contrast=left+'_minus_'+right,
                                      mean=float(delta.mean()),ci95=bootstrap_ci(delta,rng,cfg['bootstrap_reps']),
                                      p_raw=signflip_p(delta,rng,cfg['signflip_reps']),
                                      groups=len(delta)))
        holm(contrasts)
        np.savez_compressed(out/'predictions.npz',**predictions)
    (out/'scores.json').write_text(json.dumps(scores,indent=2)+'\n')
    (out/'primary-contrasts.json').write_text(json.dumps(contrasts,indent=2)+'\n')
    summary=dict(stage='formal '+('/'.join(cfg['cells']))+' blinded evaluation',elapsed_seconds=time.perf_counter()-started,
                 primary_contrasts=len(contrasts),predictions=len(predictions),
                 scope='primary fixed-coefficient group contrasts; online full baseline cost audited separately')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
