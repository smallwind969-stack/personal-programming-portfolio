# B题问题3机器狗程序

先在模拟器界面登录，选择“问题3演练测试”，等待界面显示机器狗接口已经就绪。
本程序的覆盖与提前停止规则针对问题3的全向源、总数10–16条件。

在 PowerShell 中进入程序目录：

```powershell
Set-Location -LiteralPath 'C:\Users\LSY\Desktop\数学建模9.10-9.13'
```

检查接口状态，不发送 `/enter`：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot --robot-id 202613002010
```

确认处于问题3演练后，使用当前文献增强最终模式：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot --robot-id 202613002010 --mode q3_final --route-budget 1 --execute
```

如需使用原保守策略：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot --robot-id 202613002010 --mode safe --execute
```

查看最新运行日志：

```powershell
Get-ChildItem -LiteralPath '.\robot_b3\logs' -Filter '*.jsonl' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
```

`q3_final` 在 `q3_dynamic` 的逐频道滚动模型上加入多边形相交单元光学保底；`fusion`、`score` 保留为旧基线。
本机已验证 `py -3.10` 对应 Python 3.10.10；代码只使用标准库，无需联网安装包。
默认接口为 `http://127.0.0.1:2026`。运行记录保存在 `robot_b3/logs/`。
模拟器生成的正式测试加密日志仍需从模拟器界面导出，并保留原文件名。

# 问题4：最终严格证书模式

先在模拟器中选择“问题4演练测试”并等待接口就绪，然后执行：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot --robot-id 202613002010 --mode q4_final --route-budget 1 --execute
```

`q4_final` 采用“原点 + 8 点内环 + 16 点外环”的边界贴合剖分，离线差分进化候选由连续证书再次验收。
它与旧方案同为 25 个严格证书站，但最长证书边约 996.47 米，静态开路线
由 24071.49 米降至约 17887.51 米。已到达的目标位置只有通过三角形包含
和边长双重充分判据后，才会替换未来边界站，因此不会用经验阈值冒充全覆盖证明。

## 问题4信念空间基线

入口中的 `--mode q4_belief` 可复现上一版信念空间策略。

`q4_belief` 是与旧 `q4` 隔离的重建版：使用位置、有效接收半径、
全向/定向类型和方向粒子估计未知频道在当前点的命中概率；
在动态定位/清除停靠点展开深度2的命中与 `no_signal` 结果树，
以“期望剩余时间+尾部风险”选择机会测量，每次只执行根动作并重规划。
定位阶段使用3次探测与光学清除的成本平衡，搜索兜底使用
25站、995米边长的严格三角剖分。概率信念只负责动作排序，不会单独宣布空频道。

最新6个独立离线场景中，旧 `q4` 平均8880.68秒，深度2的 `q4_belief`
平均7643.24秒，两者均6/6全部清除；该结果是离线模拟样本，不代表官方测试保证值。

## 问题4旧基线（仅用于对照）

如需复现原 `q4` 策略，执行：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot --robot-id 202613002010 --mode q4 --route-budget 1 --q4-novelty-distance 350 --q4-insertion-distance 220 --execute
```

该版本保留990米局部凸包覆盖的严格兜底，但改变执行顺序：不足14个源时保持原短路线，
达到14个源后切换空间分散的anytime站序，并在已到达的新颖定位/清除点顺带扫描未知频道；发现15个
源后提高最后一源的发现优先级；发现16个源立即取消剩余严格站点。发现尚未结束时，
只有插入覆盖主路线额外不超过220米的目标任务才允许抢占；一旦启动窄区域光学覆盖链，
连续清除直至成功，不再中途离开后折返。

`--q4-novelty-distance` 越小，动态位置补扫越积极；`--q4-insertion-distance` 越小，
发现阶段越不容易被定位和清除任务打断。上述默认值来自现有8545秒日志的结构性重建，
本轮未做模拟器训练，需由参赛者自行演练校准。

