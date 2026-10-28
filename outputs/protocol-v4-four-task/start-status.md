# 四格定价比较：启动记录（2026-10-18）

协议：protocol.md。原固定参数欧式看涨结果保持封存；本轮四格主任务统一为零息债看跌。

P3a 看涨试跑 v1 因过紧的单调不等式检查失败，节点 OS wait return_code=1；v2 保留完整结果。其百慕大价格与欧式价格几乎相等，说明看涨合约不适合作为提前行权难度测试。该结果促成追加 v4 协议，不改写先前快照。

P3a 看跌试跑（p3a-bermudan-put-v1）OS wait return_code=0、校验回传。代表参数下 801 点网格的欧式/百慕大价格：中等波动 0.004643904 / 0.067328634；高波动 0.037301243 / 0.109880480。两例均有明显提前行权价值。201/401/801 网格仅是初步趋稳证据，不是完整空间、时间和截断域独立认证。

P3b GTFK 条件传播两轮试跑均 OS wait return_code=0、校验回传。中等波动百慕大价格在加密设置下约 0.067329919，高波动约 0.109764551；高波动最新两档仍差 5.63e-6，尚未满足正式精度门槛。此处不可解释为 A 与 PDE 的正式误差排名。下一关必须检验 GTFK 核的积分、截断和多次传播一致性，PDE 独立认证，并冻结新看跌格的样本与预算；之后才能训练 B/C/D。

本轮无网络训练、无时变模型运行、无四格总体结论。部署记录和原始数值分别见各 stage 目录的 deployment.json、node-status.json、results/results.json；失败运行保留在原 stage。

2026-10-18 追加：P3b 的独立核审计与折点分段积分试跑已完成，详细见 p3b-audit-note.md。高波动 GTFK 直接债券与分段传播的约 8e-5 组合缺口在加密设置中稳定；因此不能把加密积分视为完全解决 A 的多次行权误差。新四格正式比较继续等待 P3b 方法验证。

2026-10-18 继续：独立欧式 GTFK 交叉核验确认直接积分稳定；百慕大高波动价格在固定积分阶数、状态网格 601→801 时仍变化约 5.71e-6。P3b 门槛未过，详情见 p3b-audit-note.md。部署器已改为自动预检选定节点后从同一 SHA 源快照启动，本机/远端不再因调度选择执行不同的可变源文件。

2026-10-18 继续：GTFK 状态域扫描解释了大部分百慕大网格跳动；PDE 参考单独扫描空间、时间和域后，中等波动约稳定到 10^-7，但高波动仍有约 10^-6 的变化。两项运行均保有节点 OS child wait 与 SHA-256 回传证据，详情见 p3b-audit-note.md。参考解仍需继续认证，不能启动正式看跌格训练或声称五种方法排名。

2026-10-18 继续：独立 OU 高斯传播加贴现分裂交叉核验通过，百慕大值与 PDE 处于数个 10^-7 至 10^-6 的一致范围；高波动欧式折点误差仍需处理。运行记录和数值见 p3b-split-crosscheck-v1，详细解释见 p3b-audit-note.md。

2026-10-18 继续：PDE 细网格复核后，两组代表案例的欧式/百慕大看跌参考在独立空间、时间、域扫描下约稳至 1e-7。GTFK 扩域和加密阶段 p3b-gtfk-domain-v2 已通过控制器启动，最近节点状态为同一子进程仍在运行；不得重复启动。正式样本与训练继续等待该数值门槛及额外验证。

2026-10-18 继续：p3b-gtfk-domain-v2 已完成并校验回传。代表案例下 GTFK 百慕大数值网格/域误差低于 1e-6；其高波动价格约比细 PDE 低 1.18e-4，应归为方法近似误差。P3b 的代表数值门槛已有证据，但正式样本、预算、主比较与逐例参考质量规则尚未冻结；新看跌格仍无网络训练。

2026-10-18 继续：四个额外 P3b 合约试跑完成并校验回传；价格界与提前行权检查全部通过，GTFK 数值范围小于 5e-7，但方法误差随区域从约 1e-6 变至 3.3e-4。较长期高波动参考仍需加密。详情见 p3b-audit-note.md 与 p3b-support-suite-v1。

2026-10-18 继续：F-B 数据生成前 16 组/48 合约计时与质量试跑完成，全部通过 1e-6 数值门槛；四进程墙钟约 371 秒。此为预算与失败率试探，不属于正式数据或方法排名。下一步按实测成本冻结新看跌格样本、预算、主比较及逐例质量/失败规则，再启动正式数据与训练。

2026-10-18 继续：F-E/F-B 常参数两格的正式抽样、预算、数值门槛、12 项主要成对比较与 Holm 校正规则已事前冻结在 fixed-put-formal-freeze.md。额外高波动、长合约各 4 组的域外试跑均完成并通过数值门槛。下一步启动新的正式数据阶段；试跑数据不会并入正式划分。

2026-10-18 继续：`fixed-put-formal-data-v1` 已按冻结协议经项目部署器及全局 controller 启动于 campus-3090-2 的不可变源快照（run_id `20261017T192814Z__1627c004__fixed-put-formal-data-v1`）。最近节点状态显示 PID 身份、命令、工作目录匹配且子进程仍在运行；不得重复启动。正式数据尚未完成、无训练、无新看跌格方法排名。若数值门槛失败，完整原始组和失败原因保留，停在数据门槛。

2026-10-18 继续：P3c 时变欧式看跌的分段 PDE、独立 OU 分裂传播及分段 GTFK 核合成已实现并通过普通恒定参数/零波动单元测试。预检 v1 的执行价 0.95 使价格近于零，不具鉴别力，原始结果保留。修订 v2 执行价为 0.98，两例均产生非零价格；201 点/低阶 GTFK 约有 0.008 的异常大误差，401 点/较高积分阶数下缩至约 1e-5。两轮均经节点 OS wait 与 SHA-256 回传；这只是数值探索，必须进一步分离状态网格、积分阶数、时间步及域误差，不能将其视为时变格方法排名或正式精度通过。

2026-10-18 继续：P3c v3 在同一合约上分别变动 GTFK 积分阶数与状态网格。固定 401 点时，积分阶数 16→24→32→48 的常参数欧式误差约 8.83e-3→1.75e-5→3.31e-7→3.41e-7；时变合约约 8.16e-3→1.16e-5→2.52e-7→2.43e-7。固定阶数 24 时，201→401→801 点几乎不改变约 1e-5 的误差。因此此前异常主要是积分阶数不足，不是状态网格。v3 已 OS wait 与 SHA-256 回传；PDE 时间/空间/截断域及独立分裂传播仍需认证，不能宣称 P3c 已通过。

2026-10-18 继续：P3c `p3c-reference-certify-v1` 用预设 1e-6 门槛完成代表常参数与两段时变欧式看跌参考的空间、时间、截断域独立细化及 OU 分裂传播交叉核验。常参数四项最大差 2.44e-8，时变最大差 1.21e-7；节点 OS wait return_code=0、SHA-256 校验回传。代表参考数值门槛通过，但正式时变抽样规则、预算、逐例质量与 GTFK 误差前沿尚未冻结，不能启动 T-E 正式训练或声称总体方法排名。

2026-10-18 继续：P3d 时变参数加三次行权的 PDE、独立 OU 分裂传播及分段 GTFK 递推已实现，恒定参数及单次行权退化单元测试通过。`p3d-joint-pilot-v1` 代表合约两档设置的百慕大价格约 0.0199653/0.0199655，欧式约 0.0007111/0.0007117，明确存在提前行权价值；细档 PDE 与独立传播/GTFK 的差分别约 9.72e-8/6.12e-8。节点 OS wait return_code=0、SHA-256 校验回传。此为代表试跑，联合格仍需独立空间/时间/域认证及正式抽样预算冻结。

2026-10-18 继续：`p3d-reference-certify-v1` 对同一联合合约的欧式及百慕大看跌价格分别做空间、时间、截断域细化和独立 OU 分裂传播复核；最大差依次约 6.54e-8、6.83e-8、2.53e-9、1.21e-7，均低于预设 1e-6，价格界与行权机会单调性通过。节点 OS wait return_code=0、SHA-256 校验回传。此代表参考数值门槛通过，正式 T-B 的样本、预算与逐例质量规则仍待冻结。

2026-10-18 继续：T-E/T-B 时变两格已建立共同参数组与三档执行价的小样本质量/计时试跑 `timevarying-data-timing-v1`（8 组、4 工作者），经不可变快照、项目物料/环境收据及全局控制器启动于 campus-3090。最近节点状态为同一子进程仍在运行，不得重启；该试跑仅用于冻结正式规则与预算，未产生正式样本。

2026-10-18 继续：`timevarying-data-timing-v1` 已经节点 OS wait return_code=0、SHA-256 校验回传。8 组中 5 组通过逐约 1e-6 参考数值门槛，3 组空间网格差最高 4.43e-6，故不能冻结正式规则。加密 PDE 网格及 GTFK 积分后，独立新快照 `timevarying-data-timing-v2` 已完成同样的 OS wait 与校验回传：8 组中 7 组通过，唯一失败组参考最大差 1.00684e-6；GTFK 两档最大变化 1.14474e-6。v2 仍不满足门槛，失败保留。再次加密的 `timevarying-data-timing-v3` 已准备，正式 T-E/T-B 数据与训练继续等待其结果及事前冻结。

2026-10-18 继续：`timevarying-data-timing-v3` 已经节点 OS wait return_code=0、SHA-256 校验回传。同一 8 组全部通过；48 个合约中参考独立轴细化的最大差 7.97197e-7，GTFK 两档变化最大 6.86258e-7，四工作者墙钟 93.98 秒。这个小样本不足以估计正式 8192 组的失败率，另用不同随机种子、32 组、8 工作者的 `timevarying-data-timing-v4` 检验稳健性和成本，仍不并入正式数据。固定参数正式数据阶段在 campus-3090-2 保持原进程，最新只读 train 账本 1223 组；没有重启。

2026-10-18 继续：`timevarying-data-timing-v4` 已有节点 OS wait return_code=0 及 SHA-256 校验回传。不同种子的 32 组仅 28 组通过参考数值门槛；失败组 8、26、28、31。最大参考独立轴差约 1.00848e-4，主要来自扩大截断域；GTFK 两档最大变化约 3.14874e-6。当前统一以第一时段模型构造状态域，未充分覆盖部分第二时段高波动/低回复速度合约，不能把 v3 的 8 组成功外推为正式质量保证。已准备只针对这四个失败组的预冻结域扫描 `timevarying-domain-diagnose-v1`，所有失败数据保留，时变正式样本/训练继续暂停。

2026-10-18 继续：`timevarying-domain-diagnose-v1` 经全局控制器、节点 OS wait return_code=0 和 SHA-256 校验回传。四个失败组的中档执行价均在以第一时段域宽的 3 倍与 4 倍、保持近似相同空间步长时趋稳：最严重的组 28 在宽 1.5→2.0 倍时变约 1.0e-4，而 3.0→4.0 倍时变化约 1e-12，4.0 倍的空间再加密差约 3e-9。证据指向状态域选取不足，不是必须改变经济合约或提高参考容忍度。下一步应基于整条时变曲线构造域并独立加密认证，再以不同样本试跑；暂不冻结 T-E/T-B 正式数据。

2026-10-18 继续：已实现随整条分段 OU 时变曲线均值、方差构造状态域的数值试跑版本；仍保留第一时段原域下界，逐段以精确 OU 矩传播，域宽至少覆盖均值偏移加七个标准差及 0.5 缓冲。新 `timevarying-data-timing-v5` 将对先前相同 32 组进行空间/时间/域独立细化与 GTFK 两档检查；这是检验失败组修复的预冻结试跑，不能并入正式数据或充当新随机样本外验证。

