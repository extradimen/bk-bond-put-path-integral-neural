import unittest,sys,pathlib,numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from learning import MLP
class TestBackprop(unittest.TestCase):
 def test_gradients(self):
  net=MLP(2,3,2,1);x=np.array([[.3,-.1],[.1,.7]]);y=np.array([.2,.4]);eps=1e-6
  gw,gb=net.gradients(x,2*(net.predict(x)-y)/2)
  for p,g in zip(net.W+net.b,gw+gb):
   for idx in np.ndindex(p.shape):
    old=p[idx];p[idx]=old+eps;up=np.mean((net.predict(x)-y)**2)
    p[idx]=old-eps;dn=np.mean((net.predict(x)-y)**2);p[idx]=old
    self.assertAlmostEqual(g[idx],(up-dn)/(2*eps),7)
 def test_input_and_tangent_gradients(self):
  net=MLP(2,3,2,3);x=np.array([[.2,-.3],[.6,.1]]);eps=1e-6;target=np.array([.4,-.1]);dim=0
  xp=x.copy();xm=x.copy();xp[:,dim]+=eps;xm[:,dim]-=eps
  np.testing.assert_allclose(net.input_gradient(x)[:,dim],(net.predict(xp)-net.predict(xm))/(2*eps),rtol=1e-7,atol=1e-9)
  g=net.input_gradient(x)[:,dim];gw,gb=net.tangent_gradients(x,dim,2*(g-target)/len(x))
  for p,grad in zip(net.W+net.b,gw+gb):
   for idx in np.ndindex(p.shape):
    old=p[idx];p[idx]=old+eps;up=np.mean((net.input_gradient(x)[:,dim]-target)**2)
    p[idx]=old-eps;dn=np.mean((net.input_gradient(x)[:,dim]-target)**2);p[idx]=old
    self.assertAlmostEqual(grad[idx],(up-dn)/(2*eps),7)
if __name__=='__main__':unittest.main()
