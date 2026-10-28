import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from numerics import pde
from risk_numerics import calls_only
class CallOnlyTest(unittest.TestCase):
 def test_identical_call_operator(self):
  c=dict(a=.2,sigma=.3,r0=.03,rbar=.04,expiry=2.,tenor=5.)
  for width in [1.,1.5]:
   np.testing.assert_array_equal(calls_only(c,[.7,.8,.9],101,50,width),pde(c,101,50,width,strikes=[.7,.8,.9])['calls'])
