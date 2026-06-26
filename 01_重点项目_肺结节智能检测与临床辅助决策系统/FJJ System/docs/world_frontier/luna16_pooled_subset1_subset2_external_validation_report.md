# LUNA16 subset1+subset2 pooled 外部验证报告

日期：2026-06-15

## 1. 实验目的

本轮实验将 subset1 与 subset2 两个未参与 hard-negative mining、模型训练和 NMS 半径选择的外部子集合并，形成 pooled external validation。目的不是宣称完整 LUNA16 官方成绩，而是检验 hard-negative FPRED agent 的跨子集稳定性，并量化其相对 baseline FPRED 的低假阳性区间收益。

## 2. 数据与协议

| 项目 | 数值 |
|---|---:|
| 外部子集 | subset1 + subset2 |
| CT series | 178 |
| official annotations | 256 |
| baseline fixed 10 mm NMS predictions | 106,325 |
| hard-negative fixed 10 mm NMS predictions | 106,187 |
| NMS 半径 | 10 mm，沿用 subset0 calibration 固定协议 |
| bootstrap | 1000 次 series-level bootstrap，seed=20260615 |

合并脚本强制检查 seriesuid 不重叠，并拒绝预测文件中出现不属于声明子集的 seriesuid，以避免跨子集重复计数或数据泄漏。

## 3. Pooled FROC 结果

| 指标 | baseline FPRED | hard-negative FPRED | 绝对提升 |
|---|---:|---:|---:|
| Sens@0.125 FP/scan | 0.222656 | 0.328125 | +0.105469 |
| Sens@0.25 FP/scan | 0.304688 | 0.449219 | +0.144531 |
| Sens@0.5 FP/scan | 0.437500 | 0.554688 | +0.117188 |
| Sens@1 FP/scan | 0.574219 | 0.660156 | +0.085937 |
| Sens@2 FP/scan | 0.699219 | 0.742188 | +0.042969 |
| Sens@4 FP/scan | 0.800781 | 0.824219 | +0.023438 |
| Sens@8 FP/scan | 0.867188 | 0.878906 | +0.011718 |
| CPM | 0.558036 | 0.633929 | +0.075893 |

## 4. Bootstrap 不确定性

| 模型 | CPM | 95% series-bootstrap CI |
|---|---:|---:|
| baseline FPRED + fixed 10 mm NMS | 0.558036 | 0.456829-0.646117 |
| hard-negative FPRED + fixed 10 mm NMS | 0.633929 | 0.580228-0.700952 |

## 5. 配对 bootstrap 增益分析

为直接评估 hard-negative FPRED 相对 baseline FPRED 的改进，本报告进一步使用相同 series 重采样索引进行 paired bootstrap。该计算在每次重采样中同时评估两组十万级预测，使用 1000 次 bootstrap，seed=20260615。

| 指标 | 增益点估计 | 95% paired-bootstrap CI | gain > 0 比例 |
|---|---:|---:|---:|
| CPM | +0.075893 | +0.010124 到 +0.157924 | 0.988000 |
| Sens@0.125 FP/scan | +0.105469 | +0.006944 到 +0.268657 | 0.977000 |
| Sens@0.25 FP/scan | +0.144531 | -0.003690 到 +0.264069 | 0.973000 |
| Sens@0.5 FP/scan | +0.117188 | -0.013453 到 +0.263345 | 0.943000 |
| Sens@1 FP/scan | +0.085938 | +0.013453 到 +0.203065 | 0.991000 |

配对结果支持 hard-negative FPRED 在 pooled 外部验证上的总体 CPM 改进为正，且低 FP/scan 区间的点估计提升最明显。部分单点 sensitivity 的区间仍跨 0，说明低假阳性区间仍需更多子集和更强模型优化来收窄不确定性。

## 6. 科研解释

hard-negative FPRED 在 pooled 外部验证中保持了跨子集收益，尤其在 0.125、0.25 和 0.5 FP/scan 的低假阳性区间提升更明显。这与 hard-negative mining 的目标一致：压低高置信假阳性，使有限 FP budget 下更早保留真阳性候选。

需要谨慎表述的是：当前结果仍属于 candidates_V2 false-positive reduction bridge evaluation，不等同于完整端到端 LUNA16 nodule detection leaderboard。与近期公开论文中 CPM 0.90 以上的完整 LUNA16 报告相比，本项目还需要继续扩大到更多 subset，并进一步优化低 FP/scan 区间。

## 7. 产物索引

- pooled merge report：`docs/world_frontier/luna16/pooled_subset1_subset2_external/baseline_merge_report.json`
- hard-negative merge report：`docs/world_frontier/luna16/pooled_subset1_subset2_external/hardneg_merge_report.json`
- baseline FROC summary：`docs/world_frontier/luna16/pooled_subset1_subset2_external/baseline_fixed10_nms_froc/froc_summary.csv`
- hard-negative FROC summary：`docs/world_frontier/luna16/pooled_subset1_subset2_external/hardneg_fixed10_nms_froc/froc_summary.csv`
- baseline bootstrap：`docs/world_frontier/luna16/pooled_subset1_subset2_external/baseline_fixed10_nms_bootstrap/bootstrap_froc_summary.json`
- hard-negative bootstrap：`docs/world_frontier/luna16/pooled_subset1_subset2_external/hardneg_fixed10_nms_bootstrap/bootstrap_froc_summary.json`
- paired gain bootstrap：`docs/world_frontier/luna16/pooled_subset1_subset2_external/paired_bootstrap_gain/paired_bootstrap_gain_summary.json`
- pooled figure：`docs/world_frontier/luna16/pooled_subset1_subset2_external/pooled_external_validation_froc_ci.png`
