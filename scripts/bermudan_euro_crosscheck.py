"""Governed independent European put integration and parity cross-check."""
import argparse
import json
import pathlib
import time
from numerics import gt_price
from bermudan_gtfk_split_pilot import price as split_price


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    cfg=json.loads(pathlib.Path(a.config).read_text());out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    records=[]
    for case in cfg['cases']:
        c=dict(case['model']);c['expiry']=case['exercise'][-1];c['tenor']=case['maturity']-c['expiry']
        rows=[]
        for nq,ny,n in cfg['settings']:
            t=time.perf_counter()
            direct=gt_price(c,[case['strike']],nq=nq,ny=ny,both=True)
            split=split_price(case['model'],[c['expiry']],case['maturity'],case['strike'],n,nq,ny)
            call=direct['calls'][0];put=direct['puts'][0]
            rows.append({'nq':nq,'ny':ny,'curve_n':n,'direct_put':put,'split_put':split,'integration_difference':split-put,
                'direct_call':call,'parity_gap_using_direct_bond':call-put-direct['bond']+case['strike']*direct['discount'],
                'seconds':time.perf_counter()-t})
        records.append({'name':case['name'],'settings':rows})
    result={'stage':'P3b European GTFK cross-check','cases':records,'scope':'independent integration paths and approximate parity; not a formal ranking'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
