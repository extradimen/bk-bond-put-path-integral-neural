# 时变正式数据部署修订 v2

2026-10-18。`timevarying-put-formal-data-v1` 已通过全局控制器启动，但节点 OS child wait return_code=1；节点 stderr 明确显示 `campus-3090` 的 CPU affinity 只有 12，低于已冻结的 24 工作者，程序在生成样本前退出。失败快照、日志、节点退出和校验回传保留，不能当作正式数据。

本修订仅将正式数据节点从 `campus-3090` 改为已检查 CPU affinity 为 32、可用内存约 60 GiB 的 `campus-cpu`。仍固定 24 单线程工作者、48 小时预算；正式抽样的五个划分、种子、合约、数值门槛、加密档、失败规则及 24 项四格主要比较均沿用 `timevarying-put-formal-freeze.md`，不因这次计算前失败而变动。v2 必须使用新的不可变源快照、同项目物料与环境收据和全局预检/启动。若该节点的项目物料或依赖直接获取失败，遵循本项目新的 Mac 或 Silicon 路由选择规则，不擅自下载。
