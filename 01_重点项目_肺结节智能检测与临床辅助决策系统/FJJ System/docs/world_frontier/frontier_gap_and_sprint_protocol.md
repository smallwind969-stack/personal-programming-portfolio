# 肺结节检测 Agent 前沿差距评估与结题冲刺协议

生成日期：2026-06-15

## 1. 当前结论

当前项目已经完成从本地演示系统到可复现实验闭环的关键跃迁：本地病例闭环、LUNA16 subset0 数据接入、FPRED 微调、完整 candidates_V2 候选池评分、FROC/CPM 评估、NMS 分区验证、series-level bootstrap 置信区间、subset1 外部子集验证、论文级图表与中文答辩 PPT。

但是，当前结果还不能宣称达到完整 LUNA16 官方世界前沿水平。最审慎、也最能经得起答辩追问的表述是：

> 本项目已建立可复现的肺结节检测/标注/随访 Agent 科研闭环，并在 LUNA16 subset0 内完成公开候选池级 FROC 验证。采用 calibration split 预先选定的 10 mm NMS 后，evaluation split 的 CPM 为 0.6888（95% CI: 0.6026-0.7804），相较无 NMS 的 0.6199 有稳定提升趋势。

2026-06-15 继续推进后，项目已完成 LUNA16 subset1 外部验证。固定 10 mm NMS 在 subset1 上将 CPM 从 0.5536 提升至 0.5792，series-level bootstrap 95% CI 为 0.4582-0.6838。这证明后处理策略有跨子集迁移收益，但绝对性能仍未达到近年前沿水平。

随后完成 subset0 calibration hard-negative mining：从 calibration series 中挖掘 512 个高置信假阳性并微调 FPRED。在未参与挖掘的 subset0 evaluation split 上，hard-negative FPRED + fixed 10 mm NMS 将 CPM 提升至 0.8648（95% CI: 0.7560-0.9317），0.25 FP/scan sensitivity 提升至 0.7857。该结果已显著接近强方法区间，但仍需要 subset1 新权重外部重评估后才能作为跨子集前沿证据。

已完成 subset1 新权重外部重评估：hard-negative FPRED + fixed 10 mm NMS 在 subset1 上将 CPM 从 baseline 0.5792 提升到 0.6161，95% CI 为 0.5217-0.7099；0.125 FP/scan sensitivity 从 0.2422 提升至 0.3672。该结果证明 hard-negative 排序改进具有一定跨子集迁移性，但绝对 CPM 仍未达到完整 LUNA16 前沿。

已完成 subset2 第三方外部验证的第一阶段：hard-negative FPRED + fixed 10 mm NMS 在 subset2 上获得 CPM 0.6652，95% CI 为 0.5892-0.7494。subset2 未参与训练、hard-negative mining、NMS 半径选择或 subset1 验证，说明模型在第二个外部子集上没有崩溃。但 baseline FPRED 尚未在 subset2 重跑，因此当前不能声明 subset2 上的相对提升幅度。

已完成 subset2 baseline 对照：在同一 subset2、同一 fixed 10 mm NMS 下，hard-negative FPRED 将 CPM 从 baseline 0.5446 提升至 0.6652，并将 0.25 FP/scan sensitivity 从 0.2813 提升至 0.4531。这是目前最强的第三方外部相对提升证据。

## 2. 证据底座

