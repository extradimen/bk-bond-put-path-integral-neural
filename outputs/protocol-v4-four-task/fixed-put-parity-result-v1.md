# F-E 欧式看跌平价核验结果 v1

冻结的训练/验证 6 组、每组 3 个执行价共 18 例全部通过。节点 OS 子进程等待状态为 0，结果按 SHA-256 校验返回。最大 `C - Z(0,T) + K Z(0,e) - P_direct` 绝对差为 `4.479056014972116e-15`；两档网格的平价隐含看跌价格最大差为 `1.3768721374152193e-7`。

注意证据边界：看涨、直接看跌、债券和贴现因子在本实验共享同一 PDE 传播器，正式 F-E 标签也由此传播器在细档网格计算，因此与正式标签的近机器精度一致是预期的代数关系，并非外部独立复现。它能排查符号、执行价、日期及 payoff 拼接等实现错误；对 PDE 本身的独立数值检查仍依赖先前 OU 高斯传播加贴现分裂实验。欧式平价不用于 Bermudan 提前行权价格。

数值账本：[summary.json](../../outputs/fixed-put-parity-check-v1/results/summary.json)、[checks.json](../../outputs/fixed-put-parity-check-v1/results/checks.json)。