2026-10-18 继续：`timevarying-data-timing-v5` 经节点 OS wait return_code=0 和 SHA-256 校验回传。修复域后，先前同一 32 组全部通过参考独立轴 1e-6 门槛，最大差 4.22731e-7；GTFK 两档最大变化 8.36769e-7，8 工作者墙钟 288.13 秒。修复样本已有事后选择风险，故另以未用于开发的种子 20261034 做 32 组 `timevarying-data-timing-v6`，仍属预冻结质量/成本试跑，不进入正式训练或测试。

2026-10-18 继续：新种子 `timevarying-data-timing-v6` 已有节点 OS wait return_code=0 及 SHA-256 校验回传。32 组全部通过 PDE 参考空间/时间/域 1e-6 门槛，最大差 6.39935e-7，8 工作者墙钟 300.75 秒。但组 5 最低执行价的 GTFK 百慕大两档结果差 2.18940e-6（欧式差 1.01288e-6），超过预定数值门槛；不能把它当成 GTFK 近似方法误差。已准备 `timevarying-gtfk-diagnose-v1` 对该组分别扫描积分阶数、状态网格及域，正式 T-E/T-B 数据继续等待数值规则冻结。

2026-10-18 继续：`timevarying-gtfk-diagnose-v1` 已经节点 OS wait return_code=0、SHA-256 校验回传。在该难合约上，固定 2401 点时积分阶数 64→128 的百慕大价格变化仅约 4.9e-8，而固定 128 阶时状态网格 2401→3201 变化约 1.10e-6；3201 点原域与等步长扩域价格几乎完全一致。因此当前主导因素是 GTFK 状态网格而非积分阶数或截断域。追加 `timevarying-gtfk-diagnose-v2` 扫描 3201/4801/6401 点及更高阶数，正式时变格仍未冻结。

2026-10-18 继续：`timevarying-gtfk-diagnose-v2` 已经节点 OS wait return_code=0、SHA-256 校验回传。难合约最低执行价下，GTFK 百慕大 3201→4801 点差 2.76756e-7，4801→6401 点差 1.67443e-7；6401 点 128→160 阶差 3.48e-9，等步长扩域结果一致。欧式对应网格差最大 3.53490e-7。候选正式配置可采用 3201/4801 点、128 阶，并逐约检查 1e-6，超标时预设加密到 6401 点；这尚需域外质量和成本试跑。已准备高波动 OOD 小样本 `timevarying-data-timing-v7`，正式 T-E/T-B 仍未冻结或训练。

2026-10-18 继续：高波动域外 `timevarying-data-timing-v7` 经节点 OS wait return_code=0、SHA-256 校验回传。8 组全部通过 PDE 与 GTFK 逐约 1e-6 数值门槛，最大参考轴差 5.63916e-7，GTFK 两档最大差 1.45575e-7；4 工作者墙钟 693.53 秒。此成本明显高于主域，正式时变数据预算须覆盖域外尾部。长合约域外 `timevarying-data-timing-v8` 已准备，正式 T-E/T-B 继续等待其质量与计时结果。

2026-10-18 继续：长合约域外 `timevarying-data-timing-v8` 经节点 OS child wait return_code=0 和 SHA-256 校验回传。8 组全部通过逐约 PDE 与 GTFK 1e-6 数值门槛；最大参考独立轴差 2.66509e-7、GTFK 两档差 8.38982e-8；4 工作者墙钟 731.51 秒。高波动及长合约小样本均过关，但不能据此推断 512 组域外正式集零失败；正式逐约停机规则与加密档仍须事前冻结。固定参数正式数据原进程仍运行，未重启。

2026-10-18 继续：预先选定主域、域外高波动、域外长合约各一组中档执行价，分别核对 T-E/T-B 共 6 例的独立 OU 高斯传播加贴现分裂与细 PDE 参考。`timevarying-independent-check-v1` 由不可变快照经全局控制器启动，节点 OS child wait return_code=0，结果 SHA-256 校验回传；六例两档分裂细化差及细档对 PDE 差均≤1e-6，最大细档对 PDE 差 7.46372e-7。该预冻结独立交叉核验通过；正式数据仍须事前冻结抽样、逐例门槛、成本和失败规则。

2026-10-18 继续：T-E/T-B 正式抽样、逐约 PDE/GTFK 数值门槛、预算、主比较已事前冻结于 `timevarying-put-formal-freeze.md`。初次部署 `timevarying-put-formal-data-v1` 在任何组生成前因 `campus-3090` CPU affinity 12 < 冻结的 24 工作者而失败；节点 OS child wait return_code=1、失败物料校验回传，stderr 与快照保留。仅修订部署节点的 v2 选择 CPU affinity 32 的 `campus-cpu`，样本/预算/科学规则均不变；同项目物料已完成，但该节点直接安装依赖失败，控制器要求本项目新的 Mac 或 Silicon 路由选择。尚未启动 v2，绝不擅自下载或借用其他项目的中转授权。

2026-10-18 继续：用户为 v3 明确选择本次 Mac 依赖中转；该节点在环境创建时又因缺少 `python3.12-venv/ensurepip` 失败，未启动正式计算。v4 转向 48 核的 `campus-3090-2`，环境已构建，但全局 preflight 因节点两个活动 compute 租约达到并发上限而拒绝，未启动。所有失败和拒绝记录保留。v5 仅将工作者修订为 `campus-3090` 可用的 12 核，墙钟上限按相同总 CPU 预算增为 96 小时，正式样本与科学规则不变；已通过不可变快照、物料/环境收据及全局 preflight/launch 启动（run_id `20261018T014237Z__1627c004__timevarying-put-formal-data-v5`）。节点子进程 PID 970726、工作目录与命令身份匹配，目前运行中；不得重复启动。固定参数正式数据在另一节点继续原进程。

2026-10-18 继续：固定参数正式数据 `fixed-put-formal-data-v1` 节点 OS child wait return_code=0、结果 SHA-256 校验回传。完整 4096 组训练划分中 1 组（3451）最低执行价 F-B 的 GTFK 数值门槛未过：预设 1601→2401 状态点与域交叉复核差为 1.0146178e-6，较 1e-6 门槛高约 1.46e-8；PDE 参考两格认证及其余价格检查通过。程序按冻结规则在训练划分后停机，没有生成可训练完整快照或验证/测试/域外数据，不能训练或声称方法排名。已保留整份失败账本、失败清单与旧源快照；只针对该合约的 GTFK 3201/4801 点及域扫描新阶段 `fixed-put-gtfk-failure-diagnose-v1` 已经全局控制器启动，最近 OS 身份核查仍运行中，绝不重复启动。时变正式数据在独立节点维持原进程。

2026-10-18 继续：`fixed-put-gtfk-failure-diagnose-v1` 节点 OS wait return_code=0、SHA-256 校验回传，3201→4801 点与域宽交叉差均低于原 1e-6 门槛。已在任何新验证/测试标签生成前追加冻结 `fixed-put-formal-recovery-v2.md`：只修复旧训练账本第 3451 组最低执行价的 GTFK 网格，旧 4095 组原样复用；未来划分使用新种子和统一按需加密规则。`fixed-put-formal-recovery-v2` 已经项目部署器、同项目物料/环境收据及全局 preflight/launch 在 campus-3090-2 启动（run_id `20261018T070652Z__1627c004__fixed-put-formal-recovery-v2`）；节点 worker PID 2792720、child PID 2792721 的命令、工作目录、启动 ticks 和 boot ID 均匹配，当前运行中，不能重启或视作完成。时变 v5 在 campus-3090 保持原进程运行。
2026-10-19 继续：固定参数正式恢复数据 `fixed-put-formal-recovery-v2` 节点 OS child wait return_code=0、SHA-256 校验回传；8192 组完整，数值门槛失败 0，数据包 SHA-256 `f43b1488a839ebebe6c8300dedda7c050371bb3d0d6349928e8ebce3a3d100c9`。事前选定的 44 个 F-E/F-B 独立 OU 分裂参考交叉核验已按 `fixed-put-independent-check-v1.md` 冻结，并经项目部署器、同项目物料/环境收据及全局 preflight/launch 在 `campus-3090-2` 启动，run_id `20261018T174018Z__1627c004__fixed-put-independent-check-v1`。核验通过前不训练固定参数网络；时变正式数据原进程保持运行。
2026-10-19 继续：固定参数独立交叉核验 `fixed-put-independent-check-v1` 节点 OS child wait return_code=0、SHA-256 校验回传，但事前冻结 44 例中 1 例未过 1e-6：`ood_vol` 组 0、最低执行价 F-E 的细档独立 OU 分裂值与 PDE 参考差 `1.0620111079231997e-6`，其两档变化 `-2.761814574536725e-7`。原失败保留，域外高波动参考资格暂停，尚不训练固定参数网络。追加冻结仅六例的细网格诊断 `fixed-put-independent-diagnose-v2.md`，经项目部署器和全局控制器在 `campus-3090-2` 启动，run_id `20261018T175452Z__1627c004__fixed-put-independent-diagnose-v2`；时变数据任务仍运行。
2026-10-19 继续：`fixed-put-independent-diagnose-v2` 节点 OS child wait return_code=0、SHA-256 校验回传；六例全部通过原 1e-6 门槛，先前超标的 F-E 低执行价细档对 PDE 差降至 `5.165737412722582e-7`、两档变化 `-5.454373666509416e-7`，原 v1 失败仍保留。固定参数 F-E/F-B 的 720 项 B/C/D 候选训练已在读取测试误差前冻结 `fixed-put-fit-v1.md`，只用 SHA 固定的 train/val 数据，通过项目部署器、同项目物料/环境及全局 preflight/launch 在 `campus-3090-2` 启动，run_id `20261018T181011Z__1627c004__fixed-put-fit-v1`；节点 PID 2888468/2888469 身份和 boot ID 匹配，现运行中。时变数据原任务继续运行。
2026-10-19 继续：固定参数网络 `fixed-put-fit-v1` 节点 OS child wait return_code=0、SHA-256 校验回传；720 项候选、180 个验证选择/固定容量记录完整，训练墙钟 660.28 秒、拟合 CPU 时间和 14985.83 秒。固定参数正式盲测在读取测试误差前冻结 `fixed-put-evaluate-v1.md`，以 SHA 固定的完整数据、选择记录和模型归档，经项目部署器及全局控制器在 `campus-3090-2` 启动，run_id `20261018T182515Z__1627c004__fixed-put-evaluate-v1`；节点 worker PID 2892140、child PID 2892141 身份匹配，现运行中。时变数据任务保持原进程。
2026-10-19 继续：固定参数正式盲测 `fixed-put-evaluate-v1` 节点 OS child wait return_code=0、SHA-256 校验回传；2048 个测试组、两类 512 组域外划分、12 项局部主对比已输出。五种子 4096 组验证选择模型的测试价格 MAE：F-E A `2.6737e-6`、B `1.6746e-4`、C `2.5473e-7`、Dbase `3.0748e-6`、D `1.9907e-6`；F-B A `3.2431e-5`、B `3.9203e-4`、C `2.1723e-6`、Dbase `7.0136e-6`、D `3.9326e-6`。这是固定参数两格的局部结果；在线完整成本、E2–E6 与时变两格尚未完成，最终四格 24 项 Holm 校正不得用这里 12 项局部 Holm 代替。时变数据任务继续运行。

2026-10-19 继续：F-E/F-B 在线完整成本补充实验在 `fixed-put-online-cost-v1.md` 事前冻结，以 SHA 固定的验证集、选择模型与归档，由项目部署器和全局控制器启动于 `campus-3090-2`，run_id `20261019T002631Z__1627c004__fixed-put-online-cost-v1`。节点 worker PID 2941357、child PID 2941358 的命令、工作目录、启动 ticks 与 boot ID 已匹配，当前仍运行，不能重复启动。时变正式数据 v5 维持原进程；两者均未得到新结果。

