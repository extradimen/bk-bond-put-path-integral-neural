"""Pre-freeze timing and numerical-quality pilot for fixed BK bond puts."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
import pathlib
import time

import numpy as np

from bermudan_gtfk_split_pilot import price as gtfk_bermudan
from bermudan_pilot import value as pde_value
from numerics import gt_price


def sample(n, seed, region='main'):
    rng = np.random.default_rng(seed)
    cases = []
    for u in rng.random((n, 8)):
        logscale = lambda lo, hi, z: float(np.exp(np.log(lo)+(np.log(hi)-np.log(lo))*z))
        a = logscale(.1, 1.0, u[0])
        sigma = float(.65+.2*u[1]) if region == 'vol' else float(.1+.55*u[1])
        r0 = logscale(.01, .1, u[2])
        rbar = logscale(.01, .1, u[3])
        if region == 'long':
            e1 = 1.0+u[4]
            e2 = e1+1.0+u[5]
            e3 = e2+1.0+u[6]
            maturity = e3+2.0+2*u[7]
        else:
            e1 = .5+u[4]
            e2 = e1+.5+u[5]
            e3 = e2+.5+u[6]
            maturity = e3+1.0+2*u[7]
        base = math.exp(-rbar*(maturity-e3))
        strikes = [min(.999, float(base*z)) for z in (.9, 1.0, 1.1)]
        cases.append(dict(model=dict(a=a, sigma=sigma, r0=r0, rbar=rbar),
                          exercise=[e1, e2, e3], maturity=maturity, strikes=strikes))
    return cases


def reference(c, exercise, maturity, strike, option_type):
    settings = [(3201, 400, 1.0), (6401, 400, 1.0), (3201, 800, 1.0), (4801, 400, 1.5)]
    values = [pde_value(c, exercise, maturity, strike, n, steps, option_type, width)
              for n, steps, width in settings]
    error = max(abs(values[i]-values[0]) for i in range(1, len(values)))
    price = values[2]
    if error > 1e-6:
        settings += [(6401, 800, 1.0), (9601, 800, 1.5)]
        values += [pde_value(c, exercise, maturity, strike, n, steps, option_type, width)
                   for n, steps, width in settings[-2:]]
        error = max(abs(values[4]-values[1]), abs(values[4]-values[2]),
                    abs(values[5]-values[4]))
        price = values[4]
    return dict(price=price, error_indicator=error, settings=settings, values=values,
                certified=bool(error <= 1e-6))


def one(item):
    idx, contract = item
    started = time.perf_counter()
    cpu_started = time.process_time()
    c = contract['model']
    exercise = contract['exercise']
    maturity = contract['maturity']
    rows = []
    try:
        direct = dict(c, expiry=exercise[-1], tenor=maturity-exercise[-1])
        direct_euro = gt_price(direct, contract['strikes'], nq=192, ny=96, both=True)['puts']
        direct_euro_coarse = gt_price(direct, contract['strikes'], nq=96, ny=48, both=True)['puts']
        for j, strike in enumerate(contract['strikes']):
            ref = reference(c, exercise, maturity, strike, 'put')
            euro = reference(c, [exercise[-1]], maturity, strike, 'put')
            g1 = gtfk_bermudan(c, exercise, maturity, strike, 1201, 192, 96, .75)
            g2 = gtfk_bermudan(c, exercise, maturity, strike, 1601, 192, 96, .75)
            g3 = gtfk_bermudan(c, exercise, maturity, strike, 1601, 192, 96, 1.0)
            g_values = [g1, g2, g3]
            numerical = max(abs(g2-g1), abs(g3-g1))
            if numerical > 1e-6:
                g4 = gtfk_bermudan(c, exercise, maturity, strike, 2401, 192, 96, .75)
                g_values.append(g4)
                numerical = max(abs(g4-g2), abs(g4-g3))
            coarse = pde_value(c, exercise, maturity, strike, 201, 100, 'put')
            coarse_euro = pde_value(c, [exercise[-1]], maturity, strike, 201, 100, 'put')
            rows.append(dict(strike=strike, reference=ref, european_reference=euro,
                             gtfk_bermudan=g_values[-1] if len(g_values)>3 else g2,
                             gtfk_settings=[(1201,192,96,.75),(1601,192,96,.75),(1601,192,96,1.0)]
                                           + ([(2401,192,96,.75)] if len(g_values)>3 else []),
                             gtfk_values=g_values,
                             gtfk_european=direct_euro[j],
                             gtfk_european_numerical_indicator=abs(direct_euro[j]-direct_euro_coarse[j]),
                             gtfk_numerical_indicator=numerical,
                             coarse_pde=coarse, coarse_european_pde=coarse_euro,
                             monotonic=bool(ref['price']+1e-8 >= euro['price']),
                             bounds=bool(0 <= min(ref['price'], euro['price'], g_values[-1],
                                                   direct_euro[j], coarse, coarse_euro) and
                                         max(ref['price'], euro['price'], g_values[-1],
                                             direct_euro[j], coarse, coarse_euro) <= strike+1e-8)))
        return dict(group=idx, contract=contract, rows=rows, seconds=time.perf_counter()-started,
                    cpu_seconds=time.process_time()-cpu_started,
                    certified=all(r['reference']['certified'] and r['european_reference']['certified']
                                  and r['gtfk_numerical_indicator'] <= 1e-6
                                  and r['gtfk_european_numerical_indicator'] <= 1e-6
                                  and r['monotonic'] and r['bounds'] for r in rows))
    except Exception as exc:
        return dict(group=idx, contract=contract, rows=rows, seconds=time.perf_counter()-started,
                    cpu_seconds=time.process_time()-cpu_started,
                    certified=False, error=type(exc).__name__+': '+str(exc))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    cfg = json.loads(pathlib.Path(args.config).read_text())
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    contracts = sample(cfg['groups'], cfg['seed'], cfg.get('region', 'main'))
    start = time.perf_counter()
    rows = []
    with ProcessPoolExecutor(max_workers=cfg['workers']) as pool, (out/'groups.jsonl').open('w') as ledger:
        for row in pool.map(one, enumerate(contracts)):
            rows.append(row)
            ledger.write(json.dumps(row)+'\n')
            ledger.flush()
            print(json.dumps(dict(group=row['group'], certified=row['certified'],
                                  seconds=row['seconds'])), flush=True)
    summary = dict(stage='P3b F-B data and timing pilot', groups=len(rows),
                   certified_groups=sum(r['certified'] for r in rows),
                   failures=[r['group'] for r in rows if not r['certified']],
                   elapsed_seconds=time.perf_counter()-start,
                   group_cpu_seconds_sum=sum(r['seconds'] for r in rows),
                   scope='pre-freeze timing; no training or method ranking')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
