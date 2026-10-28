"""Rendering only: reads frozen synthesis summaries; no fitting or bootstrap."""
import argparse,json,pathlib,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
COL={'A':'#243447','B':'#0072B2','C':'#E69F00','D':'#009E73','Dbase':'#777777'}
MARK={'B':'o','C':'s','D':'^'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--summary',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=pathlib.Path(a.out);root.mkdir(parents=True,exist_ok=False);d=json.load(open(a.summary));plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
 def save(fig,name):
  for ext in ['png','svg','pdf']:fig.savefig(root/(name+'.'+ext),dpi=320,bbox_inches='tight')
  plt.close(fig)
 for selection in ['tuned','fixed_capacity']:
  fig,axes=plt.subplots(1,3,figsize=(10,3.2),sharey=True)
  for ax,split,title in zip(axes,['test','ood_vol','ood_expiry'],['In-domain test','Higher volatility OOD','Longer expiry OOD']):
   for method in ['B','C','D']:
    rows=sorted([r for r in d['main']if r['split']==split and r['method']==method and r['selection']==selection],key=lambda r:r['budget']);x=[r['budget']for r in rows];y=[r['metrics']['mae']['mean']for r in rows];lo=[r['metrics']['mae']['min']for r in rows];hi=[r['metrics']['mae']['max']for r in rows]
    ax.plot(x,y,color=COL[method],marker=MARK[method],label=method);ax.fill_between(x,lo,hi,color=COL[method],alpha=.13)
    for j,r in enumerate(rows):ax.scatter([x[j]]*5,r['metrics']['mae']['seed_values'],color=COL[method],s=6,alpha=.6)
   for method in ['A','Dbase']:
    row=next(r for r in d['main']if r['split']==split and r['method']==method);ax.axhline(row['metrics']['mae'],color=COL[method],linestyle='--' if method=='A'else ':',label=method)
   ax.axhline(1e-6,color='#D55E00',lw=.7,ls='-.');ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xticks([256,1024,4096],['256','1024','4096']);ax.set_xlabel('Training parameter groups');ax.set_title(title);ax.grid(axis='y',alpha=.2)
  axes[0].set_ylabel('Price MAE per unit face value');handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,ncol=5,fontsize=8,loc='upper center',bbox_to_anchor=(.5,1.03));fig.tight_layout(rect=[0,0,1,.92]);save(fig,'price-learning-curves-'+selection)
 fig,axes=plt.subplots(1,2,figsize=(8,3.4),sharey=True)
 for ax,mode,title in zip(axes,['single','surface'],['One strike per request','Five strikes per request']):
  for method in ['A','B','C','D','Dbase']:
   r=next(r for r in d['main']if r['split']=='test'and r['method']==method and (r['budget']==4096 and r['selection']=='tuned'if method in ['B','C','D']else True));mae=r['metrics']['mae'];y=mae['mean']if isinstance(mae,dict)else mae
   key='A'if method=='A'else 'D_baseline'if method=='Dbase'else 'tuned-'+method;bench=d['cost']['online_benchmark']['samples'][mode][key];x=bench['median']*1000
   if isinstance(mae,dict):ax.plot([x,x],[mae['min'],mae['max']],color=COL[method],alpha=.5)
   ax.scatter(x,y,facecolors='none'if method=='Dbase'else COL[method],edgecolors=COL[method],marker=MARK.get(method,'D'),s=32);ax.annotate(method,(x,y),xytext=(5,-15)if method=='Dbase'else (5,18)if method=='D'else (5,5),textcoords='offset points');ax.plot([bench['q10']*1000,bench['q90']*1000],[y,y],color=COL[method],alpha=.5)
  ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Serial latency, ms/request');ax.set_title(title);ax.set_ylim(bottom=6e-6);ax.grid(alpha=.2)
 axes[0].set_ylabel('In-domain price MAE');fig.tight_layout();save(fig,'accuracy-latency')
 fig,axes=plt.subplots(1,4,figsize=(11,3.1))
 for j,ax in enumerate(axes):
  for k,m in enumerate(['B','C','D']):
   for sup,off,marker in [('price',-.12,'o'),('price_derivatives',.12,'s')]:
    r=next(r for r in d['risk']['aggregated']if r['method']==m and r['supervision']==sup)['risk_mae'][j];x=k+off;ax.plot([x,x],[r['min'],r['max']],color=COL[m]);ax.scatter(x,r['mean'],color=COL[m],marker=marker,s=25)
  for baseline in d['risk']['baselines']:ax.axhline(baseline['risk_mae'][j],color=COL[baseline['method']],ls='--' if baseline['method']=='A' else ':',lw=1)
  ax.set_xticks([0,1,2],['B','C','D']);ax.set_yscale('log');ax.set_title(['dV / d log(a)','dV / d sigma','dV / d log(r0)','dV / d log(rbar)'][j]);ax.grid(axis='y',alpha=.2)
 axes[0].set_ylabel('Derivative MAE (coordinate units)');fig.legend(handles=[Line2D([0],[0],marker='o',color='black',ls='',label='Price supervision'),Line2D([0],[0],marker='s',color='black',ls='',label='Price + three derivatives'),Line2D([0],[0],color=COL['A'],ls='--',label='A: GTFK'),Line2D([0],[0],color=COL['Dbase'],ls=':',label='Dbase: coarse PDE')],loc='lower center',ncol=4,bbox_to_anchor=(.5,-.05));fig.tight_layout();save(fig,'risk-supervision')
 caption='''Figures use the frozen synthesis summary. A=GTFK; B=direct neural network; C=GTFK residual network; D=coarse-PDE residual network; Dbase=coarse PDE alone.\n\nPrice learning curves: five seeds, 256/1024/4096 training groups, five strikes per group. Curves are seed means; bands are seed min/max, not confidence intervals. Separate tuned and fixed-capacity figures retain both comparisons. Tuned models use validation-only hyperparameter selection. Fixed capacity is3hidden layers of64units and learning rate0.001. Test has2048groups and each OOD set512groups. Horizontal dash-dot line is the1e-6 reference convergence threshold, not a statistical confidence bound or proven total error bound.\n\nAccuracy-latency: price MAE averages five seeds; latency measures seed11 selected architectures,16 preselected test groups and3 repetitions, preloaded weights, serial CPU. Horizontal bars are latency10th/90th percentiles; vertical bars are price-MAE seed min/max. Hybrid timing sums separately measured baseline and neural work for the same request; wrapper/addition overhead is omitted. Label generation, training and model loading are excluded here and reported separately in the cost tables. No quality-equivalent speedup is implied.\n\nRisk supervision:128 held-out test groups, five seeds, fixed3x64architecture. Points=seed mean; bars=min/max. Horizontal reference lines retain A and Dbase derivative errors. Three directions are supervised; log(rbar) is evaluated without derivative supervision. Each panel has its own vertical scale because units differ. PDE derivatives passed independent space/time/finite-difference checks at1e-4; the figure does not establish hedging performance on real markets.\n'''
 (root/'captions.txt').write_text(caption);(root/'source.json').write_text(json.dumps({'path':str(pathlib.Path(a.summary).resolve()),'sha256':hashlib.sha256(pathlib.Path(a.summary).read_bytes()).hexdigest()},indent=2));(root/'checksums.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n'for f in root.iterdir()if f.is_file()and f.name!='checksums.sha256'))
if __name__=='__main__':main()
