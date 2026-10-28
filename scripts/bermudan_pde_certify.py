"""Governed independent grid-axis checks for Bermudan put PDE reference."""
import argparse
import json
import pathlib
import time
from bermudan_pilot import value


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    cfg=json.loads(pathlib.Path(a.config).read_text());out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    records=[]
    for case in cfg['cases']:
        rows=[]
        for n,steps,width in cfg['settings']:
            start=time.perf_counter()
            e=value(case['model'],[case['exercise'][-1]],case['maturity'],case['strike'],n,steps,'put',width)
            b=value(case['model'],case['exercise'],case['maturity'],case['strike'],n,steps,'put',width)
            rows.append({'n':n,'steps_per_year':steps,'width_scale':width,'european_put':e,'bermudan_put':b,'seconds':time.perf_counter()-start})
        records.append({'name':case['name'],'settings':rows})
    result={'stage':'P3a/P3b PDE reference axis certification pilot','cases':records,'scope':'separate space/time/domain checks; no formal method ranking'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
