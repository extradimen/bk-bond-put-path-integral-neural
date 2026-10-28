"""Governed pre-freeze support check for fixed-coefficient put methods."""
import argparse
import json
import pathlib
import time

import numpy as np

from bermudan_gtfk_split_pilot import price as gtfk_bermudan
from bermudan_pilot import value as pde_value
from numerics import gt_price


def check(case, cfg):
    c = case['model']
    exercise = case['exercise']
    maturity = case['maturity']
    strike = case['strike']
    rows = {'name': case['name'], 'contract': case, 'gtfk': [], 'pde': []}
    for n, nq, ny, width in cfg['gtfk_settings']:
        start = time.perf_counter()
        b = gtfk_bermudan(c, exercise, maturity, strike, n, nq, ny, width)
        rows['gtfk'].append(dict(n=n, nq=nq, ny=ny, width_scale=width,
                                 bermudan_put=b, seconds=time.perf_counter()-start))
    direct = dict(c, expiry=exercise[-1], tenor=maturity-exercise[-1])
    start = time.perf_counter()
    euro = gt_price(direct, [strike], nq=cfg['direct_nq'], ny=cfg['direct_ny'], both=True)
    rows['gtfk_direct_european'] = dict(price=euro['puts'][0], seconds=time.perf_counter()-start)
    for n, steps, width in cfg['pde_settings']:
        start = time.perf_counter()
        e = pde_value(c, [exercise[-1]], maturity, strike, n, steps, 'put', width)
        b = pde_value(c, exercise, maturity, strike, n, steps, 'put', width)
        rows['pde'].append(dict(n=n, steps_per_year=steps, width_scale=width,
                                european_put=e, bermudan_put=b, seconds=time.perf_counter()-start))
    vals = [r['bermudan_put'] for r in rows['gtfk']]
    refs = [r['bermudan_put'] for r in rows['pde']]
    rows['diagnostics'] = {
        'gtfk_range': max(vals)-min(vals), 'pde_range': max(refs)-min(refs),
        'pde_vs_gtfk_fine': refs[-1]-vals[-1],
        'early_exercise_pde': refs[-1]-rows['pde'][-1]['european_put'],
        'early_exercise_gtfk': vals[-1]-euro['puts'][0],
        'nonnegative': bool(min(vals+refs+[euro['puts'][0]]) >= -1e-10),
        'put_upper_bound': bool(max(vals+refs+[euro['puts'][0]]) <= strike+1e-10),
        'bermudan_ge_european_pde': bool(refs[-1]+1e-8 >= rows['pde'][-1]['european_put']),
        'bermudan_ge_european_gtfk': bool(vals[-1]+1e-8 >= euro['puts'][0])
    }
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    cfg = json.loads(pathlib.Path(args.config).read_text())
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for case in cfg['cases']:
        row = check(case, cfg)
        results.append(row)
        print(json.dumps({'name': row['name'], 'diagnostics': row['diagnostics']}), flush=True)
    result = {'stage': 'P3b fixed-coefficient method support pilot', 'cases': results,
              'scope': 'pre-freeze numerical support; no training or formal ranking'}
    (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