2026-10-19 继续：`fixed-put-online-cost-v1` 节点 OS child wait return_code=0、SHA-256 校验回传。当前实现下三执行价组中位在线秒数：F-E C `0.3710`、D `0.01895`；F-B C `72.60`、D `0.04405`，完整记录与限制见 `fixed-put-online-cost-result-v1.md`。此为 16 个验证组的实现级成本，不等于优化后方法族前沿。时变正式数据 v5 仍在原进程运行，未训练 T-E/T-B。

2026-10-19 继续：固定参数 E2 补充的验证集 PDE 网格扫描先按 `fixed-put-pde-grid-scan-v1.md` 冻结。`fixed-put-pde-grid-scan-v1` 节点 OS child wait return_code=1，stderr 证实不可变物料清单漏列 `scripts/numerics.py`，无扫描结果；失败及回传收据保留。仅修复物料清单的 v2 见 `fixed-put-pde-grid-scan-v2.md`，已由项目部署器、同项目 SHA-256 物料/环境及全局 preflight/launch 启动于 campus-3090-2，run_id `20261019T011342Z__1627c004__fixed-put-pde-grid-scan-v2`；节点 worker PID 2950439、child PID 2950440 的启动 ticks、boot ID、命令和工作目录均匹配，当前运行中，不得重复启动。时变 v5 原进程仍在 campus-3090 运行。

2026-10-19 继续：`fixed-put-pde-grid-scan-v2` 节点 OS child wait return_code=0、SHA-256 校验回传。每格验证集 128 组三执行价，F-E A MAE `2.5178e-6`、最接近的 PDE 是原 201/100 Dbase（`3.1671e-6`）；F-B A MAE `2.7493e-5`、最接近的 PDE 是 101/50（`3.5054e-5`）。五档网格误差/组耗时及探索性限制见 `fixed-put-pde-grid-scan-result-v2.md`。F-B 后续 E2 要重新计算 101/50 的训练/验证基线并保持原预算种子；时变正式数据原进程仍在运行。

2026-10-19 继续：F-B 同误差级别 E2 已按 `fixed-put-e2-matched-v1.md` 冻结：新 101/50 PDE 残差网络与原 D 在相同 1024 训练组、五种子、固定 3×64 容量下比较，并只作探索性 512 组测试。项目部署器、同项目 SHA-256 物料/环境及全局 preflight/launch 已启动于 campus-3090-2，run_id `20261019T014113Z__1627c004__fixed-put-e2-matched-v1`。节点 worker PID 2956098、child PID 2956099 的 boot ID、启动 ticks、命令和工作目录匹配，当前运行中，不得重复启动。时变正式数据 v5 原进程保持运行。

2026-10-19 继续：`fixed-put-e2-matched-v1` 节点 OS child wait return_code=0、SHA-256 校验回传。相同 F-B 测试前 512 组中，A `2.9968e-5`、101/50 PDE 基线 `3.7132e-5`、Dmatch 五种子均值 `3.4116e-5`、原 201/100 D 五种子均值 `6.0158e-6`。验证集误差匹配没有稳定迁移到该测试子集；详细见 `fixed-put-e2-matched-result-v1.md`。此为原测试已查看后的探索性补充，不替代四格主检验。时变正式数据 v5 继续原进程。

2026-10-19 继续：固定参数 F-E/F-B 风险导数 E3/E4 前的数值标签预检已冻结于 `fixed-put-risk-pilot-v1.md`，只用训练前 8 组/格，检查四个模型参数坐标的中心差分步长与 PDE 网格联合细化，尚不训练网络。项目部署器、同项目 SHA-256 物料/环境及全局 resources/preflight/launch 已在 campus-3090-2 启动 `fixed-put-risk-pilot-v1`，run_id `20261019T021013Z__1627c004__fixed-put-risk-pilot-v1`。节点 worker PID 2962044、child PID 2962045 的 boot ID、启动 ticks、命令和工作目录匹配，当前运行中，不得重复启动。时变正式数据 v5 保持原进程。

2026-10-19 继续：`fixed-put-risk-pilot-v1` 节点 OS child wait return_code=0、SHA-256 校验回传，但仅 5/16 组达到 1e-4 风险导数稳定性门槛；最大步长差 `2.1620e-4`、最大 PDE 联合网格差 `5.9254e-4`。失败主要来自网格差，所有失败组保留。已在 `fixed-put-risk-pilot-v2.md` 冻结相同 16 组、更密 801/400 与 1601/800 网格的追加诊断；E3/E4 正式导数训练仍暂停。时变数据 v5 继续原进程。

2026-10-19 继续：风险导数加密诊断 `fixed-put-risk-pilot-v2` 已经项目部署器、同项目 SHA-256 物料/环境及全局 resources/preflight/launch 启动于 campus-3090-2，run_id `20261019T021240Z__1627c004__fixed-put-risk-pilot-v2`。节点 worker PID 2964205、child PID 2964206 的 boot ID、启动 ticks、命令和工作目录匹配，当前运行中，不得重复启动。时变正式数据 v5 保持原进程。

2026-10-19 继续：`fixed-put-risk-pilot-v2` 节点 OS child wait return_code=0、SHA-256 校验回传。加密后 16 组中 9 组通过，仍有 F-E 2/4/5/6 和 F-B 0/2/6 共七组未过 1e-4 导数数值门槛；最大 PDE 联合网格差 `5.4689e-4`。详见 `fixed-put-risk-pilot-result-v2.md`。须进一步分离空间、时间、域和移动网格/折点误差，E3/E4 正式导数标签和监督训练仍暂停；时变 v5 原进程继续。

2026-10-19 继续：七个风险导数失败训练组的独立空间、时间、域和差分步长轴诊断已冻结于 `fixed-put-risk-axes-v1.md`，并经项目部署器、同项目 SHA-256 物料/环境、全局 resources/preflight/launch 启动于 campus-3090-2，run_id `20261019T022502Z__1627c004__fixed-put-risk-axes-v1`。节点 worker PID 2970446、child PID 2970447 的 boot ID、启动 ticks、命令和工作目录匹配，当前运行中，不得重复启动。时变正式数据 v5 保持原进程。

2026-10-19 继续：`fixed-put-risk-axes-v1` 节点 OS child wait return_code=0、SHA-256 校验回传。七个失败组 28 个组×坐标结果中，25 个以空间轴为最大变化来源；跨全部案例最大空间差 `2.7716e-4`、差分步长差 `8.6703e-5`，时间差 `2.3137e-8`、域差 `3.7595e-11`。详见 `fixed-put-risk-axes-result-v1.md`。下一门槛是进一步单独空间加密及折点敏感性，E3/E4 正式导数训练仍暂停；时变 v5 原进程运行。

2026-10-19 继续：仅空间加密的风险导数预检 `fixed-put-risk-pilot-v3` 已按 `fixed-put-risk-pilot-v3.md` 冻结，在相同训练前 8 组/格上比较 3201 与 6401 点、保持每年 800 时间步和旧差分步长。项目部署器、同项目 SHA-256 物料/环境及全局 resources/preflight/launch 已启动于 campus-3090-2，run_id `20261019T023946Z__1627c004__fixed-put-risk-pilot-v3`。节点 worker PID 2973603、child PID 2973604 的身份、boot ID、命令和工作目录匹配，当前运行中，不得重复启动。时变数据 v5 保持原进程。

2026-10-19 继续：`fixed-put-risk-pilot-v3` 节点 OS child wait return_code=0、SHA-256 校验回传；空间 3201→6401 点、时间固定 800 步/年时，16/16 个训练代表组通过 1e-4 导数门槛，最大差分步长差 `2.8878e-5`、空间网格差 `5.8245e-5`。结果与限制见 `fixed-put-risk-pilot-result-v3.md`。下一步须对更细网格独立复核时间/域及未参与修复的训练新组，方能冻结 E3/E4 正式风险标签和训练；时变 v5 原进程继续。

2026-10-19 继续：细网格风险导数独立轴及未参与修复新组预检已冻结于 `fixed-put-risk-axes-v2.md`，以 6401 点为基准，分别加密空间至 12801 点、时间至每年 1600 步、域扩至 1.5 倍，并再半差分步长；每格有困难旧组与新训练组 8、9。项目部署器、同项目 SHA-256 物料/环境及全局 resources/preflight/launch 已启动于 campus-3090-2，run_id `20261019T031001Z__1627c004__fixed-put-risk-axes-v2`。节点 worker PID 2977143、child PID 2977144 的 boot ID、启动 ticks、命令和工作目录匹配，当前运行中，不得重复启动。时变 v5 原进程继续。

2026-10-19 继续：`fixed-put-risk-axes-v2` 节点 OS child wait return_code=0、SHA-256 校验回传；8 组（含新组）的空间、时间、域及步长独立轴最大差依次 `2.9097e-5`、`3.9331e-8`、`5.4015e-10`、`2.2297e-5`，均低于 `1e-4`；详情见 `fixed-put-risk-axes-result-v2.md`。固定参数 F-E/F-B 分组导数标签 `fixed-put-risk-labels-v1` 已按 `fixed-put-risk-labels-v1.md` 冻结，经项目部署器、同项目 SHA-256 物料/环境及全局 resources/preflight/launch 启动于 campus-3090-2，run_id `20261019T032725Z__1627c004__fixed-put-risk-labels-v1`。时变正式数据 v5 仍在原进程；两者都不得因终端状态重复启动。

2026-10-19 继续：`fixed-put-risk-labels-v1` 节点 OS child wait return_code=0、SHA-256 校验回传；1,024 组全部留账，其中 20 组未过 `1e-4` 门槛，全部是 `sigma` 导数的空间差，故没有发布训练用归档。原失败和计算账本完整保留。只重算 20 个失败组的 `fixed-put-risk-repair-v1` 已按 `fixed-put-risk-repair-v1.md` 冻结，以 SHA 固定的原六份账本、6401/12801 空间网格和原门槛经项目部署器、同项目物料/环境及全局 resources/preflight/launch 启动于 campus-3090-2，run_id `20261019T042620Z__1627c004__fixed-put-risk-repair-v1`。节点 worker PID 2992975、child PID 2992976 的 boot ID、启动 ticks、命令及工作目录匹配，当前运行中，不能重复启动。时变正式数据 v5 保持原进程。

2026-10-19 继续：`fixed-put-risk-repair-v1` 节点 OS child wait return_code=0、SHA-256 校验回传；20 个原失败组全部按未放宽的 `1e-4` 门槛通过，剩余失败 0，完整 1,024 组风险标签归档 SHA-256 `608b6c64bd3b6ef9efc1a721b124e655f7372d9c61c8f73977ee090e8b248aba`，标签形状和组级对齐已复核。B 直接网络的同种子价格-only 与价格+导数监督补充实验已按 `fixed-put-derivative-supervision-v1.md` 冻结，经项目部署器、同项目物料/环境和全局 resources/preflight/launch 启动于 campus-3090-2，run_id `20261019T044716Z__1627c004__fixed-put-derivative-supervision-v1`。节点 worker PID 2998314、child PID 2998315 的 boot ID、启动 ticks、命令和工作目录匹配，当前运行中，不能重复启动。时变正式数据 v5 继续原进程。

2026-10-19 继续：`fixed-put-derivative-supervision-v1` 节点 OS child wait return_code=0、SHA-256 校验回传；20 个拟合的顶层结果完整，嵌套 `models/` 未被原收集器抓取，已另外通过同项目 v2 物料清单返回 20 份模型并逐份 SHA-256 校验。每格五个配对种子下，加入导数监督后价格和四个风险坐标的平均 MAE 均降低，但单拟合训练时间约增加 4.7–4.9 倍，且导数标签生成成本另计；完整结果及探索性限制见 `fixed-put-derivative-supervision-result-v1.md`。时变正式数据 v5 原进程继续，最近只读 train 账本 2,496/8,192 组、无失败文件。

2026-10-19 继续：F-E 欧式看跌平价补充核验已事前冻结于 `fixed-put-parity-check-v1.md`，仅使用预选训练/验证组、固定两档数值设置和原精度门槛。项目部署器完成不可变快照、同项目 SHA-256 物料、环境、resources/preflight 与全局 controller launch；run_id `20261019T051130Z__1627c004__fixed-put-parity-check-v1`，campus-3090-2 worker PID 3003599、child PID 3003600 的启动 ticks、boot ID、命令和工作目录匹配，仍运行，不能重启。时变正式数据 v5 的原节点 child PID 970726 也匹配并继续运行。

