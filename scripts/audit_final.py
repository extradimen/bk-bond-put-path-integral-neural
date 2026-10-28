"""Read-only integrity audit of completed local return receipts and frozen artifacts."""
import pathlib,json,hashlib,argparse

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();cfg=json.load(open(a.config));out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);root=pathlib.Path(cfg['root']);entries=[];failed=[]
 for stage in cfg['required_stages']:
  d=root/'outputs'/stage;state=json.loads((d/'node-status.json').read_text());terminal=state.get('termination_evidence')=='os_child_wait_status'and state.get('return_code')==0
  if not terminal:failed.append(stage+': no successful OS child wait')
  results=d/'results'
  if not (results/'FROZEN').exists():failed.append(stage+': missing completion seal')
  if (results/'gate-failures.json').exists():failed.append(stage+': numerical gate failed')
  if (results/'summary.json').exists():
   summary=json.load(open(results/'summary.json'))
   if summary.get('passed') is False:failed.append(stage+': explicit validation failure')
  if stage.startswith('adaptive-gate'):
   gate=json.load(open(results/'gate.json'))
   if gate.get('status') not in ['enabled','not_enabled']:failed.append(stage+': missing conditional gate outcome')
  manifest=json.loads((d/'return-materials.json').read_text()) if (d/'return-materials.json').exists() else {'materials':[{'destination':str(f.relative_to(root)),'sha256':hashlib.sha256((root/'runs'/stage/f.name).read_bytes()).hexdigest()}for f in results.iterdir()if f.is_file()]};checks=[]
  for m in manifest['materials']:
   path=root/m['destination'];got=hashlib.sha256(path.read_bytes()).hexdigest();checks.append({'file':m['destination'],'sha256':got,'valid':got==m['sha256']})
   if got!=m['sha256']:failed.append(stage+': hash mismatch '+path.name)
  entries.append({'stage':stage,'run_id':state['run_id'],'successful_os_wait':terminal,'checks':checks})
 mainroot=root/'outputs'/cfg['main_stage']/'results';fitcount=sum(1 for _ in (mainroot/'fits.jsonl').open());splitcounts={sp:sum(1 for _ in (mainroot/(sp+'.jsonl')).open())for sp in ['train','val','test','ood_vol','ood_expiry']}
 if fitcount!=360:failed.append('Expected360 main candidate fits')
 if list(splitcounts.values())!=[4096,1024,2048,512,512]:failed.append('Main sample count mismatch')
 rroot=root/'outputs'/cfg['risk_stage']/'results';riskfits=len(json.load(open(rroot/'fits.json')));putfits=len(json.load(open(rroot/'put-fits.json')))
 if riskfits!=30 or putfits!=15:failed.append('Risk/put fit counts differ from protocol')
 for split,n in [('train',256),('val',128),('test',128)]:
  rows=[json.loads(x)for x in (rroot/(split+'-risk.jsonl')).read_text().splitlines()]
  if len(rows)!=n or any(not r['certified']for r in rows):failed.append('Risk label certification/count mismatch: '+split)
 broot=root/'outputs'/cfg['baseline_stage']/'results';fine=[json.loads(x)for x in (broot/'fine-test.jsonl').read_text().splitlines()];bsummary=json.load(open(broot/'summary.json'));baselinefits=len(json.load(open(broot/'fits.json')));expected=5+15*len({256,bsummary['E5']['low_precision_max_groups']})
 if len(fine)!=512 or any(not r['certified']for r in fine):failed.append('E5 fine-reference certification/count mismatch')
 if baselinefits!=expected:failed.append('E2/E5 fit count mismatch')

 report={'passed':not failed,'failures':failed,'entries':entries,'counts':{'main_fits':fitcount,'splits':splitcounts,'risk_fits':riskfits,'put_fits':putfits,'baseline_precision_fits':baselinefits,'fine_reference_groups':len(fine)},'note':'Negative conditional E6 gate counts as complete only with its explicit gate artifact. This audit does not prove numerical truth, novelty, or empirical validity.'}
 (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'audit.json').read_bytes()).hexdigest()+'  audit.json\n')
 if failed:raise RuntimeError('Final integrity audit did not pass')
 (out/'FROZEN').write_text('Integrity audit passed.\n')
if __name__=='__main__':main()
