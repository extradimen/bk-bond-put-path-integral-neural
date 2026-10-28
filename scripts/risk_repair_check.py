import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[v]='1'
import argparse,pathlib,json,time,hashlib
from concurrent.futures import ProcessPoolExecutor
from risk_followup import risk_one

def repair(job):
 row,old,revalidate=job
 if old is None or revalidate:return risk_one(row)
 if old["certified"]:return old
 if max(old["discretization_step_errors"])>1e-4:return risk_one(row)
 from risk_numerics import baselines
 start=time.perf_counter();cpu=time.process_time();base=baselines(row["parameters"],row["strikes"],old["reference_refinement"][-1]["h"])
 new=dict(old);new.update(gt_derivatives=base["gt"].tolist(),coarse_derivatives=base["coarse"].tolist(),gt_derivative_quadrature_change=base["quadrature"],gt_step_change=base["gt_step"],coarse_step_change=base["coarse_step"],baseline_refinement=base["meta"],certified=base["certified"],seconds=old["seconds"]+time.perf_counter()-start,cpu_seconds=old["cpu_seconds"]+time.process_time()-cpu)
 return new

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();c=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);rows=[json.loads(s)for s in pathlib.Path(c['input_path']).read_text().splitlines()][:40];start=time.perf_counter();result=[]
 previous=[json.loads(s) for s in pathlib.Path(c['previous_rows']).read_text().splitlines()] if c.get('previous_rows') else [None]*len(rows)
 assert len(previous)<=len(rows)
 previous += [None]*(len(rows)-len(previous))
 with ProcessPoolExecutor(max_workers=c['workers'])as pool:
  for i,r in enumerate(pool.map(repair,zip(rows,previous,[i in c.get("revalidate_indices",[]) for i in range(len(rows))]))):
   result.append(r)
   with (out/'rows.jsonl').open('a')as f:f.write(json.dumps(r)+'\n')
   print(json.dumps({'group':i,'certified':r['certified'],'elapsed':time.perf_counter()-start}),flush=True)
 report={'passed':all(r['certified']for r in result),'failed':[{'group':i,'ref':r['discretization_step_errors'],'gt_quadrature':r['gt_derivative_quadrature_change'],'gt_step':r['gt_step_change'],'coarse_step':r['coarse_step_change']}for i,r in enumerate(result)if not r['certified']],'elapsed_seconds':time.perf_counter()-start,'cpu_seconds':sum(r['cpu_seconds']for r in result)}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'checksums.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'for p in out.iterdir()if p.name!='checksums.sha256'));(out/'FROZEN').write_text('Numerical repair validation only; no fitted performance evidence.\n')
if __name__=='__main__':main()