| 证据项 | 当前结果 | 来源 |
|---|---:|---|
| 本地病例闭环 | 3 cases / 607 DICOM slices | `docs/research_loop/` |
| 本地 review-proxy reference nodules | 11 | `docs/research_loop/research_loop_report.json` |
| LUNA16 subset0 CT series | 89 | `docs/world_frontier/luna16/subset0_full_candidates_stream/` |
| subset0 official annotations | 112 | `docs/world_frontier/luna16_subset0_full_candidates_v2_report.md` |
| subset0 raw candidates_V2 predictions | 79,135 | `docs/world_frontier/luna16/subset0_full_candidates_stream/froc/froc_summary.csv` |
| subset0 raw bridge CPM | 0.6020 | 同上 |
| calibration/evaluation split | 55/34 series，56/56 annotations | `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/series_split_summary.json` |
| fixed 10 mm NMS evaluation CPM | 0.6888 | `docs/world_frontier/luna16_evaluation_froc_bootstrap_ci_report.md` |
| fixed 10 mm NMS CPM 95% CI | 0.6026-0.7804 | 同上 |
| subset1 raw CPM | 0.5536 | `docs/world_frontier/luna16_subset1_external_validation_report.md` |
| subset1 fixed 10 mm NMS CPM | 0.5792 | 同上 |
| subset1 fixed 10 mm NMS CPM 95% CI | 0.4582-0.6838 | 同上 |
| hard-negative FPRED subset0 evaluation fixed 10 mm NMS CPM | 0.8648 | `docs/world_frontier/luna16_hard_negative_mining_report.md` |
| hard-negative FPRED subset0 evaluation CPM 95% CI | 0.7560-0.9317 | 同上 |
| hard-negative FPRED subset1 fixed 10 mm NMS CPM | 0.6161 | `docs/world_frontier/luna16_hard_negative_subset1_external_report.md` |
| hard-negative FPRED subset1 CPM 95% CI | 0.5217-0.7099 | 同上 |
| hard-negative FPRED subset2 fixed 10 mm NMS CPM | 0.6652 | `docs/world_frontier/luna16_hard_negative_subset2_third_party_report.md` |
| hard-negative FPRED subset2 CPM 95% CI | 0.5892-0.7494 | 同上 |
| baseline FPRED subset2 fixed 10 mm NMS CPM | 0.5446 | `docs/world_frontier/luna16_subset2_baseline_vs_hard_negative_report.md` |
| subset2 hard-negative absolute CPM gain | +0.1205 | 同上 |
| subset1+subset2 pooled external series | 178 CT / 256 annotations | `docs/world_frontier/luna16_pooled_subset1_subset2_external_validation_report.md` |
| baseline FPRED pooled fixed 10 mm NMS CPM | 0.5580 | 同上 |
| hard-negative FPRED pooled fixed 10 mm NMS CPM | 0.6339 | 同上 |
| hard-negative pooled CPM 95% CI | 0.5802-0.7010 | 同上 |
| pooled hard-negative absolute CPM gain | +0.0759 | 同上 |
| pooled paired-bootstrap CPM gain 95% CI | +0.0101 到 +0.1579 | 同上 |
| FPRED independent candidate AUC | 0.9926 | `docs/world_frontier/luna16/patch_test_103/metrics/bootstrap_summary.json` |

## 3. 与前沿水平的差距

联网核查到的近年公开结果显示，完整 LUNA16 上的强方法通常报告约 0.90 以上的 CPM。例如 2025 年 Scientific Reports 的一篇多尺度 CNN 肺结节检测论文报告 LUNA16 CPM 0.929；LUNA16 官方结果页也强调 leaderboard 针对完整 nodule detection 系统或 false positive reduction 系统。

因此，本项目当前差距主要不在“没有实验”，而在以下四点：

1. 数据范围差距：当前只有 subset0，不是完整 888 CT。
2. 任务定义差距：当前主要是 candidates_V2 + FPRED bridge，不是完整端到端官方 detection submission。
3. 低 FP/scan 差距：0.125 与 0.25 FP/scan sensitivity 仍偏低，且 CI 较宽。
4. 参数验证差距：10 mm NMS 是严谨固定结果；evaluation 上 20-30 mm 更高只能作为新假设，不能事后写成最终选择。

## 4. 下一个最有价值的实验

### 实验 A：subset1 固定协议外部验证（已完成）

目的：验证 subset0 上选出的 fixed 10 mm NMS 是否能迁移到新的 CT 子集。

输入：

- `data/luna16/subset1.zip`，约 6.3 GB。
- `data/luna16/candidates_V2/candidates_V2.csv`。
- `data/luna16/annotations.csv`。
- FPRED 权重：`docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth`。

执行协议：

1. 下载并校验 subset1。
2. 解压 subset1。
3. 从 annotations/candidates_V2 中抽取 subset1 seriesuid。
4. 使用现有 FPRED 流式评分脚本，开启 checkpoint 和 resume。
5. 只报告 fixed 10 mm NMS，不在 subset1 上重新调半径。
6. 输出 subset1 FROC/CPM 与 series-level bootstrap CI。

