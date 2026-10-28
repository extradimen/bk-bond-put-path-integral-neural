# 扩大状态条件拟合 v1：启动前冻结

原 320/320 标签组中 304 组直接通过，16 组按追加数值规则重算后全部通过原 1e-4 独立资格；修复后归档 SHA-256 b6719b3222c6c834f69371d1d0bee2b6b479b84d0e4695d8a8308263b96866ad。修复阶段原 PID 与 OS child wait 0 匹配、同项目 SHA-256 校验回传。归档含 F-B/T-B 各 128 train、32 val 组，无 test 键；逐数组长度一致且数值有限。

按拟合前冻结的 conditional-boundary-expanded-design-v1.md，B/C/D 每格同试宽度 64/128/256、隐藏层 2/3、随机种子 11/29、学习率 0.001，共 72 拟合。每项最多 500 epoch、批量 256、早停 patience 40；按验证继续持有价值 MAE 选择，目标仍 <=0.002。任何验证失败照实保留，不修改原小样本测试或门槛，不读取 test。本阶段证据通过项目部署器、全局 resources/preflight/experimentctl launch、不可变快照、同项目物料/环境收据、节点 OS wait 和校验回传。
