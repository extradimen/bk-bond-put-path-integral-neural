# 扩大条件边界拟合：节点重启后的追加续算

原 `conditional-boundary-fit-expanded-v1` 在 campus-3090-2 节点重启前写入 54/72 条拟合账本及 54 个对应模型，未生成完成汇总；没有 OS 子进程 wait，退出码未知。原运行、原配置和失败事实均保留。控制器已核查较新 boot ID、原 worker/child PID 均消失，并把 55 个文件打包为同项目 SHA-256 归档，经 materialize 校验回 Mac 后才解决原租约。归档 SHA-256 为 `c7984823ef660c55e7b9dccdafb7f4f44c6952fe90a071463ad2e60000eb472b`。

续算配置绑定原训练/验证归档及该中断归档。原 72 候选顺序、参数、种子、预算、验证选模和 0.002 目标不变。先核对归档中 54 条记录恰为原候选前缀且每条有对应可读模型，再原样复制这 54 个模型，仅拟合剩余 18 项；合并 72 项后按原规则选择每格每方法的验证最优模型。新测试分组 128–191 及数值门槛保持 `conditional-boundary-expanded-design-v1.md` 不变，不在续算阶段读取 test。

续算仍须经项目部署器、不可变快照、同项目 SHA-256 物料与环境、全局 resources/preflight/experimentctl launch、节点 OS wait 和校验回传。原中断的 54 项属于恢复证据，不把原运行改记为成功。