完成结果：

- subset1 全部 89 series、71,012 candidates_V2 已完成 FPRED 评分。
- fixed 10 mm NMS CPM = 0.5792，95% CI = 0.4582-0.6838。
- raw CPM = 0.5536，说明 fixed 10 mm NMS 有迁移收益，但 subset1 绝对性能低于 subset0 evaluation。
- 下一步应围绕 subset1 高分假阳性进行 hard-negative mining，而不是继续只做后处理半径微调。

### 实验 B：低 FP/scan hard-negative mining

目的：针对 0.125/0.25 FP/scan sensitivity 的短板，提升低假阳性区间表现。

执行协议：

1. 从 subset0 raw candidates_V2 中收集高分假阳性。
2. 按 series 分层，避免把 evaluation 信息泄露到训练。
3. 用 hard negatives 重新微调 FPRED。
4. 在固定 evaluation split 上报告 no NMS / fixed 10 mm NMS / retrained FPRED + fixed NMS 三组消融。

完成结果：

- 已从 subset0 calibration series 挖掘 512 个 hard negatives。
- 已与 base train 256 patches 合并为 768 patches 新训练集。
- subset0 evaluation fixed 10 mm NMS CPM 从 0.6888 提升至 0.8648。
- 0.25 FP/scan sensitivity 从 0.4821 提升至 0.7857。
- 训练与评价 series 分离；subset1 未进入训练。

完成结果：已用 hard-negative FPRED 权重重跑 subset1，fixed 10 mm NMS CPM 从 baseline 0.5792 提升至 0.6161，说明跨子集提升成立但幅度有限。

### 实验 C：NMS 半径二阶段验证

目的：把 evaluation 上 20-30 mm 的事后观察转化为新一轮严谨假设。

执行协议：

1. 不直接选择 evaluation 最优半径。
2. 在新的 calibration 设计或 subset1 calibration 上比较 10/20/30 mm。
3. 在独立 evaluation 或另一个 subset 上固定报告。

成功判据：

- 新半径必须由 calibration 预先选出。
- 独立 evaluation 上 CPM 与低 FP/scan sensitivity 同时不下降。

## 5. 结题表述建议

可以写：

> 项目不仅实现了肺结节检测与标注系统，还构建了面向科研复现的评估闭环，包括 LUNA16 数据接入、候选池评分、FROC/CPM 计算、NMS 后处理分区验证与 bootstrap 置信区间报告。

可以写：

> 当前 public benchmark 结果仍限定于 LUNA16 subset0，主要证明方法链路、评估口径和后处理改进有效；完整 LUNA16 与多中心临床验证是后续工作。

不能写：

> 本系统达到世界前沿水平。

不能写：

> 本系统在完整 LUNA16 上 CPM = 0.6888。

原因：0.6888 是 subset0 内 evaluation split fixed 10 mm NMS 的结果，不是完整 LUNA16 官方 leaderboard。

## 6. 下周汇报的主线

1. 系统闭环：上传 CT、检测候选、医生复核、随访 Agent。
2. 科研闭环：本地病例只做工程证据，公开数据用 LUNA16 subset0。
3. 关键结果：FPRED AUC 0.9926；subset0 raw CPM 0.6020；subset0 fixed 10 mm NMS evaluation CPM 0.6888；subset1 external fixed 10 mm NMS CPM 0.5792。
4. 严谨性：calibration/evaluation 分离、series-level bootstrap CI、CLAIM/TRIPOD+AI 口径。
5. 冲刺路线：已完成 subset1+subset2 pooled external CI；下一步推进 subset3 第四子集验证、低 FP/scan 专项优化和论文实验消融。

## 7. 外部来源

- LUNA16 official data page: https://luna16.grand-challenge.org/Data/
- LUNA16 official results page: https://luna16.grand-challenge.org/Results/
- CLAIM 2024 Update: https://pubs.rsna.org/doi/abs/10.1148/ryai.240300
- TRIPOD+AI statement: https://www.bmj.com/content/385/bmj-2023-078378
- Recent LUNA16 comparison example: https://www.nature.com/articles/s41598-025-97187-w
