import sys,pathlib,unittest,numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from numerics import gt_bond,gt_price,mixture,pde
class NumericsTests(unittest.TestCase):
 def test_ou_kernel_normalization_and_moments(self):
  c=dict(a=.3,sigma=.2,rbar=.04,r0=.03);x=np.log(c['r0']);T=2
  w,mu,sd=mixture(c,T,x,96,kill=0)
  mean=np.log(c['rbar'])+(x-np.log(c['rbar']))*np.exp(-c['a']*T)
  var=c['sigma']**2*(-np.expm1(-2*c['a']*T))/(2*c['a'])
  self.assertAlmostEqual(float(w.sum()),1,10)
  self.assertAlmostEqual(float((w*mu).sum()),mean,10)
  self.assertAlmostEqual(float((w*(sd*sd+mu*mu)).sum()),var+mean*mean,9)
 def test_quadratic_vasicek_exactness(self):
  c=dict(a=.3,sigma=.2,rbar=np.exp(.04),r0=np.exp(.03));T=5.;x0=.03
  w,_,_=mixture(c,T,x0,192,rate_kind='linear')
  B=-np.expm1(-c['a']*T)/c['a']
  variance=c['sigma']**2/c['a']**2*(T-2*B+(-np.expm1(-2*c['a']*T))/(2*c['a']))
  exact=np.exp(-.04*T-(x0-.04)*B+variance/2)
  self.assertAlmostEqual(float(w.sum()),exact,10)
 def test_gt_constant_rate_limit(self):
  c=dict(a=.3,sigma=0,rbar=.04,r0=.04,expiry=1,tenor=4)
  v=gt_price(c,[.8]);self.assertAlmostEqual(v['bond'],np.exp(-.2),12)
  self.assertAlmostEqual(v['calls'][0],np.exp(-.04)*(np.exp(-.16)-.8),12)
 def test_pde_constant_rate_limit(self):
  c=dict(a=.3,sigma=0,rbar=.04,r0=.04,expiry=1,tenor=4,strike=.8)
  v=pde(c,101,200)
  self.assertLess(abs(v['bond']-np.exp(-.2)),2e-6)
  self.assertLess(abs(v['calls'][0]-np.exp(-.04)*(np.exp(-.16)-.8)),2e-6)
if __name__=='__main__':unittest.main()
