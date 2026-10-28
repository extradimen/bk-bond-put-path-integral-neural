import sys, pathlib, unittest, math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from reference_pilot import stepper, price
class SolverTest(unittest.TestCase):
    def test_constant_rate_discount(self):
        solve=stepper([-1.,0.,1.],0,0,0,0.1)
        got=solve([1,1,1])
        for x,v in zip([-1.,0.,1.],got): self.assertAlmostEqual(v,1/(1+0.1*math.exp(x)),14)
    def test_deterministic_at_equilibrium(self):
        c=dict(a=0.3,sigma=0,r0=0.04,rbar=0.04,expiry=1,tenor=4,strike=0.8)
        got=price(c,101,100,6)
        exact_bond=math.exp(-0.04*5)
        exact_call=math.exp(-0.04)*max(math.exp(-0.04*4)-0.8,0)
        self.assertLess(abs(got['bond']-exact_bond),0.0002)
        self.assertLess(abs(got['call']-exact_call),0.0002)
if __name__=='__main__': unittest.main()
