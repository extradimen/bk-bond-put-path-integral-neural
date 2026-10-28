import json,time,pathlib,platform,hashlib,signal,argparse
import numpy as np
from numerics import pde,gt_price,gt_bond

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 cfg=json.load(open(a.config)); out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def alarm(*_):raise TimeoutError('P1 wallclock exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg['max_seconds']);start=time.perf_counter(); rows=[]
 for c in cfg['cases']:
  timings={}; results={}
  for name,n,steps,ws in cfg['levels']:
   t=time.perf_counter();results[name]=pde(c,n,steps,ws);timings[name]=time.perf_counter()-t
  gt={}
  for q in cfg['quadrature_orders']:
   t=time.perf_counter();gt[str(q)]=gt_price(c,[c['strike']],q,q);timings['gt'+str(q)]=time.perf_counter()-t
  norm=float(gt_bond(c,c['expiry'],np.log(c['r0']),192,kill=0)[0])
  errors={}
  for key in ['bond','calls']:
   value=lambda name:np.asarray(results[name][key])
   errors[key]={'space':float(np.max(abs(value('s3')-value('s2')))), 'space_previous':float(np.max(abs(value('s2')-value('s1')))), 'time':float(np.max(abs(value('t3')-value('s3')))), 'time_previous':float(np.max(abs(value('s3')-value('t1')))), 'domain':float(np.max(abs(value('wide')-value('s3'))))}
  row={'parameters':c,'pde':results,'gtfk':gt,'zero_killing_normalization_error':abs(norm-1),'errors':errors,'timings':timings}
  rows.append(row);print(json.dumps(row),flush=True)
 result={'stage':'P1','rows':rows,'elapsed_seconds':time.perf_counter()-start,'runtime':platform.python_version(),'formal_labels_certified':False,'reason':'Independent reference cross-check and full-domain per-point certification still required.'}
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'results.json').read_bytes()).hexdigest()+'  results.json\n');(out/'FROZEN').write_text('Validation only.\n')
if __name__=='__main__':main()