2026-10-19 继续：`fixed-put-parity-check-v1` 节点 OS child wait return_code=0、SHA-256 校验回传，18/18 个预选 F-E 合约通过；最大平价代数差 `4.4791e-15`，两档价格最大差 `1.3769e-7`。平价隐含价格与正式标签近机器精度相等，是因为使用了与正式标签相同的 PDE 求解器/数值设置；该比较不能作为独立代码验证，独立 OU 分裂检验另见 `fixed-put-independent-check-v1` 及其修复诊断。结果解释见 `fixed-put-parity-result-v1.md`。时变数据原进程身份仍匹配，只读 train 账本 2,540/8,192 组、无失败文件。

2026-10-19 继续：固定参数风险结构 E3 已按 `fixed-put-risk-structure-v1.md` 冻结并由项目部署器、同项目物料/环境、全局 resources/preflight/launch 执行；run_id `20261019T054015Z__1627c004__fixed-put-risk-structure-v1`，节点 OS child wait return_code=0、SHA-256 校验回传。测试前 128 组每组三执行价的 F-B 提前行权溢价均非负；F-B 相对 F-E 的 `sigma` 敏感度均值随波动率四分位总体增加，完整分层见 `fixed-put-risk-structure-result-v1.md`。本分析在主结果已看后开展，仅作探索性描述，不进入四格主要检验。时变正式数据 v5 原 PID 身份匹配，继续运行。

2026-10-19 继续：固定参数 E5 标签分辨率敏感性分析已按 `fixed-put-label-precision-v1.md` 冻结，并经项目部署器、同项目物料/环境、全局 resources/preflight/launch 执行；run_id `20261019T055536Z__1627c004__fixed-put-label-precision-v1`，节点 OS child wait return_code=0、SHA-256 校验回传。F-E/F-B 2048 组测试的平均网格变化指标分别 `1.0532e-8`/`2.4214e-8`，显著低于原 `1e-6` 通过门槛；F-E 最低 C 模型误差约为该平均指标的 24 倍。指标不是严格真实误差上界，完整解释见 `fixed-put-label-precision-result-v1.md`。时变数据 v5 仍维持原进程。

2026-10-19 继续：固定参数 E6 条件选法已按 `fixed-put-adaptive-selection-v1.md` 冻结，项目部署器传输 170 MB 模型归档并完成同项目 SHA-256 物料/环境、全局 resources/preflight/launch；run_id `20261019T061456Z__1627c004__fixed-put-adaptive-selection-v1`，节点 OS child wait return_code=0、结果 SHA-256 校验回传。F-E 在零成本权重选择全 C；中等成本权重选择 C/D 单阈值；F-B 零成本权重选 C/D 单阈值但耗时很高，计入时间后选全 D。完整规则、测试 MAE、组合在线成本及探索性限制见 `fixed-put-adaptive-selection-result-v1.md`。时变数据 v5 原进程保持运行。

2026-10-19 继续：时变数据 v5 当前原节点子进程身份匹配，训练账本最近只读 2,716/8,192 组、已写入组均通过数值门槛；按约每小时 90 组粗估后续数据接近 96 小时预算，尚不能认定会超时。为防超时丢失既有计算，已仅在本地新增 `scripts/timevarying_formal_recovery.py` 源代码和小型身份校验测试；它要求旧任务先有节点 OS child wait 终态、SHA-256 固定的旧账本及新冻结配置，才能复用认证前缀并只计算缺失组。当前没有部署或启动恢复任务，也没有修改活跃远端快照；若原任务正常完成，此备用代码不参与正式证据。
2026-10-21 继续：时变正式数据 v6 已由节点 OS child wait 证实 return_code=0，五划分 8192 组全部写入并经同项目 SHA-256 校验回传；其中 8191 组认证通过，`ood_long` 第 396 组最低执行价因 T-B−T-E = −1.34759746882e-8 未过原 1e-8 支配门槛，`summary.complete=false`，不发布时变训练快照。已新增单组诊断 v7 协议、代码和冻结配置；来源账本与 OS wait 哈希及代码语法检查通过。项目部署器完成不可变快照、同项目物料/环境、resources/preflight 和 experimentctl launch；run_id `20261021T215911Z__1627c004__timevarying-put-dominance-diagnostic-v7`，固定 campus-3090-2，worker PID 3455863、child PID 3455864 的 boot ID、start_ticks、命令及工作目录匹配。节点状态 running，不得重启。v7 仅诊断已知失败，不用于训练或四格成绩；时变数据当前认证仍为 8191/8192。
2026-10-21 继续：单组 `timevarying-put-dominance-diagnostic-v7` 已经节点 OS child wait return_code=0、同项目 SHA-256 校验回传。23 条预定记录显示最低执行价 PDE T-B−T-E 随加密由 −1.3476e-8 缩至 −4.7044e-11，独立 OU 分裂两档为正，细档 +6.2043e-12；原 1e-8 支配容差和 1e-6 精度门槛均未改变。详见 `timevarying-put-dominance-diagnostic-result-v7.md`。v8 正式修复尚未冻结；原协议要求完整新测试集，不能仅重包 v6 的旧测试账本。时变正式数据 v6 当前仍仅 8191/8192 组认证，训练未启动。
2026-10-21 继续：正式时变数据 v8 按 `timevarying-put-formal-recovery-v8.md` 冻结新测试种子 20261052、新长合约域外种子 20261054，保持总量 8192 组；原 v6 认证的 train/val/ood_vol 合约与账本 5632 组经本地逐组验证，OS wait 固定副本和来源 SHA-256 校验通过。v8 只复用这三划分，完整计算新 test 2048 和 ood_long 512，不将已见失败组或 v6 测试集当作新盲测。项目部署器完成不可变快照、同项目物料及环境收据、resources/preflight 和 experimentctl launch，run_id `20261021T223048Z__1627c004__timevarying-put-formal-recovery-v8`，固定 campus-3090-2。节点 worker PID 3459541、child PID 3459542 的 boot ID、start_ticks、命令、cwd 均匹配；OS 状态 running，不得重启。最新节点认证账本 train 4096、val 1024、test 0、ood_vol 0、ood_long 0，总计 5120/8192 (62.50%)；源账本的 5632 数量不冒充尚未写入 v8 的进度。完整数据和独立核验前不训练时变网络。

2026-10-23 继续：v8 时变看跌正式数据已由节点 OS child wait return_code=0 终结并经同项目 SHA-256 校验回传；train/val/test/ood_vol/ood_long 分别 4096/1024/2048/512/512 组全部认证，失败 0，`summary.complete=true`，数据归档 SHA-256 `b1db5c8042c8ac2d6090656add4d16b089d35f0403ac90e41c07d0b833da79ce`。按原预冻结组号和 1e-6 门槛，新的独立 OU 分裂核验已冻结于 `timevarying-put-independent-check-v8.md`；项目部署器完成不可变快照、同项目 SHA-256 物料/环境收据、resources/preflight 与 experimentctl launch，run_id `20261023T031113Z__1627c004__timevarying-put-independent-check-v8`，campus-3090-2 worker PID 3737684、child PID 3737685 的 boot ID、start ticks、命令和 cwd 匹配，节点状态 running。不得重复启动；独立核验通过前不训练时变网络。

2026-10-23 继续：`timevarying-put-independent-check-v8` 的 44/44 个预选 T-E/T-B 合约单元通过原 1e-6 门槛，最大细档对 PDE 差 6.0778e-7、两档变化 3.3544e-7；节点 OS child wait return_code=0、同项目 SHA-256 校验回传。结果见 `timevarying-put-independent-check-result-v8.md`。T-E/T-B 的 720 候选拟合、180 条选择规则已事前冻结在 `timevarying-put-fit-v1.md`，训练包仅含 train/val 且 SHA-256 为 `2a3ab0d2719d86a49135dd193da399561d3b65b847e60770f6ae5b904215aa5c`。项目部署器完成不可变快照、同项目物料/环境、resources/preflight 和 experimentctl launch，run_id `20261023T032544Z__1627c004__timevarying-put-fit-v1`，campus-3090-2 worker PID 3746939、child PID 3746940 的 boot ID、start ticks、命令和 cwd 匹配，状态 running，不得重复启动。测试与域外评价尚未进行。

2026-10-23 继续：`timevarying-put-fit-v1` 720/720 候选、180 条选择记录完成，节点 OS child wait return_code=0、同项目 SHA-256 校验回传；所选模型归档和选择文件分别 SHA-256 `fe7da7f162afc75822a68358f3d2d5abfcbb9385496f3762578018d71efcaf79`、`19aece34f800496ef46d9dfb0a996bef39545cb7e583d18225b74107f313950f`。新 test/域外盲测已事前冻结于 `timevarying-put-evaluate-v1.md`，项目部署器经不可变快照、同项目物料/环境、resources/preflight/experimentctl launch 启动并由节点 OS child wait return_code=0、SHA-256 校验回传。run_id `20261023T034254Z__1627c004__timevarying-put-evaluate-v1`；原始分数和 12 项时变主比较已回传，四格 24 项统一 Holm 及成本/风险等补充分析尚未完成，不可声称总体研究完毕。

2026-10-23 继续：四格 24 项事前指定的组级主比较已按 `four-cell-primary-v1.md` 从固定格与时变格两份 SHA-256 固定结果统一 Holm 校正；项目部署器、不可变快照、同项目物料/环境、resources/preflight/experimentctl launch、节点 OS child wait return_code=0 及 SHA-256 校验回传完整。run_id `20261023T035509Z__1627c004__four-cell-primary-v1`。24/24 项的统一调整 p 值均约 0.00239976；这是价格误差主比较的统计结果，在线成本、方法精度前沿和风险导数/E2–E6 的四格解释仍需审计，不等于四格研究总体完成。

2026-10-23 继续：时变 T-E/T-B 完整在线成本在 `timevarying-put-online-cost-v1.md` 事前冻结为验证前 16 组、每组三执行价及五种子 4096 组训练预算所选模型。原数值基线与冻结验证数组须逐价相符至 1e-6。项目部署器完成不可变快照、同项目 SHA-256 物料/环境、resources/preflight 和 experimentctl launch，run_id `20261023T041117Z__1627c004__timevarying-put-online-cost-v1`，campus-3090-2 worker PID 3767206、child PID 3767207 的 boot ID、start ticks、命令及 cwd 匹配，当前 running，不能重复启动。四格主要 24 项 Holm 已完成，但成本、精度前沿、风险导数与补充分析仍待完成。

2026-10-23 继续：`timevarying-put-online-cost-v1` 已取得节点 OS child wait return_code=0、同项目 SHA-256 校验回传，T-E/T-B 各 16/16 个验证组完成，完整 544 条方法/种子计时记录和汇总见 `timevarying-put-online-cost-result-v1.md`。基线逐价复现原冻结验证数组至 1e-6；T-E 的 C/D 中位在线耗时约 54.472/0.01937 秒，T-B 约 238.642/0.04695 秒，每组三执行价。精度—成本数值前沿和剩余补充分析仍未完成。

2026-10-23 继续：T-E/T-B 的数值精度—成本前沿 v1 已按 `timevarying-put-precision-frontier-v1.md` 事前冻结为两格各 8 个验证组、每组三执行价、GTFK 六档和 PDE 五档。脚本语法、14 个部署文件及数据 SHA-256 已检查。项目部署器完成不可变快照、同项目物料/环境、resources/preflight 和 experimentctl launch，run_id `20261023T061029Z__1627c004__timevarying-put-precision-frontier-v1`，固定 campus-3090-2，worker PID 3801304、child PID 3801305 的 boot ID、start ticks、命令和 cwd 匹配，节点状态 running；不得重复启动。逐组账本当前 0/16，仅表示尚无完整格-组，不代表总体研究完成率。

