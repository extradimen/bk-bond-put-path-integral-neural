"""Disjoint risk-label shard; no fit or test-driven sampling."""
import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[v]='1'
import pathlib,json,argparse,time,hashlib,signal
from concurrent.futures import ProcessPoolExecutor
from risk_followup import risk_one

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();c=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
 def alarm(*_):raise TimeoutError('Risk shard budget exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(c['max_seconds'])
 if c.get('runtime_crosscheck'):
  import numpy as np
  cc=c['runtime_crosscheck'];source=[json.loads(s)for s in pathlib.Path(cc['inputs']).read_text().splitlines()];baseline=[json.loads(s)for s in pathlib.Path(cc['risks']).read_text().splitlines()];checks=[]
  with ProcessPoolExecutor(max_workers=min(c['workers'],len(cc['indices'])))as pool:
   values=list(pool.map(risk_one,[source[i]for i in cc['indices']]))
  for i,r in zip(cc['indices'],values):
   errors={key:float(np.max(abs(np.asarray(r[key])-np.asarray(baseline[i][key]))))for key in ['reference_derivatives','gt_derivatives','coarse_derivatives']}
   checks.append({'group':i,'certified':r['certified'],'differences':errors,'cpu_seconds':r['cpu_seconds'],'passed':bool(r['certified']and max(errors.values())<=cc['tolerance'])})
  (out/'runtime-crosscheck.json').write_text(json.dumps(checks,indent=2)+'\n')
  if not all(r['passed']for r in checks):(out/'gate-failures.json').write_text(json.dumps(checks));return
 rows=[json.loads(s)for s in pathlib.Path(c['input_path']).read_text().splitlines()][c['offset']:c['offset']+c['count']];assert len(rows)==c['count'];(out/'inputs.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows));reuse=[]
 if c.get('reuse_path'):
  assert c['offset']==0
  reuse=[json.loads(s)for s in pathlib.Path(c['reuse_path']).read_text().splitlines()];assert len(reuse)==c['reuse_count']and all(r['certified']for r in reuse)
 results=list(reuse)
 with (out/'risk.jsonl').open('w')as f:
  for r in reuse:f.write(json.dumps(r)+'\n')
 with ProcessPoolExecutor(max_workers=c['workers'])as pool:
  for i,r in enumerate(pool.map(risk_one,rows[len(reuse):]),start=len(reuse)):
   results.append(r)
   with (out/'risk.jsonl').open('a')as f:f.write(json.dumps(r)+'\n')
   print(json.dumps({'group':c['offset']+i,'certified':r['certified'],'elapsed':time.perf_counter()-start}),flush=True)
 bad=[c['offset']+i for i,r in enumerate(results)if not r['certified']];report={'split':c['split'],'offset':c['offset'],'count':len(results),'reused_count':len(reuse),'failures':bad,'elapsed_seconds':time.perf_counter()-start,'new_derivative_cpu_seconds':sum(r['cpu_seconds']for r in results[len(reuse):]),'passed':not bad}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 if bad:(out/'gate-failures.json').write_text(json.dumps(bad));return
 (out/'checksums.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'for p in out.iterdir()if p.name!='checksums.sha256'));(out/'FROZEN').write_text('Disjoint risk-label shard certified; no fitting.\n')
if __name__=='__main__':main()
