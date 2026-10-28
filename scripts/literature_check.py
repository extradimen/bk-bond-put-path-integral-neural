import argparse,json,pathlib,numpy as np,hashlib,time
from numerics import gt_bond,pde_curve,grid_for
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);rows=[];start=time.perf_counter()
for T,published_gt,published_pde in cfg['table']:
 c=dict(a=.1,sigma=.85,r0=.06,rbar=.04,expiry=T,tenor=T)
 gt=[float(gt_bond(c,T,np.log(.06),q)[0])for q in [96,192,384]]
 refs=[]
 for n,nt in [(1601,800),(3201,1600),(6401,3200)]:
  g=grid_for(c,n);refs.append(float(pde_curve(c,T,g,nt)[n//2]))
 rows.append({'T':T,'gtfk':gt,'pde':refs,'published_gtfk':published_gt,'published_pde':published_pde,'gt_rounding_match':abs(gt[-1]-published_gt)<=5.1e-5,'pde_rounding_match':abs(refs[-1]-published_pde)<=5.1e-5})
result={'source':cfg['source'],'source_table':'Table I','elapsed_seconds':time.perf_counter()-start,'rows':rows}
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'results.json').read_bytes()).hexdigest()+'  results.json\n');(out/'FROZEN').write_text('Independent literature table reproduction check.\n')