2026-10-23 继续：`timevarying-put-precision-frontier-v1` 两格各 8/8 组、每组三执行价和 11 个数值档位全部完成，节点 OS child wait return_code=0、同项目 SHA-256 校验回传。201/100 PDE 复现冻结 Dbase 门槛通过。完整结果见 `timevarying-put-precision-frontier-result-v1.md`；固定格 GTFK 前沿及跨四格风险/补充分析仍需完成。

2026-10-23 继续：固定 F-E/F-B 数值前沿已按 `fixed-put-precision-frontier-v1.md` 冻结为两格各 8 个验证组，分别扫描直接 GTFK 求积、折点分段 GTFK 状态/求积/域和 PDE 独立空间/时间轴。脚本语法、物料存在性及数据 SHA-256 检查通过。项目部署器完成不可变快照、同项目物料/环境、resources/preflight 和 experimentctl launch，run_id `20261023T065603Z__1627c004__fixed-put-precision-frontier-v1`，固定 campus-3090-2，worker PID 3804881、child PID 3804882 的 boot ID、start ticks、命令、cwd 匹配。节点运行中，不得重复启动；逐组账本当前 F-E 8/8、F-B 0/8。

2026-10-23 继续：`fixed-put-precision-frontier-v1` 已完成 F-E/F-B 各 8/8 组、各自全部数值档位，节点 OS child wait return_code=0、同项目 SHA-256 校验回传；201/100 PDE 复现 Dbase 门槛通过。详见 `fixed-put-precision-frontier-result-v1.md`。四格主比较与数值前沿均已完成，但风险敏感度、边界、E2–E6 的跨格审计和最终综合报告仍未完成。

2026-10-23 继续：四格组级诊断 v1 在运行前冻结为每格 test 2048、ood_vol 512、ood_long 512 组，总 12288 格-组；输入 SHA-256、脚本语法、部署文件检查通过。项目部署器完成不可变快照、同项目物料/环境、resources/preflight、experimentctl launch；run_id `20261023T074052Z__1627c004__four-cell-group-diagnostics-v1` 在 campus-3090-2 取得节点 OS child wait return_code=0，同项目 SHA-256 回传。全组误差、近零价格、提前行权溢价及域外排序变化见 `four-cell-group-diagnostics-result-v1.md`。真实行权边界、时变风险导数及最终 E2–E6 解释仍未完成。

2026-10-23 继续：时变 T-E/T-B 七参数风险导数数值预检 v1 按 `timevarying-put-risk-pilot-v1.md` 冻结为两格各 1 组、中间执行价；经项目部署器完成不可变快照、同项目物料/环境、resources/preflight、experimentctl launch。run_id `20261023T075600Z__1627c004__timevarying-put-risk-pilot-v1` 在 campus-3090-2 完成，节点 PID 身份和 OS child wait return_code=0、同项目 SHA-256 回传已核验。逐组账本 2/2 通过，最大步长/空间/时间/截断域变化分别 1.1695e-5、5.8325e-5、7.4490e-8、1.440e-11；这是代表性轴的探索性预检，不等于全量风险标签认证。真实行权边界、扩展风险标签及最终跨格综合仍未完成。

2026-10-23 继续：时变风险导数扩展轴检查 v2 已按 `timevarying-put-risk-axes-v2.md` 冻结为 T-E/T-B 验证集各 16 组、每组中间执行价，共 32 格-组。输入 SHA-256、三执行价组完整性和脚本语法已核查。项目部署器完成不可变快照、同项目物料/环境、resources/preflight 与 experimentctl launch；run_id `20261023T082451Z__1627c004__timevarying-put-risk-axes-v2` 固定 campus-3090-2。worker PID 3813503、child PID 3813504 的 boot ID、start ticks、命令及 cwd 匹配，OS 状态 running，不得重复启动。节点实时逐组账本最近 2/32 格-组均通过；此检查仍非整体研究完成率。

2026-10-23 继续：`timevarying-put-risk-axes-v2` 的 T-E/T-B 验证集各 16/16 组、七坐标逐组账本全部完成且 32/32 通过，节点 OS child wait return_code=0、同项目 SHA-256 校验回传。数值轴最大变化和限定范围见 `timevarying-put-risk-axes-result-v2.md`。该检查不替代真实行权边界或最终跨四格导数比较。

2026-10-23 继续：时变 T-E/T-B 测试子集风险导数标签 v1 已按 `timevarying-put-risk-labels-v1.md` 冻结为两格各 128 组、每组中间执行价，共 256 格-组；七坐标与 1e-4 数值门槛不变。冻结输入 SHA-256、组内三执行价和脚本语法核查通过。项目部署器完成不可变快照、同项目物料/环境、resources/preflight、experimentctl launch；run_id `20261023T083957Z__1627c004__timevarying-put-risk-labels-v1` 在 campus-3090-2 的 worker PID 3816234、child PID 3816235 的 boot ID、start ticks、命令、cwd 匹配，节点 running，日志 stderr 为空，不能重复启动。实时逐组账本最近 3/256 均通过；该阶段是探索性导数标签，不代表四格总体完成率。

2026-10-23 继续：`timevarying-put-risk-labels-v1` 已完成 256/256 格-组计算，节点 OS child wait return_code=0、同项目 SHA-256 校验回传；252 组通过、4 组因空间轴导数差超过原 1e-4 门槛失败。失败组和原始数值保留，详见 `timevarying-put-risk-labels-result-v1.md`。本阶段计算完成不等于 256 组标签全部认证；须先加密诊断失败组。

2026-10-23 继续：针对 v1 四个失败组的空间轴加密诊断 v2 已按 `timevarying-put-risk-repair-v2.md` 冻结为两格各 4 组、共 8 格-组，含四个已知失败和四个对照；原门槛 1e-4 未变。项目部署器完成不可变快照、同项目物料/环境、resources/preflight/experimentctl launch；run_id `20261023T102523Z__1627c004__timevarying-put-risk-repair-v2`，campus-3090-2 worker PID 3825845、child PID 3825846 的 boot ID、start ticks、命令和 cwd 匹配，节点 running，不能重复启动。实时账本最近 1/8 已通过。原 v1 失败账本完整保留，诊断结果未定。

2026-10-23 继续：`timevarying-put-risk-repair-v2` 已完成 8/8 格-组、节点 OS child wait return_code=0、同项目 SHA-256 校验回传，7 组通过；T-B 110 的 `sigma1` 在 6401/9601 点空间轴上仍差 1.04456e-4，未过原 1e-4 门槛。原始失败保留，详见 `timevarying-put-risk-repair-result-v2.md`；须继续单组加密诊断，不能声称 256/256 组标签均认证。

2026-10-23 继续：T-B 110 单组风险导数更细网格诊断 v3 已按 `timevarying-put-risk-repair-v3.md` 冻结，原 1e-4 门槛不变。项目部署器完成不可变快照、同项目物料/环境、resources/preflight/experimentctl launch；run_id `20261023T104012Z__1627c004__timevarying-put-risk-repair-v3`，campus-3090-2 worker PID 3828910、child PID 3828911 的 boot ID、start ticks、命令及 cwd 匹配，原节点 running，不得重启。实时逐组账本尚为 0/1；最终诊断结果未定。

2026-10-23 继续：`timevarying-put-risk-repair-v3` 已由节点 OS child wait return_code=0 终结并经同项目 SHA-256 校验回传，T-B 110 的七坐标全部通过原 1e-4 门槛；`sigma1` 9601/12801 点空间差 5.00568e-5。详见 `timevarying-put-risk-repair-result-v3.md`。v1 原始 4 个失败仍保留；按来源标识后可组合 252 个 v1、3 个 v2、1 个 v3 的通过记录，但尚未运行组合审计。真实行权边界和四格综合仍未完成。

2026-10-23 继续：时变风险导数来源合并审计 v1 已按 `timevarying-put-risk-merge-v1.md` 冻结并经项目部署器、同项目物料/环境、resources/preflight/experimentctl launch 运行。run_id `20261023T105543Z__1627c004__timevarying-put-risk-merge-v1`，节点 OS child wait return_code=0、同项目 SHA-256 校验回传。256/256 中间执行价测试子集标签均有通过原门槛的来源记录，其中 v1/v2/v3 分别 252/3/1；来源和网格点数逐组保留，见 `timevarying-put-risk-merge-result-v1.md`。真实行权边界、四格模型导数精度分析及最终综合未完成。

2026-10-23 继续：真实百慕大行权边界两组数值预检 `put-exercise-boundary-pilot-v1` 已完成 2/2，节点 OS child wait return_code=0、同项目 SHA-256 回传；两格代表合同的真实 intrinsic-minus-continuation 根在预检网格间稳定。随后按预先冻结的 `put-exercise-boundary-sample-v1.md` 完成 F-B/T-B 各 16 个测试组，共 32/32 格-组；run_id `20261023T114012Z__1627c004__put-exercise-boundary-sample-v1`，节点 OS child wait return_code=0、同项目 SHA-256 回传。原冻结单根及 1e-4 短利率位置门槛仅 23/32 通过；9 组失败原始账本保留，详见 `put-exercise-boundary-sample-result-v1.md`。须诊断缺根、独立 OU 分裂法的低利率伪根及接近切触的根位置敏感性，不得称全样本边界已认证。四格模型导数和最终综合仍未完成。

2026-10-23 继续：选择性边界加密诊断 v2 因新增脚本的 `groups_by_cell` 兼容分支错误，在任何组计算前 `KeyError: 'groups'`；run_id `20261023T115452Z__1627c004__put-exercise-boundary-diagnose-v2` 的节点 OS child wait return_code=1，失败快照、stderr 与回传收据完整保留。经加法式修复的 v3 在相同冻结 11 格-组和七设置上完成 11/11，run_id `20261023T115731Z__1627c004__put-exercise-boundary-diagnose-v3`，节点 OS child wait return_code=0、同项目 SHA-256 回传。缺根组确认为采样域内全行权；低利率多根对独立 OU 分裂空间分辨率敏感；T-B 10 等近切触根位置仍病态。详见 `put-exercise-boundary-diagnose-result-v3.md`。原 32 组门槛 23/32 通过的结论未改，全面边界与四格最终综合仍待完成。

2026-10-23 继续：已冻结的四格直接网络 B 风险导数审计 v1 完成 20/20 格-种子记录，每格 128 个中间执行价测试组，五种子、4096 组训练预算的已选价格模型；run_id `20261023T121255Z__1627c004__four-cell-direct-risk-audit-v1`，节点 OS child wait return_code=0、同项目 SHA-256 回传。与混合空间分辨率 PDE 导数子集的逐坐标差及符号失配已记录，见 `four-cell-direct-risk-audit-result-v1.md`。这是已观察价格结果后的 B-only 探索性导数审计；A/C/D 导数、全部执行价、完整测试分布、边界数值问题及最终四格综合仍未完成。

2026-10-23 继续：时变两格 E6 条件选法补充已按 `timevarying-put-adaptive-selection-v1.md` 冻结并完成 6/6 格-权重记录；run_id `20261023T122647Z__1627c004__timevarying-put-adaptive-selection-v1`，节点 OS child wait return_code=0、同项目 SHA-256 回传。验证集单次分裂规则在 T-E/T-B 各 2048 测试组的精度/成本权衡详见 `timevarying-put-adaptive-selection-result-v1.md`。其成本是暖机小样本代理，结果属事后探索；时变 E2/E3/E4/E5 的完整对照、A/C/D 导数、全面真实边界及最终四格综合仍待完成。

