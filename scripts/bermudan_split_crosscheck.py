"""Independent OU Gaussian propagation and discount-killing split for put checks."""
import argparse
import json
import pathlib
import time

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.special import roots_hermitenorm

from numerics import grid_for


def value(c, exercise, maturity, strike, n, steps_per_year, order, width_scale):
    g = grid_for(c, n, width_scale)
    a, sigma, b = c['a'], c['sigma'], np.log(c['rbar'])
    nodes, weights = roots_hermitenorm(order)
    weights /= np.sqrt(2*np.pi)

    def evolve(v, horizon):
        steps = max(4, round(horizon*steps_per_year))
        dt = horizon/steps
        kill = np.exp(-np.exp(g)*dt/2)
        conditional = b+(g[:, None]-b)*np.exp(-a*dt)
        conditional = conditional + sigma*np.sqrt(-np.expm1(-2*a*dt)/(2*a))*nodes
        conditional = np.clip(conditional, g[0], g[-1])
        for _ in range(steps):
            v = kill*(CubicSpline(g, v*kill)(conditional)@weights)
        return v

    continuation = None
    previous = maturity
    for date in reversed(exercise):
        bond = evolve(np.ones(n), maturity-date)
        intrinsic = np.maximum(strike-bond, 0)
        if continuation is None:
            continuation = intrinsic
        else:
            continuation = evolve(continuation, previous-date)
            continuation = np.maximum(intrinsic, continuation)
        previous = date
    return float(evolve(continuation, exercise[0])[n//2])


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
        rows = []
        for n, steps, order, width in cfg['settings']:
            started = time.perf_counter()
            e = value(case['model'], [case['exercise'][-1]], case['maturity'], case['strike'], n, steps, order, width)
            b = value(case['model'], case['exercise'], case['maturity'], case['strike'], n, steps, order, width)
            rows.append(dict(n=n, steps_per_year=steps, order=order, width_scale=width,
                             european_put=e, bermudan_put=b, seconds=time.perf_counter()-started))
        results.append(dict(name=case['name'], settings=rows))
    report = dict(stage='P3b independent OU split crosscheck', cases=results,
                  scope='independent propagation pilot; no method ranking')
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
