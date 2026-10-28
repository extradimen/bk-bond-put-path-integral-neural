"""Exploratory comparison of method errors to PDE refinement indicators."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse, hashlib, json, pathlib
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();cfg=json.loads(pathlib.Path(a.config).read_text())
    for path_key,hash_key in cfg['inputs']:
        path=pathlib.Path(cfg[path_key])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=cfg[hash_key]:
            raise RuntimeError('checksum mismatch '+path_key)
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    selected=json.loads(pathlib.Path(cfg['selected_file']).read_text())
    ledger=[json.loads(s) for s in pathlib.Path(cfg['ledger_file']).open()]
    if len(ledger)!=cfg['groups'] or any(r['group']!=i for i,r in enumerate(ledger)):
        raise RuntimeError('ledger group identity mismatch')
    results=[]
    with np.load(cfg['data_file']) as data,np.load(cfg['predictions_file']) as predictions:
        for cell in cfg.get('cells',('FE','FB')):
            prefix='test_'+cell+'_';y=data[prefix+'y'];ids=data[prefix+'group']
            if not np.array_equal(ids,np.repeat(np.arange(cfg['groups']),3)):
                raise RuntimeError('packed groups misaligned')
            if cfg.get('ledger_layout')=='nested_cells':
                indicator=np.array([r['cells'][cell]['reference_indicator']
                                    for group in ledger for r in group['rows']])
            else:
                key='european_reference' if cell=='FE' else 'reference'
                indicator=np.array([r[key]['error_indicator'] for group in ledger for r in group['rows']])
            if len(indicator)!=len(y):raise RuntimeError('indicator length mismatch')
            model_errors={}
            for method in ('A','Dbase'):
                model_errors[method]=abs(data[prefix+method]-y).reshape(-1,3).mean(axis=1)
            for method in ('B','C','D'):
                per_seed=[]
                for seed in cfg['seeds']:
                    matches=[e for e in selected if e['selection']=='tuned' and
                             e['fit']['cell']==cell and e['fit']['method']==method and
                             e['fit']['budget']==4096 and e['fit']['seed']==seed]
                    if len(matches)!=1:raise RuntimeError('selected model not unique')
                    pred=predictions['test_tuned_'+matches[0]['fit']['tag']]
                    per_seed.append(abs(pred-y).reshape(-1,3).mean(axis=1))
                model_errors[method]=np.mean(per_seed,axis=0)
            gi=indicator.reshape(-1,3).mean(axis=1)
            cell_result=dict(cell=cell,groups=len(gi),indicator_mean=float(gi.mean()),
                             indicator_q50=float(np.quantile(gi,.5)),
                             indicator_q95=float(np.quantile(gi,.95)),
                             indicator_max=float(gi.max()),methods={},contrasts=[])
            for method,e in model_errors.items():
                cell_result['methods'][method]=dict(mae=float(e.mean()),
                    fraction_group_error_below_indicator=float(np.mean(e<=gi)),
                    mean_error_to_indicator_ratio=float(e.mean()/max(gi.mean(),1e-15)))
            for left,right in cfg['contrasts']:
                delta=model_errors[left]-model_errors[right]
                cell_result['contrasts'].append(dict(contrast=left+'_minus_'+right,
                    mean=float(delta.mean()),
                    mean_abs_group_difference=float(np.mean(abs(delta))),
                    fraction_group_difference_within_twice_indicator=float(np.mean(abs(delta)<=2*gi)),
                    mean_difference_to_twice_mean_indicator=float(abs(delta.mean())/max(2*gi.mean(),1e-15))))
            results.append(cell_result)
    summary=dict(stage=cfg.get('study_label','fixed-put E5 numerical label resolution'),cells=results,
        scope='Post-primary exploratory sensitivity only. Refinement indicator is not a certified bound on label error; ratios and ambiguity fractions do not establish true ranking or significance.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(stage=summary['stage'],cells=[dict(cell=c['cell'],indicator_mean=c['indicator_mean']) for c in results])),flush=True)


if __name__=='__main__':main()