2026-10-23 继续：时变两格 E5 标签分辨率敏感性分析已按 `timevarying-put-label-precision-v1.md` 冻结，T-E/T-B 各 2048 测试组共 4096/4096 格-组完成；run_id `20261023T122950Z__1627c004__timevarying-put-label-precision-v1`，节点 OS child wait return_code=0、同项目 SHA-256 回传。逐组三执行价的 PDE 网格/时间/域细化指标与五方法及六项误差差的尺度比较见 `timevarying-put-label-precision-result-v1.md`。细化指标不是严格误差上界，时变 E2/E3/E4、A/C/D 导数、全面真实边界与最终综合仍待完成。
2026-10-23 12:41 UTC: time-varying E3 paired risk structure v1 completed 128/128 first test groups (middle strike), node OS child wait 0, checksum-verified return. Mean T-B minus T-E price premium 0.0541051; zero negative-premium consistency flags. See timevarying-put-risk-structure-result-v1.md. E2 matching, E4 risk supervision, A/C/D risk derivative comparison, boundary follow-up, and final synthesis remain open.
2026-10-23 12:56 UTC: time-varying E2 validation PDE grid scan v1 completed 64/64 cell-groups, node OS child wait 0 and checksum-verified return. Frozen closest-A-error rule selects T-E 401/200 and T-B original Dbase 201/100; T-E matched residual-network training/evaluation remains open. See timevarying-put-pde-grid-scan-result-v1.md.
2026-10-23 13:11 UTC: time-varying E2 matched PDE residual follow-up v1 completed 2560/2560 T-E baseline groups plus five fixed-capacity seeds, node OS child wait 0 and checksum-verified return. Matched 401/200 baseline test MAE 4.8868e-6, Dmatch five-seed mean 7.9212e-6, original D 3.0541e-5; exploratory post-primary comparison. See timevarying-put-e2-matched-result-v1.md. E4 risk supervision, A/C/D derivative comparison, boundary follow-up, and final synthesis remain open.
2026-10-23 13:25 UTC: time-varying E4 train risk-label stage v1 frozen for TE/TB first 256 train groups each, 512 cell-groups total, then deployed via project snapshot, same-project SHA material/environment, global preflight/launch to campus-3090-2. Run `20261023T132517Z__1627c004__timevarying-put-risk-labels-train-v1`, worker PID 3859855 and child PID 3859856 match node boot/start/cwd/command; node OS process still running. Read-only live node ledger at 13:25 UTC had 2/512 group rows; no duplicate launch. Validation risk labels and supervision follow after numeric certification.

2026-10-23 19:29 UTC: time-varying E4 training and validation PDE derivative labels were numerically repaired and merged with source/grid provenance: train 512/512 (502 original, 10 repaired) and validation 256/256 (252 original, 4 repaired), plus previously certified test 256/256. The first train merge v1 had wrong “test subset” scope metadata; it and all receipts remain preserved, and the additive train/val merge v2 corrected split metadata, both with OS child wait 0 and checksum return. Frozen paired B price-only versus price+risk supervision completed 20/20 fits (TE/TB × two arms × five seeds), OS child wait 0 and checksum return; mean TE price MAE 0.00218573→0.00194635 and TB 0.00745839→0.00643666, with lower mean MAE on all seven derivative coordinates. See timevarying-put-derivative-supervision-result-v1.md. A/C/D derivative audits, boundary follow-up, and final synthesis remain open.

2026-10-23 21:53 UTC: time-varying A/Dbase derivative numerical-stability pilot completed 4/4 T-E/T-B cell-groups, node OS child wait 0 and checksum-verified return. Dbase resolution changes reach 2.98e-4, while A T-E group 1 step change reaches 4.82e-6. This is diagnostic, not full A/C/D derivative certification. See timevarying-put-baseline-risk-pilot-result-v1.md.

2026-10-23 22:27 UTC: time-varying C/D residual derivative pilot completed 40/40 fit-group rows on the four A/Dbase-audited test cell-groups, node OS child wait 0 and checksum-verified return. See timevarying-put-residual-risk-pilot-result-v1.md. Larger A/C/D audit and boundary follow-up remain open.

2026-10-23 22:39 UTC: additional T-E/T-B A/Dbase stratified derivative audit frozen for six previously unused certified test groups per cell (12 new cell-groups), using the prior pilot numerical settings. Deployed through project immutable snapshot, same-project SHA materials/environment and global resources/preflight/launch to campus-3090-2. Run 20261023T223908Z__1627c004__timevarying-put-baseline-risk-stratified-v1, worker PID 4042506 and child PID 4042507 verified alive with node boot/start/cwd/command; initial live ledger 0/12. Do not relaunch while active.

2026-10-24 03:39 UTC: T-E/T-B A/Dbase stratified derivative extension completed 12/12 frozen cell-groups, OS child wait 0 and SHA-256-verified return. All recorded values finite and frozen price identities exact, but T-B group 127 coarse Dbase derivatives are unstable (max step change 0.0206, resolution change 0.0210); independent PDE reference agrees with refined derivative. SciPy interpolation overflow warnings retained. This is a numerical gate failure for coarse Dbase risk, not completion of A/C/D derivative certification. See timevarying-put-baseline-risk-stratified-result-v1.md.

2026-10-24 04:23 UTC: targeted fixed-grid diagnosis v2 completed 2/2 frozen groups, campus-3090-2 OS child wait return_code=0 and same-project SHA-256 verified return. Fixing the grid improves T-B 127 coarse `sigma1` derivative but leaves its `sigma2` discrepancy; fixed-grid `log(r0)` derivative is inapplicable because the evaluation state was also fixed. V1's pre-computation packaging failure remains preserved. Coarse Dbase derivative numerical gate is still failed; see timevarying-put-fixed-grid-risk-diagnose-result-v2.md.

2026-10-24 04:57 UTC: the additional T-E/T-B C/D derivative subset completed 120/120 frozen fit-group rows, campus-3090-2 OS child wait return_code=0 and same-project SHA-256 verified return. C remains close to certified subset reference; D errors inherit coarse Dbase numerical instability, with maximum T-B derivative resolution change 0.020986. V1 deployment stopped before launch on a registry-lock sandbox permission error; V2 preserved the same comparisons and completed. See timevarying-put-residual-risk-stratified-result-v2.md. Full-distribution derivative certification, boundary follow-up, and four-cell synthesis remain open.

2026-10-24 05:25 UTC: additive exploratory boundary-topology classification completed 32/32 frozen F-B/T-B test groups, campus-3090-2 OS child wait return_code=0 and same-project SHA-256 verified return. Among 64 early-exercise decisions, 56 are single-root consistent under the new rule, seven remain marginal-gap unresolved, and one is all-exercise within the sampled domain. The original frozen 23/32 qualification count is unchanged; see put-exercise-boundary-classify-result-v1.md. Model error near true boundaries and final four-cell synthesis remain open.

2026-10-24 05:40 UTC: interim four-cell put-price aggregation completed 4/4 frozen cells, campus-3090-2 OS child wait return_code=0 and same-project SHA-256 verified return. Existing 2048-test-group-per-cell scores show C has the lowest selected-configuration mean price MAE in all four cells, but online baseline cost, Dbase/D derivative instability, unresolved boundaries and E2–E6 synthesis prevent a final universal-method conclusion. See four-cell-price-synthesis-result-v1.md. Full derivative distribution and final synthesis remain open.

2026-10-24 05:55 UTC: an additional predeclared T-E/T-B A/Dbase derivative subset, 16 new cell-groups, was launched through the project deployer and global resources/preflight/experimentctl on campus-3090-2 using immutable same-project snapshot, SHA-256 inputs and environment receipt. Run `20261024T055454Z__1627c004__timevarying-put-baseline-risk-extension-v1`; node worker PID 4097315 and child PID 4097316 match boot identity, start ticks, command and cwd and remain running. The first live ledger read showed 0/16 groups; do not relaunch. The earlier 16 cell-groups are not repeated; coarse Dbase failures remain preserved.

2026-10-24 12:39 UTC: T-E/T-B A/Dbase 新增导数扩展完成 16/16 冻结格-组，campus-3090-2 OS child wait return_code=0、同项目 SHA-256 校验回传。粗 Dbase 数值不稳定仍在；A/T-B 组 120 sigma1 对独立参考误差达 0.0032168。见 timevarying-put-baseline-risk-extension-result-v1.md。C/D 同组 160 条拟合-组跟进已事前冻结，尚待运行；全分布导数和最终综合仍未完成。

2026-10-24 12:58 UTC: 时变 C/D 在新增八组/格的导数扩展完成 160/160 冻结拟合-组记录，campus-3090-2 OS child wait return_code=0，同项目 SHA-256 校验回传。C 与参考在此探索性子集较接近，D 继承粗 Dbase 分辨率不稳定；见 timevarying-put-residual-risk-extension-result-v1.md。四格全分布导数认证、真实边界及最终综合仍未完成。

2026-10-24 13:27 UTC: 真实行权根暴露与初始价格误差的探索性分析完成 F-B/T-B 32/32 冻结格-组，campus-3090-2 OS child wait return_code=0、同项目 SHA-256 校验回传。26 组双日期单根可判定，6 组拓扑未判定；F-B near 仅 1 组，不能得出稳健边界精度结论。该分析不是行权日继续持有价值或根位置的模型误差核验，原 23/32 边界资格数不变。见 put-boundary-exposure-error-result-v1.md。最终四格综合仍未完成。

2026-10-24 14:03 UTC: 为核验 T-B 组 120 的 GTFK sigma1 导数异常，事前冻结 1/1 格-组的 6401→9601 点状态网格诊断 `timevarying-put-gtfk-risk-group120-v1`。项目部署器完成不可变快照、同项目 SHA-256 物料和环境收据，经全局 resources/preflight/experimentctl launch 启动于 campus-3090-2，run_id `20261024T140303Z__1627c004__timevarying-put-gtfk-risk-group120-v1`。节点 worker PID 4137741、child PID 4137742 的 boot/start/cwd/command 身份匹配，14:03 UTC 状态为原子进程仍在运行；不可重复启动。此为已知异常的探索性数值诊断，不替代全分布导数或真实边界误差验证。

2026-10-24 15:09 UTC: 上述 GTFK 组 120 诊断完成 1/1 格-组，节点 OS child wait return_code=0，未重启原实验。同项目 SHA-256 校验回传完成；最初仅本机缓存写入受沙箱拒绝，补权限后只重试收集。6401→9601 点七坐标最大变化约 3.05e-10，sigma1 与独立参考差仍约 0.00321675437，说明该差异不来自此状态网格分辨率。见 timevarying-put-gtfk-risk-group120-result-v1.md；全分布导数及真实边界误差仍未认证。

2026-10-24 15:26 UTC: 对追加拓扑规则仍未判定的 F-B 1、2、6、13 和 T-B 3、10 六组，事前冻结更细空间/时间及独立 OU 分裂边界诊断 `put-exercise-boundary-unresolved-v1`，经项目部署器及全局 resources/preflight/experimentctl launch 启动于 campus-3090-2 的不可变快照。run_id `20261024T152546Z__1627c004__put-exercise-boundary-unresolved-v1`；节点 worker PID 4151356、child PID 4151357 的 boot/start/cwd/command 身份匹配，实时账本已有 2/6 格-组，原进程运行中。不得重复启动；原 23/32 边界资格数不改写。

2026-10-24 15:39 UTC: 六组加密边界诊断完成 6/6 格-组，节点 OS child wait return_code=0，同项目 SHA-256 校验回传。五组在两个提前行权日四档均单根，最大根跨度约 1.49e-5；F-B 2 第一日四档均为采样域内全行权，第二日单根。原 23/32 门槛仍保留为失败，不因追加分类变成事前通过。见 put-exercise-boundary-unresolved-result-v1.md；模型在行权日状态的局部边界误差仍未测量。

2026-10-24 16:53 UTC: 四格 t=0 看跌价格比较与 E2–E6 补充分析已按归档证据结算，最终报告 `four-cell-final-synthesis-v1.md` 已写成。四格各 2048 测试组、统一 24 项 Holm、在线成本/精度前沿/域外诊断均有校验回传。全分布导数精度未认证，原百慕大边界资格 23/32 未通过；B/C/D 当前仅输出 t=0 价格，真实行权日局部边界误差不适用于当前模型。所有失败和草稿保留，不声称各方法无条件通过。最后加密边界诊断 6/6 已 OS child wait 0、SHA-256 回传；本项目全局活动租约状态为空。

