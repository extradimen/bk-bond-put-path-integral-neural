"""Render a Chinese report from already frozen, audited analysis artifacts."""
import json,pathlib,argparse,hashlib

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();c=json.load(open(a.config));root=pathlib.Path(c['root']);out=root/'outputs'/c['out'];out.mkdir(exist_ok=False)
 load=lambda stage,name:json.load(open(root/'outputs'/stage/'results'/name))
 d=load(c['synthesis'],'summary.json');diag=load(c['diagnostics'],'diagnostics.json');gate=load(c['adaptive'],'gate.json');audit=load(c['audit'],'audit.json');assert audit['passed']
 f=lambda x:f'{x:.3g}'
 ag=lambda x:f"{f(x['mean'])} [{f(x['min'])}, {f(x['max'])}]"
 lines=['# 路径积分、神经网络与混合定价：完整实验报告','', '本报告比较固定系数 Black–Karasinski 模型下零息债券欧式看涨期权的数值方法。价格按单位债券面值计；1e-4 等于面值的1个基点。所有结论限定于本模型、参数范围和实现，不涉及真实市场是否具有物理量子性。','', '## 实际完成范围','',f"主实验 {audit['counts']['main_fits']} 次候选训练；数据划分 {audit['counts']['splits']}。风险监督训练 {audit['counts']['risk_fits']} 次，独立看跌网络 {audit['counts']['put_fits']} 次，E2/E5对照训练 {audit['counts']['baseline_precision_fits']} 次。正式训练合计{audit['counts']['main_fits']+audit['counts']['risk_fits']+audit['counts']['put_fits']+audit['counts']['baseline_precision_fits']}次。E6状态：{gate['status']}。各必需阶段均有节点操作系统子进程退出证据及回传校验。",'', 'A是GTFK路径积分近似；B直接学习参考价格；C学习参考价格减GTFK近似的残差；D学习参考价格减粗PDE价格的残差。Dbase是粗PDE本身。C和D在线仍须计算各自基线，因此不能把网络前向传播时间当成完整定价时间。','', '## 主比较','', '4096训练参数组、五随机种子。网络每个种子按验证集从八配置选择；方括号为五种子的最小值/最大值，**不是置信区间**。A与Dbase不训练。','', '| 方法 | 域内测试MAE | 高波动域外MAE | 长期限域外MAE |','|---|---:|---:|---:|']
 if c.get('interpretation'):lines[4:4]=(root/c['interpretation']).read_text().splitlines()+['']
 for m in ['A','B','C','D','Dbase']:
  cells=[]
  for sp in ['test','ood_vol','ood_expiry']:
   r=next(r for r in d['main']if r['split']==sp and r['method']==m and (r['budget']==4096 and r['selection']=='tuned'if m in ['B','C','D']else True));v=r['metrics']['mae'];cells.append(ag(v)if isinstance(v,dict)else f(v))
  lines.append('| '+m+' | '+' | '.join(cells)+' |')
 lines+=['','域内测试的尾部价格误差如下；对网络先逐种子计算，再显示种子均值与范围。1e-4为单位面值的1个基点。','', '| 方法 | 绝对误差99%分位数 | 最大绝对误差 | 超过1基点的比例 |','|---|---:|---:|---:|']
 for m in ['A','B','C','D','Dbase']:
  row=next(r for r in d['main']if r['split']=='test'and r['method']==m and (r['budget']==4096 and r['selection']=='tuned'if m in ['B','C','D']else True))
  values=[row['metrics'][k]for k in ['q99','max','exceed_1e_minus4']]
  lines.append('| '+m+' | '+' | '.join(ag(v)if isinstance(v,dict)else f(v)for v in values)+' |')
 lines+=['','固定容量结果与完整预算路径另见图表及原始汇总，不能只选择调参后的冠军。','', '| 方法 | 固定容量256组MAE | 固定容量1024组MAE | 固定容量4096组MAE |','|---|---:|---:|---:|']
 for m in ['B','C','D']:lines.append('| '+m+' | '+' | '.join(ag(next(r for r in d['main']if r['split']=='test'and r['method']==m and r['selection']=='fixed_capacity'and r['budget']==b)['metrics']['mae'])for b in [256,1024,4096])+' |')
 lines+=['','域内、4096组、调参配置的配对比较如下。正数表示右侧方法误差更小。区间按参数组重抽样2000次，保留同组五执行价，先对五个固定种子平均；是点态95%区间，不控制全部比较的家族错误率。','', '| 左−右 | 平均绝对误差之差 | 95%区间 |','|---|---:|---:|']
 for r in d['paired']:
  if r['split']=='test'and r['selection']=='tuned'and r['budget']==4096:lines.append(f"| {r['contrast']} | {f(r['mean'])} | [{f(r['ci95'][0])}, {f(r['ci95'][1])}] |")
 lines+=['','## 基线选择与标签精度','',f"E2按验证集选择误差最接近GTFK的粗PDE网格：{d['E2']['design']['selected_grid']}点。GTFK验证MAE={f(d['E2']['design']['target_gt_mae'])}；候选PDE误差={d['E2']['design']['candidate_errors']}。这只是全局接近，不保证逐样本误差相等。匹配D的测试MAE为{ag(d['E2']['matched_mae'])}，使用1024组和固定容量。",'',f"E5把预先指定的512测试组参考价格进一步细化至1e-7收敛门槛，并保持原执行价。新旧参考MAE={f(d['E5']['reference_change']['mae'])}，最大差={f(d['E5']['reference_change']['max'])}。低精度标签为401点/200步PDE；在高精度256组标签CPU预算内，最多生成{d['E5']['design']['low_precision_max_groups']}个低精度组（4096上限）。",'', '| 方法 | 标签 | 训练组数 | 对更细参考的MAE（种子均值与范围） |','|---|---|---:|---:|']
 for r in d['E5']['metrics']:lines.append(f"| {r['method']} | {r['label']} | {r['groups']} | {ag(r['mae'])} |")
 lines+=[f"低精度标签实际使用{f(d['E5']['design']['low_precision_selected_cpu_seconds'])}个CPU秒，占高精度标签工作量上限的{f(d['E5']['low_budget_used_fraction']*100)}%。样本数受预设4096组上限约束，因此结果不代表充分用尽计算预算后的最优分配。E5条件于已经固定的合约池：执行价由主实验的高精度远期债券价格构造，公共合约生成及验证/测试参考工作不计入此处标签预算；完整主实验工作量另外保留。",'']
 lines+=['','E2在1024组固定容量下的配对检验，正数表示误差匹配PDE残差网络更好：','', '| 比较 | MAE差 | 点态95%区间 |','|---|---:|---:|']
 for r in d['E2']['contrasts']:lines.append(f"| {r['contrast']} | {f(r['mean'])} | [{f(r['ci95'][0])}, {f(r['ci95'][1])}] |")
 lines+=['','E5低精度标签方案减高精度256组方案的配对误差差；负数表示低精度方案更好：','', '| 方法 | 比较 | MAE差 | 点态95%区间 |','|---|---|---:|---:|']
 for r in d['E5']['contrasts']:lines.append(f"| {r['method']} | {r['contrast']} | {f(r['mean'])} | [{f(r['ci95'][0])}, {f(r['ci95'][1])}] |")
 lines+=['','E5只检验确定性离散误差，不代表Monte Carlo随机标签噪声。高精度标签预算与训练费用分别保留，不能把更多便宜标签视为免费。','', '## 风险敏感度与监督','', '风险方向为log(a)、sigma、log(r0)、log(rbar)，合约执行价保持固定。前三项加入导数监督，第四项只评价。它们是模型参数敏感度，不能统称股票Delta/Vega。风险训练/测试标签在校内节点生成，验证标签在本机生成；先用三个固定训练样本核对跨环境导数差异不超过1e-5，再保留各自完整收敛检查。风险标签CPU秒只作描述性工作量，不能当作同硬件速度比较。导数参考独立检查空间、时间和差分步长；绝对变化门槛1e-4。','', '| 方法 | 监督方式 | 价格MAE | log(a)导数MAE | sigma导数MAE | log(r0)导数MAE | log(rbar)导数MAE |','|---|---|---:|---:|---:|---:|---:|']
 for r in d['risk']['baselines']:lines.append('| '+r['method']+' | 不训练 | '+f(r['price_mae'])+' | '+' | '.join(f(v)for v in r['risk_mae'])+' |')
 for r in d['risk']['aggregated']:lines.append('| '+r['method']+' | '+r['supervision']+' | '+ag(r['price_mae'])+' | '+' | '.join(ag(v)for v in r['risk_mae'])+' |')
 lines+=['','价格监督减导数监督的配对误差差，正数表示加入导数监督后误差下降。区间仍以参数组为重抽样单位、固定五种子平均，为点态95%区间。不同导数方向单位不同，不可直接横向比大小。','', '| 方法 | 评价量 | MAE差 | 点态95%区间 |','|---|---|---:|---:|']
 for row in d['risk']['contrasts']:
  values=[('价格',row['price_supervision_minus_derivative_supervision_price_error'])]+list(zip(['log(a)','sigma','log(r0)','log(rbar)'],row['derivatives']))
  for name,r in values:lines.append(f"| {row['method']} | {name} | {f(r['mean'])} | [{f(r['ci95'][0])}, {f(r['ci95'][1])}] |")
 lines+=['','残差几何的额外解释能力通过验证集拟合、测试集评价的回归检查；这里预测的是网络的对数绝对误差。形状特征需要参考残差，不能直接用作廉价在线选模信号。','', '| 残差方法 | 不含斜率/曲率的测试R² | 加入斜率/曲率的测试R² | R²增量 |','|---|---:|---:|---:|']
 for g in d['diagnostics']['geometry']:lines.append('| '+g['method']+' | '+ag(g['r2_without_shape'])+' | '+ag(g['r2_with_shape'])+' | '+ag(g['r2_difference'])+' |')
 lines+=['','4096组调参模型的金融约束检查（种子均值与范围；以下数值为比例，非百分数）。容差均为1e-6：负价与债券上界按单份合约计；单调性按同组相邻执行价对计；凸性按相邻割线斜率的下降计。因此各列分母不同，且该表不是完整无套利证明：','', '| 方法 | 负价格 | 超债券价值上界 | 执行价单调性违规 | 凸性违规 |','|---|---:|---:|---:|---:|']
 for g in d['diagnostics']['financial']:lines.append('| '+g['method']+' | '+' | '.join(ag(g[k])for k in ['negative_fraction','bond_bound_fraction','strike_increasing_fraction','convexity_violation_fraction'])+' |')
 e=d['economics'];lines+=['','## 经济含义与无套利诊断','', 'BK的长期平均短端利率是exp(b+sigma²/(4a))，而不是exp(b)。直接改变sigma也会改变利率均值。因此另报告保持长期均值或到期时利率均值的敏感度；这仍不等于保持完整初始收益率曲线。','',f"保持长期均值后，a/sigma方向的导数符号变化比例为{e['stationary_control_sign_change_fraction']}；保持到期均值后的比例为{e['expiry_control_sign_change_fraction']}。这些是模型内合约统计，不是市场因果证据。",'',f"最低5%风险中性到期短端利率区间对看涨价格贡献的占比（只计算价格>1e-6的{e['tail_ratio_contract_count']}份合约）分位数为{e['tail_ratio_quantiles']}；贡献价格的最大网格变化={f(e['tail_grid_change_max'])}。尾部占比与GTFK绝对误差相关系数={e['tail_ratio_vs_gt_error_correlation']}，仅作为探索性关联。尾部辅助积分只作两网格差异检查，未通过独立的严格认证门槛；比例略大于1暴露了数值误差，原值保留且未裁剪，不将此分解当作精确尾部概率或稳健经济结论。",'',f"GTFK独立积分看涨/看跌后的平价缺口MAE={f(e['gt_independent_put_parity_mae'])}，最大值={f(e['gt_independent_put_parity_max'])}。近似转移核未必满足精确半群性质；此项用于检查近似的一致性。独立看跌网络结果保留在risk/put-fits.json，不能用从看涨价格代数推导的看跌值作为检验通过证据。",'', '所有负价格、债券上界、执行价单调性及凸性违规比例见diagnostics.json；未投影修正来隐藏违规。残差几何回归使用参考残差，是解释性诊断，不能作为实盘定价前的廉价特征。']
 lines+=['','独立看跌网络与看涨网络的平价检验（256训练组、128测试组，不强制平价恒等式）：','', '| 方法与种子 | 看跌价格MAE | 平价缺口MAE | 缺口99%分位数 |','|---|---:|---:|---:|']
 for r in d['risk']['put_fits']:lines.append(f"| {r['tag']} | {f(r['put_mae'])} | {f(r['parity_mae'])} | {f(r['parity_q99'])} |")
 lines+=['','下表把各方法的四个原始导数按同一链式法则转换，评价保持利率均值时的误差。这是预设均值控制的探索性方法诊断；变换可能放大原始导数的数值误差，未给出变换后的独立误差上界。','', '| 方法 | 监督 | 固定长期均值：log(a) | 固定长期均值：sigma | 固定到期均值：log(a) | 固定到期均值：sigma |','|---|---|---:|---:|---:|---:|']
 for r in d['risk']['mean_controlled']:
  values=r['stationary_mae']+r['expiry_mae'];lines.append('| '+r['method']+' | '+r['supervision']+' | '+' | '.join(ag(v)if r['seed_count']>1 else f(v['mean'])for v in values)+' |')
 lines+=['','采样范围是数值压力测试，并未校准市场。下表给出模型隐含风险中性利率均值，以百分比计；每格依次为中位数、95分位数、最大值。长期均值与到期时均值同时列出，避免把尚未达到的长期水平当成当前市场利率。','', '| 参数组 | 长期均值（%） | 到期时均值（%） |','|---|---:|---:|']
 for split in ['train','test','ood_vol','ood_expiry']:
  q=d['economics']['risk_neutral_rate_mean_ranges'][split]
  lines.append('| '+split+' | '+', '.join(f(x*100)for x in q['stationary_median_p95_max'])+' | '+', '.join(f(x*100)for x in q['expiry_median_p95_max'])+' |')
 lines+=['', '## 成本与可用性','', '下表在线耗时为串行CPU、预加载模型、预先固定的16组测试合约各重复3次的中位数。网络采用种子11的已选配置，C/D耗时为同一请求分别测得的基线耗时与网络前向耗时之和，未单独计入加法及封装开销；未包含权重加载。','', '']
 lines+=['','风险标签生成的已记录CPU工作量（跨硬件，只作描述，不用于硬件速度排序）：','', '| 划分 | CPU秒 |','|---|---:|']
 for sp,value in d['cost']['risk_derivative_cpu_seconds_by_split'].items():lines.append('| '+sp+' | '+f(value)+' |')
 lines+=['',f"风险与独立看跌网络的45次训练合计CPU秒：{f(d['cost']['risk_training_cpu_seconds'])}。验证集导数只用于数值归档，未用于验证选择；运行环境预检查与中断修复工作另有原始凭证。",'']
 lines+=['','在线定价耗时：','', '| 方法 | 单执行价请求(ms) | 五执行价请求(ms) |','|---|---:|---:|']
 bench=d['cost']['online_benchmark']['samples']
 for m,key in [('A','A'),('B','tuned-B'),('C','tuned-C'),('D','tuned-D'),('Dbase','D_baseline')]:lines.append(f"| {m} | {f(bench['single'][key]['median']*1000)} | {f(bench['surface'][key]['median']*1000)} |")
 lines+=['','网络候选集合和验证停止规则相同，实际训练CPU工作量单独记录。每次训练最多500个epoch；达到上限仍可能限制精度。因此比较结论限定于当前容量、优化器与训练预算。4096组训练候选中达到epoch上限的数量如下：','']
 for r in d['cost']['training_cpu_seconds']:
  if r['budget']==4096:lines.append('- '+r['method']+'：'+str(r['epoch_ceiling_hits'])+'/'+str(r['candidate_count'])+' 个候选达到上限。')
 lines+=['','A/C在线采用积分阶数检查；D使用固定粗网格。本表比较当前实现，不代表各算法最优化实现的速度极限。成功阶段的标签认证、辅助参考、调参训练及重复生成CPU工作量在summary.json单列；失败中断的墙钟和部分记录另存，未完整记录的在途CPU费用不伪造。摊销表不包含研究调试失败成本。摊销计算用累计CPU工作量除串行请求节省时间，不能当作并行机器的实际回本墙钟；也必须同时满足精度需求。','', '| 方法 | 请求类型 | 离线CPU工作秒（含五种子候选调参） | 相对A摊销请求数 |','|---|---|---:|---:|']
 for r in d['cost']['break_even_vs_A']:lines.append(f"| {r['method']} | {r['mode']} | {f(r['offline_cpu_seconds_with_five_seed_tuning'])} | {'无正的逐次时间节省'if r['queries']is None else f(r['queries'])} |")
 lines+=['','## 条件扩展E6','',f"状态：{gate['status']}。启用门槛：{gate['requirements']}。规则：{gate['rule']}。",'', '候选规则仅使用定价前参数和训练分位数阈值。前半验证组选择规则，后半验证组检验；但基础网络超参数用过完整验证集，因此这不是完全独立确认检验。若门槛未通过，不强行提出自适应方法；若通过，域外和测试评估仍按探索性扩展报告。','', '## 结论边界与已有研究','', '残差神经定价已经存在：Funahashi（2021；2024在线发表的后续比较）、Knezevic（2024预印本与相关会议论文）以及Kim/Huh/Yoon（2025）均需作为已有研究对照，不能把路径积分加网络本身包装成新发现。2026年Lee/Huh/Jeong也已比较债券期权的价格、Vega、域外和成本。我们的结果只能回答当前可重复设置里，近似基线、样本预算、导数监督与标签精度怎样影响效果。','', '模型为一因子固定参数BK，未校准真实收益率曲线，未比较DeepONet/PINN/DeepBSDE，未做真实对冲回测。在线计时仅覆盖价格请求，完整Greeks请求的耗时尚未测量。验证集导数作为数值归档保留，网络的验证选择只使用价格；各数据划分的导数生成工作量分别列出。五个种子不足以刻画所有优化随机性；参数采样分布也不是市场频率。数值收敛门槛不是严格解析误差上界；当导数方法间的误差差异小于1e-4参考收敛门槛时，不能仅凭该排序声称已分辨出优势，须另做更高精度核验。尚未取得的出版全文和未经复核的理论条件在文献审计中明确列出。','', '相关原始来源：', '', '- [Funahashi（2021）](https://doi.org/10.1080/14697688.2020.1812702)', '- [Funahashi 后续比较](https://link.springer.com/article/10.1007/s10479-024-06114-1)', '- [Knezevic 预印本](https://arxiv.org/abs/2404.08903)', '- [Kim、Huh 与 Yoon（2025）](https://doi.org/10.1016/j.camwa.2025.03.029)', '- [Lee、Huh 与 Jeong（2026）](https://www.aimspress.com/article/doi/10.3934/math.2026242)', '- [Stedman 与 Capriotti 的 GTFK 方法](https://arxiv.org/html/2408.02064v1)', '', '## 证据入口','']
 lines+=['','原始事前协议与运行中的数值修订分开保留。修订包括独立细化空间/时间网格、扩大差分步长细化次数、运行环境一致性检查和并行执行；样本、方法臂、种子、精度门槛及验证选择规则未放宽。后续数值修订标记为执行期记录。','']
 for label,path in [('原始冻结协议','formal-protocol-v2/protocol.md'),('风险数值修复','risk-repair-refinement-note.txt'),('更细参考修订','reference-refinement-amendment.txt'),('本机运行环境检查','risk-local-runtime-addendum.txt'),('风险训练执行安排','risk-training-execution-note.txt')]:lines.append('- ['+label+']('+str(root/'outputs'/path)+')')
 if c.get('figures'):
  figures=root/'outputs'/c['figures']
  lines+=['','图中的种子范围不是统计置信区间；完整图注与数据来源见图表目录中的captions.txt。','']
  for name,title in [('price-learning-curves-tuned','验证集调参后的学习曲线'),('price-learning-curves-fixed_capacity','固定容量学习曲线'),('accuracy-latency','准确度与完整定价成本'),('risk-supervision','风险导数监督与数值基准')]:
   assert (figures/(name+'.png')).exists()
   lines.append('!['+title+']('+str(figures/(name+'.png'))+')')
   lines.append('')
 for label,stage,name in [('完整统计',c['synthesis'],'summary.json'),('完整性审计',c['audit'],'audit.json'),('几何与金融约束诊断',c['diagnostics'],'diagnostics.json'),('E6门槛与结果',c['adaptive'],'gate.json')]:lines.append(f"- [{label}]({root/'outputs'/stage/'results'/name})")
 lines+=['','可复核的原始产物（大型文件单独保留）：','']
 for label,relative in [('主实验数据','formal-main-v1/results/data-all.npz'),('主实验模型权重','formal-main-v1/results/models.tar.gz'),('主实验完整训练记录','formal-main-v1/results/fits.jsonl'),('风险训练记录','risk-followup-v3/results/fits.json'),('独立看跌训练记录','risk-followup-v3/results/put-fits.json'),('基线与标签精度训练记录','baseline-precision-v2/results/fits.json')]:lines.append('- ['+label+']('+str(root/'outputs'/relative)+')')
 (out/'report.md').write_text('\n'.join(lines)+'\n');(out/'checksums.sha256').write_text(hashlib.sha256((out/'report.md').read_bytes()).hexdigest()+'  report.md\n')
if __name__=='__main__':main()
