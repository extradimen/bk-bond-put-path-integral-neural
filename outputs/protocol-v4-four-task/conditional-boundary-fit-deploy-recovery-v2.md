# 条件模型拟合部署 v2：登记权限恢复

`conditional-boundary-fit-v1` 项目部署器已完成源快照、同项目物料和环境构建，但在写全局 `projects.json.lock` 时遇到本地沙箱 `PermissionError`；未进入 resources/preflight/experimentctl launch，也没有模型拟合结果或活动租约。v1 输出及错误保留。

v2 仅重试部署与启动，拟合代码、训练/验证数据 SHA-256、候选 24 项、选择规则、精度目标均沿用 `conditional-boundary-fit-v1.md`，不修改科学门槛。必须先获得全局项目登记写入权限，之后按项目部署器完成不可变快照、物料/环境收据、resources/preflight/launch、节点 OS wait 与校验回传。