2026-10-25：用户要求继续未认证项后，已事前冻结 A/Dbase 行权日真实根位置四组探索性试跑 `put-method-boundary-pilot-v1.md`；该补充不改变原 23/32 门槛，也不把仅有 t=0 价格的 B/C/D 网络当作边界函数。v1 的同项目物料和环境收据完成，但项目部署器在全局项目注册锁处遭本机沙箱 PermissionError，未 preflight/launch、无实验子进程，失败与收据保留。本项目全局活动租约复核为空；v2 只修正部署权限，保持原样本、数值设置与门槛，见 `put-method-boundary-pilot-v2.md`。

2026-10-25：`put-method-boundary-pilot-v2` 已完成 4/4 格-组，campus-3090-2 OS child wait 0、子进程退出、同项目 SHA-256 校验回传；v1 部署锁失败与 v2 首次回传缓存权限失败均保留且没有重启实验。四组各三行权日均单根，参考最大根差 8.917e-5、A 两档最大根变化 5.123e-5，均低于探索性 1e-4 门槛；A 与 Dbase 对最细 PDE 的最大短利率根差分别 2.669e-4、9.657e-4。见 `put-method-boundary-pilot-result-v2.md`。四组选自已观察测试边界，不能当总体认证；原 23/32 不改写。

2026-10-24 17:12 UTC：原 32 组 A/Dbase 真实行权根探索性复核 `put-method-boundary-all-v1` 已按另行冻结的样本、数值档和资格门槛，通过项目部署器、同项目物料/环境与全局 resources/preflight/experimentctl launch 在 campus-3090-2 不可变快照启动。run_id `20261024T171243Z__1627c004__put-method-boundary-all-v1`，worker PID 4163757、child PID 4163758 的节点 boot ID、启动 ticks、命令与 cwd 身份相符，当前均存活；认证节点账本已写 3/32 格-组（9.375%）。不得因终端或对话状态重启；须等 OS child wait 后校验回传。原 23/32 门槛和四组试跑结果不改写。

2026-10-24 17:18 UTC：`put-method-boundary-all-v1` 已完成 32/32 原始边界格-组，campus-3090-2 OS child wait 0、PID 身份匹配并退出、两份结果 SHA-256 校验回传。按本阶段预定参考与 A 档位稳定性门槛，90/96 行权日为合格单根；F-B 2 第一日域内无根，T-B 2/12 第二日 A 与参考根数冲突，T-B 5/10/13 第二日 A 档位未收敛。见 `put-method-boundary-all-result-v1.md`；原冻结 23/32 不改写。五组追加细化若实施需独立冻结与收据。

2026-10-24 17:22 UTC：针对全 32 组阶段未认证的 T-B 2/5/10/12/13 五组，独立冻结细 PDE、OU 与 A 3201/4801 加密档后，`put-method-boundary-fail-diagnose-v1` 已经项目部署器、全局 resources/preflight/experimentctl launch 启动于 campus-3090-2 不可变快照。run_id `20261024T172207Z__1627c004__put-method-boundary-fail-diagnose-v1`；worker PID 4167182、child PID 4167183 的节点 boot/start/cwd/command 身份匹配，OS 子进程仍运行，首个实时账本为 0/5 组，不得重跑。该诊断不回写 90/96 或原 23/32 门槛。

2026-10-24 17:28 UTC：`put-method-boundary-fail-diagnose-v1` 完成 5/5，节点 OS child wait 0、PID 身份匹配且退出、同项目 SHA-256 校验回传。T-B 5/10/13 第二行权日在更细 A 两档下变为单根且档间根差 <1e-4；T-B 2/12 第二日 A 两档仍双根，而细 PDE 与独立 OU 各单根，拓扑冲突未解。见 `put-method-boundary-fail-diagnose-result-v1.md`。这是后验失败诊断，不回写全 32 组阶段 90/96 或原冻结 23/32。

2026-10-24 17:33 UTC：后验低利率截断域诊断 `put-boundary-low-rate-domain-v1` 已针对 T-B 2/12 两组事前冻结三档 A 域宽，经项目部署器、全局 resources/preflight/experimentctl launch 于 campus-3090-2 不可变快照启动。run_id `20261024T173353Z__1627c004__put-boundary-low-rate-domain-v1`；worker PID 4170201、child PID 4170202 的 boot/start/cwd/command 身份匹配、仍存活；首个节点账本 0/2 组。不得重启；等待 OS child wait 与校验回传。此后验诊断不回写原 23/32、32 组阶段 90/96 或五组阶段的拓扑冲突记录。

2026-10-24 17:39 UTC：`put-boundary-low-rate-domain-v1` 完成 2/2，campus-3090-2 OS child wait 0、节点 PID 身份匹配、两份结果 SHA-256 校验回传。T-B 2/12 的 A 额外低根贴近状态网格短利率下端并随域扩张移动，在域宽 1.5 时消失；同域细 PDE 与独立 OU 均保持单根，根差 <1e-4。见 `put-boundary-low-rate-domain-result-v1.md`。早先 23/32、90/96 及窄域双根原始记录均不改写。

2026-10-24 17:52 UTC：已知 T-B 组 120 的 sigma1 导数异常独立 OU 分裂复核 `timevarying-put-split-risk-group120-v1` 先验证脚本数学接口，再冻结 2/2 个数值档及 1e-4 门槛，经项目部署器、同项目 SHA-256 物料/环境收据和全局 resources/preflight/experimentctl launch 启动于 campus-3090-2 不可变快照。run_id `20261024T175144Z__1627c004__timevarying-put-split-risk-group120-v1`；worker PID 4172668、child PID 4172669 的节点 boot/start/cwd/command 身份匹配且仍运行，认证节点账本当前 0/2 档。不得重启。此诊断不替代全分布导数认证。

2026-10-24 18:02 UTC：`timevarying-put-split-risk-group120-v1` 完成 2/2 冻结数值档。校园节点 OS child wait return_code=0、worker/child 身份匹配且退出，两份原始结果按同项目 SHA-256 校验回传。独立 OU 分裂传播导数最细档 0.06221505174，与细 PDE 参考差 4.77e-7；步长与空间变化分别 2.56e-8、6.85e-10，均低于事前 1e-4。A/GTFK 与二者仍相差约 0.003217。见 `timevarying-put-split-risk-group120-result-v1.md`；全分布导数未认证，原门槛及失败不改写。

2026-10-24 18:20 UTC：为检验已知 T-B 组 120 异常是否局限于该组，另事前冻结 16 个未用于前述 A/Dbase 扩展的 T-B 中间执行价组，仅筛查 sigma1 的 A 导数。`timevarying-put-sigma1-screen-v1` 已通过普通数学接口测试、项目部署器、同项目 SHA-256 物料/环境、全局 resources/preflight/experimentctl launch 在 campus-3090-2 不可变快照启动。run_id `20261024T181940Z__1627c004__timevarying-put-sigma1-screen-v1`；worker PID 4175117、child PID 4175118 的节点 boot/start/cwd/command 身份匹配且仍运行，实时节点账本 0/16 组。不得重启；阶段分母 16 组并非全研究进度。

2026-10-24 19:47 UTC：`timevarying-put-sigma1-screen-v1` 完成 16/16 冻结组，campus-3090-2 OS child wait 0、原 PID 身份匹配并退出，同项目 SHA-256 校验回传。16 组均满足预定 1e-4 步长/网格稳定门槛；对已有细 PDE sigma1 参考的绝对差中位数 7.9250e-5、最大 4.4721e-4（组 17）。这表明稳定的 A 导数方法差异不局限于已知组 120，但只是探索性分散子集，不构成全分布导数认证。见 `timevarying-put-sigma1-screen-result-v1.md`；当前全局活动租约为空。

2026-10-24 20:04 UTC：观察上述筛查后，针对差值最大的 T-B 组 17、57、121 另冻结独立 OU 分裂传播复核 `timevarying-put-split-risk-outliers-v1`，此为后验诊断而非新留出。经普通数学接口验证、项目部署器、同项目 SHA-256 物料/环境和全局 resources/preflight/experimentctl launch 在 campus-3090-2 不可变快照启动。run_id `20261024T200350Z__1627c004__timevarying-put-split-risk-outliers-v1`；worker PID 4178924、child PID 4178925 的 boot/start/cwd/command 身份匹配且运行，当前认证账本 0/3 组。不得重启；等 OS child wait 与校验回传。

2026-10-24 20:17 UTC：`timevarying-put-split-risk-outliers-v1` 完成 3/3 冻结组，campus-3090-2 OS child wait 0、原 PID 身份匹配并退出，同项目 SHA-256 校验回传。三组独立 OU 与细 PDE sigma1 导数最大差 1.80e-7，均通过事前 1e-4 门槛；A 与 OU 差仍为 4.05e-4 至 4.47e-4。见 `timevarying-put-split-risk-outliers-result-v1.md`。这些是后验异常组诊断，不能当独立留出或全分布认证；全局活动租约为空。

2026-10-24 21:06 UTC：状态条件行权日继续持有价值参考试跑 `conditional-boundary-reference-pilot-v1` 完成 4/4 冻结格-组，campus-3090-2 OS child wait 0、原 PID 身份匹配并退出，同项目 SHA-256 校验回传。F-B 组 1/13、T-B 组 3/10 的继续持有曲线 PDE 档间最大变化 3.32e-6，细 PDE 与独立 OU 最大差 1.14e-6；三个行权日单根且短利率根差最大 6.93e-9，均通过事前门槛。见 `conditional-boundary-reference-pilot-result-v1.md`。这些是已观察组的数值方法试跑，不是新网络边界比较；B/C/D 状态条件模型尚未训练。

2026-10-24 21:19 UTC：状态条件标签质量与计时试跑 `conditional-boundary-label-timing-v1` 已事前冻结 F-B/T-B 的 train/val 各八组、共 32 格-划分-组，普通数学接口通过后，经项目部署器、同项目 SHA-256 物料/环境与全局 resources/preflight/experimentctl launch 在 campus-3090-2 不可变快照启动。run_id `20261024T211851Z__1627c004__conditional-boundary-label-timing-v1`；worker PID 4184423、child PID 4184424 的节点 boot/start/cwd/command 身份匹配且仍运行，实时认证账本 2/32 组。不得重启；此阶段不训练网络，也不能算完整边界研究进度。

2026-10-24 21:32 UTC：`conditional-boundary-label-timing-v1` 完成 32/32 冻结格-划分-组，campus-3090-2 OS child wait 0、原 PID 身份匹配并退出，同项目 SHA-256 校验回传。标签质量 32/32 通过事前 1e-4 门槛，最大继续持有价值差 1.30686e-5；根诊断 31/32，余一组首个行权日 PDE/独立参考皆无根。中位计时 11.69 秒/组。见 `conditional-boundary-label-timing-result-v1.md`；下一阶段需冻结状态条件网络训练与真实边界比较。

2026-10-24 22:20 UTC：新状态条件训练/验证数据阶段 `conditional-boundary-trainval-v1` 已冻结 F-B/T-B 各 train 16、val 4，共 40 格-划分-组，每组 3 执行价、前两行权日各 33 状态。输入编码及标签对齐普通测试通过。经项目部署器、同项目 SHA-256 物料与环境、全局 resources/preflight/experimentctl launch 在 campus-3090-2 的新不可变快照启动，run_id `20261024T221936Z__1627c004__conditional-boundary-trainval-v1`。worker PID 4187590、child PID 4187591 的 boot/start/cwd/command 身份匹配并运行，节点原始账本当前 0/40 组，stderr/stdout 尚空。不得重启，须等 OS child wait 与校验回传；此阶段未拟合网络、未接触测试组。

