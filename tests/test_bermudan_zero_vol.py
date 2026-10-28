import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from bermudan_gtfk_split_pilot import price
from numerics import gt_bond


class BermudanZeroVolTests(unittest.TestCase):
    def test_deterministic_early_exercise(self):
        c=dict(a=.3,sigma=0.,r0=.04,rbar=.05)
        exercise=[1.,2.,3.]
        maturity=5.
        strike=.95
        x0=np.log(c['r0'])
        b=np.log(c['rbar'])
        direct=[]
        for date in exercise:
            xdate=b+(x0-b)*np.exp(-c['a']*date)
            payoff=max(strike-float(gt_bond(c,maturity-date,xdate)[0]),0.)
            direct.append(float(gt_bond(c,date,x0)[0])*payoff)
        bermudan=price(c,exercise,maturity,strike,801,64,32,.75)
        european=price(c,[exercise[-1]],maturity,strike,801,64,32,.75)
        self.assertLess(abs(bermudan-max(direct)),1e-6)
        self.assertLess(abs(european-direct[-1]),1e-6)
        self.assertGreaterEqual(bermudan,european)


if __name__=='__main__':
    unittest.main()
