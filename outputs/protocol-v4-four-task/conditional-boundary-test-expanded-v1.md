# 扩大状态条件模型的独立留出边界测试冻结

依 `conditional-boundary-expanded-design-v1.md` 预先确定 F-B/T-B 各 test 组号 128–191，共 128 格-组、768 条日期曲线。三执行价、前两个行权日期和所有参考/方法门槛不变；不混入曾用于小样本比较的 test 32–47。细 PDE 3201/400/1.0 对独立 OU 3201/400/1.0/24 的逐曲线资格为价值最大差不超过 1e-4、根拓扑一致且根短利率差不超过 1e-4。B/C/D 的 513 状态继续持有价值 MAE 门槛为 0.002，根数必须一致，根短利率差不超过 0.001；全部不合格曲线保留在固定分母中。

模型仅从 `conditional-boundary-fit-expanded-resume-v1` 的 72 项训练/验证候选中按事前最小验证 MAE 规则选择。该运行的 OS child wait=0、顶层结果与 72 个模型均同项目 SHA-256 校验回传。选模 JSON SHA `766bc7c561261b05fd95611f923d67509c4720a618e2fba633717a046307a8bb`，六个选中模型的独立 SHA 固定于 `configs/conditional-boundary-test-expanded-v1.json`。T-B 的 B 验证 MAE=0.002391 未达 0.002，仍按原规则进入测试并如实报告失败。

测试仍属追加探索性边界研究，不改变四格主研究，也不把已知七坐标导数反例修饰成通过。所有证据运行须项目部署器、不可变快照、同项目物料/环境、全局 resources/preflight/experimentctl launch、节点 OS wait 和 SHA 校验回传。