2026-10-24 22:47 UTC：`conditional-boundary-trainval-v1` 完成 40/40 冻结组，全部通过 1e-4 独立标签门槛，最大差 5.586e-6。节点原 PID 与 OS child wait 0 匹配，训练/验证归档及账本同项目 SHA-256 校验回传。每格 train 3168、val 792 条状态条件样本，数据 SHA `05660dbe8f2bc0abdddfeb9821f6f8474980329705afea66d0ce0568c2a55100`；未接触 test。见 `conditional-boundary-trainval-result-v1.md`。

2026-10-24 22:51 UTC：`conditional-boundary-fit-v1` 部署时全局 `projects.json.lock` 写入遭沙箱 PermissionError，尚未 preflight/launch，无拟合运行或活动租约；其错误与物料/环境收据保留。相同科学候选的部署恢复 v2 获全局登记权限后完成资源预检、不可变快照、同项目 SHA-256 物料/环境和 experimentctl launch。run_id `20261024T224951Z__1627c004__conditional-boundary-fit-v2`，worker PID 4191000、child PID 4191001 的节点身份匹配，OS child wait 0，同项目结果校验回传。24/24 候选完成；验证目标 0.002 下 C、D 两格通过，B 两格失败。见 `conditional-boundary-fit-result-v2.md`；测试真实边界尚待事前冻结和评价。

2026-10-24 23:07 UTC：拟合节点的 24 个嵌套模型文件经独立同项目 SHA-256 物料清单受控补充回传并验证；原顶层回传收据及补充收据均保留。新留出行权边界测试 `conditional-boundary-test-v1` 已事前冻结 F-B/T-B 各 test 32–47，共 32 格-组，三执行价、前两行权日；参考和 B/C/D 0.002 价值及 0.001 根门槛固定，普通数学接口测试通过。项目部署器完成新不可变快照、同项目模型/数据/环境、全局 resources/preflight/experimentctl launch；run_id `20261024T230624Z__1627c004__conditional-boundary-test-v1`，campus-3090-2 worker PID 3167、child PID 3168 的 boot/start/cwd/command 身份匹配并运行，节点认证账本当前 0/32 组，stderr 空。不得重启；等 OS child wait 和校验回传。

2026-10-24 23:17 UTC：`conditional-boundary-test-v1` 同一节点 boot/worker PID 3167/child PID 3168 启动身份与当前身份匹配，OS 子进程仍运行，stderr 空；节点原始账本 19/32 冻结格-组。暂时 114/114 早行权日期独立参考有效，B/C/D 的预定联合门槛通过日期 0/73/75；仅为运行中未经最终校验的观测，不发布为终局结论，不重启。

2026-10-24 23:32 UTC：`conditional-boundary-test-v1` 完成 32/32 冻结格-组、192 条早行权日曲线，campus-3090-2 原 worker/child PID 身份与 OS child wait return_code=0 相符，同项目 SHA-256 结果校验回传。独立参考 191/192 有效；T-B test 37 最低执行价第二日价值差 1.58055e-4 超过原 1e-4。预定联合价值与根门槛 B/C/D 通过 0/114/101 条；B 原验证失败未修饰，C/D 价值虽准但根拓扑仍有大量失配。见 `conditional-boundary-test-result-v1.md` 和 `four-cell-final-synthesis-v7.md`。这 32 组为新模型小样本测试，并非全分布边界认证；全分布导数仍未认证。

2026-10-25：`conditional-boundary-fast-label-pilot-v1` 已完成 8/8 组，节点 OS child wait 0 和同项目 SHA-256 校验回传；801/100 相对 3201/400 的最大差 4.50242e-5，低于冻结 1e-4 门槛。已事前冻结扩大 train/val 标签 v2：F-B/T-B 各 128/32 组，合计 320 组，含边界根附近状态。见 `conditional-boundary-fast-label-pilot-result-v1.md` 与 `conditional-boundary-trainval-v2.md`。

2026-10-25 01:21 UTC：`conditional-boundary-trainval-v2` 已经项目部署器、同项目不可变快照及 SHA-256 物料/环境收据、全局 resources/preflight/experimentctl launch 启动于 campus-3090-2；run_id `20261025T012037Z__1627c004__conditional-boundary-trainval-v2`。worker PID 9825、child PID 9826 的 boot/start/cwd/command 身份匹配，当前 OS 子进程运行，认证原始账本 2/320 组、失败 0。不得重启；待 OS wait 与 SHA 回传，全部标签通过后才冻结拟合。

2026-10-25 02:22 UTC：`conditional-boundary-trainval-v2` 同一原进程运行、worker 9825/child 9826 身份匹配，节点认证账本 116/320 组。已发现 F-B train 组 106 的参考 PDE 与独立 OU 最大差 2.640574e-4，超过事前 1e-4 标签门槛；原始失败保留，阶段继续完成以识别全部失败，结束后不直接拟合，须诊断并另立协议。stderr 当前为空。

2026-10-25 02:35 UTC：用户取消 15 分钟续跑，应用自动化 `automation` 已删除；这不终止节点实验。`conditional-boundary-trainval-v2` 同一 worker 9825/child 9826 仍运行，原始账本 141/320 组；当前标签门槛失败为 F-B train106、T-B train5/6，最大差分别 2.64057e-4、1.39878e-4、3.70881e-4。stderr 为 SciPy 插值溢出 RuntimeWarning，非 OS 子进程结束证据；待最终 OS wait、校验回传和失败诊断，暂不拟合。

2026-10-25 02:43 UTC：原扩大标签 v2 在 campus-3090-2 同一 worker 9825/child 9826 继续运行，认证账本 155/320 组、已见四个超限组。已针对观察到的 F-B train106 与 T-B train5/6/15 冻结后验数值诊断 v1；普通数学测试 3/3 通过，经项目部署器、同项目不可变快照及 SHA-256 物料/环境、全局 resources/preflight/experimentctl launch 在另一注册节点 campus-3090 启动，run_id `20261025T024226Z__1627c004__conditional-boundary-label-diagnose-v1`，worker 3795061/child 3795062 的 boot/start/cwd/command 身份匹配且运行。两个运行均不得因会话状态重启；诊断只解释失败，不修饰原门槛或标签。

2026-10-25 02:45 UTC：`conditional-boundary-label-diagnose-v1` 4/4 已完成，campus-3090 原 PID 身份匹配、OS child wait 0、同项目 SHA-256 校验回传。四组 801/100 PDE 对 3201/400 最大差 1.38e-4 至 3.70e-4；1601/200 对细 PDE 均 <1e-5，独立 OU 对细 PDE 均 <3.2e-6。见 `conditional-boundary-label-diagnose-result-v1.md`。原 v2 标签失败照实保留，待其全部 320 组结束才冻结数据修复和拟合。

2026-10-25：已在 v2 全 320 组完成前写定追加修复规则 `conditional-boundary-repair-rule-v1.md`，只重算原账本全部超限组，按 1601/200→3201/400 两档及原 1e-4 独立 OU 门槛选择；任一组两档皆失败即停止拟合。修复脚本及普通单元测试 5/5 已就绪，尚未运行修复证据，也不接触 test。

2026-10-26：conditional-boundary-trainval-v2 320/320 组，campus-3090-2 OS child wait 0、原 PID 身份匹配、同项目 SHA-256 校验回传；304 组标签资格通过，16 组失败，最大差 0.0011619165。已按照结束前冻结的追加规则，将全部 16 个失败组及原归档/账本 SHA-256 固定于 conditional-boundary-repair-v1，未训练模型或接触 test。

2026-10-26 02:38 UTC：原标签阶段 320/320 组、304 通过/16 失败已 OS wait 0 且校验回传。按预冻结规则，全部 16 个超限组修复阶段 `conditional-boundary-repair-v1` 经项目部署器、同项目不可变快照及 SHA-256 物料/环境、全局 resources/preflight/experimentctl launch 启动于 campus-3090-2，run_id `20261026T023755Z__1627c004__conditional-boundary-repair-v1`；worker 76844/child 76845 身份匹配且运行。未训练，不读取 test，不重启。

2026-10-26：conditional-boundary-repair-v1 16/16 修复组完成，campus-3090-2 OS child wait 0、原 PID 身份匹配、同项目 SHA-256 校验回传；15 组用 1601/200，T-B train113 用预设第二档 3201/400，通过组最大独立差 8.1377e-5。新归档 SHA b6719b3222c6c834f69371d1d0bee2b6b479b84d0e4695d8a8308263b96866ad；已核对 F-B/T-B 各 train128/val32、无 test 键、有限值。72 项扩大拟合配置按预冻结设计建立，尚未启动。

2026-10-27：`conditional-boundary-fit-expanded-v1` 于 2026-10-26 02:48 UTC 经项目部署器和全局控制器启动于 campus-3090-2，run_id `20261026T024827Z__1627c004__conditional-boundary-fit-expanded-v1`。上次节点 PID 身份认证时 worker 79178 / child 79179 仍运行，原始拟合账本 2/72；该数字不是当前实时进度。本次资源和 status 查询均显示 campus-3090-2 网络不可达，节点 OS child wait、日志、剩余拟合账本和校验回传无法读取；全局租约仍存在、node_state=null。未重启、未迁移，也未赋予退出码。独立边界测试须待原运行恢复访问并完成结果校验后绑定选中模型 SHA-256。

2026-10-28：campus-3090-2 恢复访问，但节点 boot ID 已改变，原 worker 79178/child 79179 均已消失且无 OS wait；原运行保留为退出码未知的基础设施中断。节点留有 54/72 条拟合账本和 54 个对应模型；55 个文件组成的同项目中断归档 SHA `c7984823ef660c55e7b9dccdafb7f4f44c6952fe90a071463ad2e60000eb472b` 已受控 materialize 回本机。冻结归档及物料收据通过全局 `status --resolve-node-reboot` 校验，原租约已按规则解除，未把原运行记为成功。追加续算协议和代码固定前 54 项复用、只拟合剩余 18 项，已通过普通前缀检查。新阶段 `conditional-boundary-fit-expanded-resume-v1` 经项目部署器、不可变快照、同项目 SHA-256 物料/环境、全局 resources/preflight/experimentctl launch 启动于 campus-3090-2，run_id `20261028T011007Z__1627c004__conditional-boundary-fit-expanded-resume-v1`；worker 3856/child 3857 的 boot/start/cwd/command 身份匹配且在运行。最近节点账本仍为 54/72，新增拟合 0/18；不得重复启动。

2026-10-28 后续：续算阶段 72/72 项完成，节点原 PID 身份匹配、OS child wait return_code=0，顶层结果和 72 个嵌套模型均同项目 SHA-256 校验回传。按原验证 MAE 0.002 门槛，F-B B/C/D 和 T-B C/D 达标；T-B B 最优验证 MAE 0.002391 未达标，失败保留。独立新测试 F-B/T-B 各 test 128–191、合计 128 格-组/768 日期曲线及原数值门槛在模型读取测试前冻结；源数据、选模和六个模型 SHA 均已核对。`conditional-boundary-test-expanded-v1` 已经项目部署器、不可变快照、同项目物料/环境、全局 resources/preflight/experimentctl launch 于 campus-3090-2 启动，run_id `20261028T013505Z__1627c004__conditional-boundary-test-expanded-v1`，worker 14968/child 14969 身份匹配且在运行。节点原始账本最近为 0/128，不得重启；待 OS wait、校验回传和全曲线分析。

2026-10-28 02:51 UTC：`conditional-boundary-test-expanded-v1` 128/128 冻结格-组、768 日期曲线全部结束；原 worker 14968/child 14969 节点身份匹配、OS child wait return_code=0，结果和摘要同项目 SHA-256 校验回传。独立参考 753/768 条通过资格，B/C/D 联合价值及根门槛分别通过 165/454/239 条，全部失败保留；见 `conditional-boundary-test-expanded-result-v1.md`。全局项目 status 返回空活动租约，当前无该项目活动实验，用户可在此安全节点重启机器。原七坐标导数失败和真实边界未被稳定认证的结论不变。
