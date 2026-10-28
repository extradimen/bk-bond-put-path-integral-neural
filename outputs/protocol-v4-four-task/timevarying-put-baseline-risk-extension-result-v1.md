# 时变看跌 A/Dbase 风险导数扩展 v1：结果

冻结 T-E/T-B 各 8 个新测试组，合计 16/16 格-组完成。运行 `20261024T055454Z__1627c004__timevarying-put-baseline-risk-extension-v1` 于 campus-3090-2，节点 OS child wait return_code=0，同项目 SHA-256 校验回传；原始逐组结果为 `outputs/timevarying-put-baseline-risk-extension-v1/results/pilot.jsonl`（SHA-256 `8bb3b9cd91e230f08385572631f404ef57e2542160d063f317bf0d58d981fbb7`）。

| 方法/格 | 最大步长差 | 最大网格分辨率差 | 最大相对独立参考绝对差 |
|---|---:|---:|---:|
| A / T-E | 5.0553e-5 (40, sigma1) | 3.4834e-5 (40, sigma2) | 1.1456e-4 (120, sigma1) |
| A / T-B | 7.9136e-6 (40, log(r0)) | 7.0630e-6 (40, sigma2) | 3.2168e-3 (120, sigma1) |
| Dbase / T-E | 1.5443e-4 (12, log(rbar2)) | 1.7890e-3 (40, sigma1) | 2.3881e-3 (40, sigma1) |
| Dbase / T-B | 3.2374e-4 (40, log(r0)) | 2.8265e-4 (40, log(r0)) | 5.4494e-4 (40, log(r0)) |

全部记录为有限值。粗 PDE 基线的导数数值稳定门槛仍未通过；A/T-B 组 120 的 sigma1 与独立 PDE 参考也有较大偏差，即使自身两档变化较小，不能用两档稳定性宣称准确。旧失败和本轮异常均保留，后续 C/D 比较仅是这些组上的探索性诊断，不是全分布导数认证。
