# v8 时变看跌独立 OU 参考核验结果

2026-10-23。按事前冻结的 44 个 T-E/T-B 合约单元，精确 OU 转移加 Strang 折现分裂两档全部通过原 1e-6 门槛，失败 0。细档与 PDE 标签最大绝对差 6.077783952229687e-7，两档价格最大变化 3.354355214944815e-7；各划分均通过。节点 OS child wait return_code=0，结果经同项目 SHA-256 校验回传。原始逐案数据、summary、node-status 与 return-receipt 位于 `outputs/timevarying-put-independent-check-v8/`。这支持所抽查区域的数值参考资格，不把 PDE 称为解析真值或声称所有 8192 组经独立 OU 重算。