新版策略把剩余覆盖点和全部已知目标放入开放路径规划，每次收到反馈后重排。
补测点按移动、检测、后续定位成本选取；成熟目标选择保证20米内的低绕行清除点。
发现16个源后利用题目数量上限结束未知频道搜索。小区域允许一次光学试探，
失败按3秒计费并继续定位，绝不因尝试过清除就把目标记为完成。

路径搜索默认每轮使用1实秒软预算，可增加 `--route-budget 3`。
计算耗时不计入虚拟成绩，但受题目20分钟程序运行上限约束。
日志中的 `proven_optimal` 只描述当前固定坐标子问题，不代表整场自适应任务全局最优。

`fusion` 还会利用全部正测站推导未知接收半径的下界，以半平面交严格验证扩展补测点；
只有其预测总时间比 `score` 候选低至少100秒时才启用，否则自动回退基线。最终30组
成对离线验证中，两模式均完成395/395个源，平均总时同为2957.43秒（229.24秒/源）。

离线复现对照试验（不访问模拟器或互联网）：

```powershell
py -3.10 -X utf8 -m robot_b3.benchmark --seeds 100 --start 1000 --route-budget 1 --output robot_b3/results/my-validation
```

输出逐场CSV和汇总JSON，使用5 m/s、换频1秒、检测5秒、成功清除5秒、失败3秒。
两版接收相同场景，并从零观察开始，误差按位置固定；真实坐标只由离线模拟器持有。
这是自建场景测试，官方正式成绩需要按赛事流程另外获得。

运行回归测试：

```powershell
py -3.10 -X utf8 -m unittest discover -s robot_b3/tests -v
```
# 逐频道残余覆盖实验

`residual` 模式为严格保证的研究版本：各未知频道独立维护实际检测站点，定位和清除位置只有在能减少后续覆盖站点数时才顺路测量，并对剩余区域重新生成带精确覆盖证书的圆心。

本地配对测试入口（不连接模拟器）：

```powershell
py -3.10 -X utf8 -m robot_b3.benchmark --seeds 30 --start 18000 --route-budget .1 --modes score residual --output robot_b3/results/residual-vs-score
```

模拟器实验入口：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot --robot-id 202613002010 --mode residual --route-budget 1 --execute
```

截至30组配对消融，`residual` 保持384/384全清除，但平均总时间为2978.12秒，慢于 `score` 的2954.56秒，因而当前正式竞赛仍推荐 `--mode score`。该结果说明严格条件下自由补洞中心未减少测量数，反而增加了联合路线长度；若继续冲击速度，需要单独设计允许明确遗漏风险的竞速层。

## 问题三：证书—时间融合入口

真正逐频道联合实验入口：

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot `
  --robot-id 202613002010 `
  --mode q3_joint_residual `
  --route-budget 1 `
  --execute
```

`q3_joint_residual` 继承每个频道各自的残余覆盖证书，并联合选择物理扫描站、站内频道、目标第二测点、保证清除任务和开放路线。第二测点替换采用路线距离与最坏定位半径的 Pareto 支配约束，目标函数显式计入测量后返回目标区域的路程。

`q3_oracle_fusion` 将逐频道残余覆盖证书、物理站点合并、完整指令时间核算和滚动重规划放入同一入口。为防止自适应任务中局部切频收益破坏主路线，距离路线作为安全基线；时间路线只有在保持该几何代价且预测收益超过不确定性裕量时才可替换。目标附近的顺路测量仍须严格减少该频道的剩余证书站数，完整路线反事实同时写入日志用于后续校准。

```powershell
py -3.10 -X utf8 -m robot_b3.run_robot `
  --robot-id 202613002010 `
  --mode q3_oracle_fusion `
  --route-budget 1 `
  --execute
```

自建场景对照结果保存在 `results/q3-oracle-fusion-v6-3.json` 与同名 CSV。该小样本中融合模式与 `residual` 均完成 40/40 个目标，平均虚拟时间均为 2650.07 秒；这只说明融合入口没有引入已观察到的虚拟时间退化，不代表官方场景成绩。
