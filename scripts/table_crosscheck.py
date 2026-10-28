import pathlib,json,hashlib,argparse,time
from numerics import independent_split
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);result=[];start=time.perf_counter()
for row in cfg['cases']:
 T=row['T'];c=dict(a=.1,sigma=.85,r0=.06,rbar=.04,expiry=T/2,tenor=T/2,strike=.8)
 q1=independent_split(c,3201,400)['bond'];q2=independent_split(c,6401,800)['bond']
 result.append({'T':T,'independent_coarse':q1,'independent_fine':q2,'own_pde':row['own_pde'],'published_pde':row['published_pde'],'independent_vs_own_pde':abs(q2-row['own_pde']),'independent_refinement':abs(q2-q1)})
(out/'results.json').write_text(json.dumps({'rows':result,'seconds':time.perf_counter()-start},indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'results.json').read_bytes()).hexdigest()+'  results.json\n');(out/'FROZEN').write_text('Literature PDE discrepancy cross-check.\n')
