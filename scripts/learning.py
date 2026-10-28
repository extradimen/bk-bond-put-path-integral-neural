"""NumPy MLP and Adam. Same implementation used for direct and residual fits."""
import numpy as np,time
class MLP:
 def __init__(self,nin,width,layers,seed):
  rng=np.random.default_rng(seed);sizes=[nin]+[width]*layers+[1]
  self.W=[rng.normal(0,np.sqrt(2/(a+b)),(a,b)) for a,b in zip(sizes[:-1],sizes[1:])]
  self.b=[np.zeros((1,b)) for b in sizes[1:]]
 def forward(self,x):
  h=[x]
  for i,(w,b) in enumerate(zip(self.W,self.b)):
   v=h[-1]@w+b;h.append(np.tanh(v) if i<len(self.W)-1 else v)
  return h
 def predict(self,x):return self.forward(x)[-1][:,0]
 def gradients(self,x,residual):
  h=self.forward(x);d=residual.reshape(-1,1);gw=[];gb=[]
  for i in range(len(self.W)-1,-1,-1):
   gw.append(h[i].T@d);gb.append(d.sum(axis=0,keepdims=True))
   if i:d=(d@self.W[i].T)*(1-h[i]**2)
  return list(reversed(gw)),list(reversed(gb))
 def input_gradient(self,X):
  h=self.forward(X);d=np.ones((len(X),1))
  for i in range(len(self.W)-1,-1,-1):
   d=d@self.W[i].T
   if i:d*=1-h[i]**2
  return d
 def tangent_gradients(self,X,dim,residual):
  h=self.forward(X);t=[np.broadcast_to(np.eye(X.shape[1])[dim],X.shape).copy()];dz=[]
  for i,w in enumerate(self.W):
   z=t[-1]@w;dz.append(z);t.append(z*(1-h[i+1]**2) if i<len(self.W)-1 else z)
  ah=np.zeros((len(X),1));at=residual.reshape(-1,1);gw=[];gb=[]
  for i in range(len(self.W)-1,-1,-1):
   if i<len(self.W)-1:
    phi=1-h[i+1]**2;az=ah*phi-2*at*h[i+1]*phi*dz[i];atz=at*phi
   else:az=ah;atz=at
   gw.append(h[i].T@az+t[i].T@atz);gb.append(az.sum(axis=0,keepdims=True))
   ah=az@self.W[i].T;at=atz@self.W[i].T
  return list(reversed(gw)),list(reversed(gb))
 def fit(self,X,y,V,vy,lr,seed,epochs=500,batch=256,patience=30,derivatives=None):
  rng=np.random.default_rng(seed);params=self.W+self.b;m=[np.zeros_like(p)for p in params];v=[p.copy()for p in m]
  best=np.inf;bestpars=None;wait=0;step=0;history=[];start=time.perf_counter();cpu_start=time.process_time()
  for epoch in range(epochs):
   for ii in np.array_split(rng.permutation(len(X)),max(1,int(np.ceil(len(X)/batch)))):
    pred=self.predict(X[ii]);gw,gb=self.gradients(X[ii],2*(pred-y[ii])/len(ii));grads=gw+gb
    # Exact tangent propagation and reverse gradients of derivative losses.
    if derivatives is not None:
     weight=derivatives['weight'];D=derivatives['values'];dims=derivatives['dims']
     derivative_pred=self.input_gradient(X[ii])
     for k,dim in enumerate(dims):
      residual=2*(derivative_pred[:,dim]-D[ii,k])*weight/len(ii)/len(dims)
      dw,db=self.tangent_gradients(X[ii],dim,residual)
      grads=[g+p for g,p in zip(grads,dw+db)]
    step+=1
    for j,(p,g) in enumerate(zip(params,grads)):
     m[j]=.9*m[j]+.1*g;v[j]=.999*v[j]+.001*g*g
     p-=lr*(m[j]/(1-.9**step))/(np.sqrt(v[j]/(1-.999**step))+1e-8)
   loss=float(np.mean(abs(self.predict(V)-vy)))
   if not np.isfinite(loss):raise FloatingPointError('nonfinite validation loss')
   history.append(loss)
   if loss<best-1e-12:best=loss;bestpars=[p.copy()for p in params];wait=0
   else:wait+=1
   if wait>=patience:break
  for p,q in zip(params,bestpars):p[:]=q
  return {'epochs':epoch+1,'validation_mae_scaled':best,'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu_start,'history':history}
