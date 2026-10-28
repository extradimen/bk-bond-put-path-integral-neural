# A 与粗 PDE 的真实行权边界探索性试跑 v2：部署补记

v1 使用已冻结四组、数值设置及同项目物料/环境，materialize 和 environment-build 均完成，但项目部署器在写入全局 `projects.json.lock` 前遇到本机沙箱 PermissionError；未执行 preflight 或 launch，无实验子进程、无结果。失败收据与不可变快照全部保留。已核查本项目全局活动租约为空。v2 只修正部署权限，沿用 `put-method-boundary-pilot-v1.md` 的科学冻结、`configs/put-method-boundary-pilot-v1.json` 的样本与门槛及同一计算脚本，不读 v1 的任何结果作选择；总量仍为 4/4 格-组。v2 的独立不可变部署与收据完整归档。
