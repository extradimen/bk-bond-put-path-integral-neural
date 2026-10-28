"""Exploratory paired F-E/F-B price and parameter-risk structure."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse, hashlib, json, pathlib
import numpy as np


def describe(a):
    a=np.asarray(a,dtype=float)
    return dict(mean=float(a.mean()),median=float(np.median(a)),q05=float(np.quantile(a,.05)),
                q95=float(np.quantile(a,.95)),negative_fraction=float(np.mean(a<0)))


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();cfg=json.loads(pathlib.Path(a.config).read_text())
    for file_key,sha_key in [('data_file','data_sha256'),('risk_file','risk_sha256')]:
        if hashlib.sha256(pathlib.Path(cfg[file_key]).read_bytes()).hexdigest()!=cfg[sha_key]:
            raise RuntimeError('frozen input checksum mismatch: '+file_key)
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    n=cfg['test_groups'];axes=cfg['coordinates'];records=[]
    with np.load(cfg['data_file']) as data,np.load(cfg['risk_file']) as risk:
        fe=data['test_FE_X'][:3*n];fb=data['test_FB_X'][:3*n]
        if not np.allclose(fe[:,:4],fb[:,:4]) or not np.allclose(fe[:,4:7],fb[:,6:9]):
            raise RuntimeError('F-E/F-B group contracts misaligned')
        for cell,X in [('FE',fe),('FB',fb)]:
            ids=data[f'test_{cell}_group'][:3*n]
            if not np.array_equal(ids,np.repeat(np.arange(n),3)) or not np.array_equal(ids,risk[f'test_{cell}_group']):
                raise RuntimeError('test groups or risk labels misaligned')
        yfe=data['test_FE_y'][:3*n];yfb=data['test_FB_y'][:3*n]
        rfe=risk['test_FE_risk'];rfb=risk['test_FB_risk']
        if rfe.shape!=rfb.shape!=(3*n,len(axes)):
            raise RuntimeError('risk tensor shape mismatch')
        premium=yfb-yfe;drisk=rfb-rfe
        sigma=fe[::3,1];quartile_edges=np.quantile(sigma,[0,.25,.5,.75,1])
        for strike_index in range(3):
            ix=np.arange(strike_index,3*n,3)
            records.append(dict(slice=f'strike_{strike_index}',groups=n,
                                premium=describe(premium[ix]),
                                FE={axis:describe(rfe[ix,j]) for j,axis in enumerate(axes)},
                                FB={axis:describe(rfb[ix,j]) for j,axis in enumerate(axes)},
                                FB_minus_FE={axis:describe(drisk[ix,j]) for j,axis in enumerate(axes)}))
        for q in range(4):
            group_mask=(sigma>=quartile_edges[q]) & (sigma<(quartile_edges[q+1]) if q<3 else sigma<=quartile_edges[q+1])
            ix=(3*np.flatnonzero(group_mask)[:,None]+np.arange(3)).reshape(-1)
            records.append(dict(slice=f'sigma_quartile_{q}',groups=int(group_mask.sum()),
                                sigma_bounds=[float(quartile_edges[q]),float(quartile_edges[q+1])],
                                premium=describe(premium[ix]),
                                FE={axis:describe(rfe[ix,j]) for j,axis in enumerate(axes)},
                                FB={axis:describe(rfb[ix,j]) for j,axis in enumerate(axes)},
                                FB_minus_FE={axis:describe(drisk[ix,j]) for j,axis in enumerate(axes)}))
        summary=dict(stage='fixed-put risk structure E3',groups=n,strikes=3,records=records,
                     early_exercise_premium_min=float(premium.min()),
                     early_exercise_negative_count=int(np.sum(premium < -cfg['premium_tolerance'])),
                     scope='Exploratory first 128 test groups whose derivative labels were generated after primary price results; descriptive only, no new primary p-values or generalization claim')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(stage=summary['stage'],groups=n,
                          early_exercise_premium_min=summary['early_exercise_premium_min'],
                          early_exercise_negative_count=summary['early_exercise_negative_count'])),flush=True)


if __name__=='__main__':main()
