# 扩大状态条件标签的修复 v1：启动前冻结

原 conditional-boundary-trainval-v2 经 campus-3090-2 原 PID 身份、OS child wait 0 和同项目 SHA-256 回传完成 320/320 组，其中 304 组通过、16 组不满足原 1e-4 PDE/独立 OU 标签资格，最大差 0.0011619165。原数据 SHA-256 为 35c94221a63ad8ac2ea59c863e46fe6f44e77fc0160141132309d191a2ff9f9b；完整原失败账本另以 SHA-256 锁定。原失败及门槛保留。

按照 v2 结束前写定的 conditional-boundary-repair-rule-v1.md，精确重算账本中全部 16 个失败格-划分-组：F-B train 106；T-B train 5、6、15、29、32、57、62、79、82、106、109、113；T-B val 3、9、23。首档参考 PDE 1601/200/1.0，若独立 OU 3201/400/1.0/24 阶差仍 >1e-4，才试 3201/400/1.0。两档都失败则停止合并与拟合；通过组沿用原归档，不接触 test。新数据归档与原归档并存，后续拟合须新 SHA-256 冻结。

本阶段所有证据通过项目部署器、不可变快照、同项目 SHA-256 物料及环境收据、全局 resources/preflight/experimentctl launch、节点 OS wait 和校验回传。
