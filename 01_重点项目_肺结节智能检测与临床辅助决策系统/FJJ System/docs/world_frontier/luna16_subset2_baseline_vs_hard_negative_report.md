# LUNA16 subset2 baseline FPRED vs hard-negative FPRED 对比报告

生成日期：2026-06-15

## 1. 目的

上一阶段已经在 LUNA16 subset2 上完成 hard-negative FPRED 的第三方外部验证，但当时尚未重跑 baseline FPRED，因此只能报告 hard-negative 模型的绝对表现。本阶段补齐 baseline FPRED 在 subset2 上的全量 candidates_V2 评分、FROC/CPM、fixed 10 mm NMS 和 bootstrap CI，从而形成同一外部子集上的严格对比。

subset2 未参与：

- baseline FPRED 微调；
- hard-negative mining；
- hard-negative FPRED 微调；
- NMS 半径选择；
- subset1 外部验证。

因此，subset2 是当前最严格的第三方外部子集。

## 2. 数据

| 项目 | 数值 |
|---|---:|
| CT series | 89 |
| official annotations | 128 |
| candidates_V2 rows | 74,458 |
| candidates_V2 class=1 rows | 181 |

数据路径：

- series list: `docs/world_frontier/luna16/subset2_seriesuids.txt`
- CT index: `docs/world_frontier/luna16/subset2_ct_index.csv`
- readiness summary: `docs/world_frontier/luna16/subset2_external_validation/subset2_readiness_summary.json`

## 3. 模型与预测

| 模型 | 权重 | predictions | failures |
|---|---|---:|---:|
| baseline FPRED | `docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth` | 74,458 | 0 |
| hard-negative FPRED | `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/best_resnet_cbam_subset0.pth` | 74,458 | 0 |

baseline 输出：

- `docs/world_frontier/luna16/subset2_external_validation/baseline_candidates_v2_predictions.csv`
- `docs/world_frontier/luna16/subset2_external_validation/baseline_candidates_v2_summary.json`
- `docs/world_frontier/luna16/subset2_external_validation/baseline_candidates_v2_failures.json`

hard-negative 输出：

- `docs/world_frontier/luna16/subset2_external_validation/hardneg_candidates_v2_predictions.csv`
- `docs/world_frontier/luna16/subset2_external_validation/hardneg_candidates_v2_summary.json`
- `docs/world_frontier/luna16/subset2_external_validation/hardneg_candidates_v2_failures.json`

## 4. Raw FROC 对比

| 指标 | baseline FPRED raw | hard-negative FPRED raw | 变化 |
|---|---:|---:|---:|
| CPM | 0.535714 | 0.638393 | +0.102679 |
| Sens @0.125 FP/scan | 0.203125 | 0.328125 | +0.125000 |
| Sens @0.25 FP/scan | 0.281250 | 0.398438 | +0.117188 |
| Sens @0.5 FP/scan | 0.359375 | 0.570312 | +0.210937 |
| Sens @1 FP/scan | 0.539062 | 0.687500 | +0.148438 |
| Sens @2 FP/scan | 0.687500 | 0.789062 | +0.101562 |
| Sens @4 FP/scan | 0.796875 | 0.835938 | +0.039063 |
| Sens @8 FP/scan | 0.882812 | 0.859375 | -0.023437 |

## 5. Fixed 10 mm NMS 对比

fixed 10 mm NMS 来源：subset0 calibration split 预先选择；subset2 不重新调半径。

| 项目 | baseline FPRED | hard-negative FPRED |
|---|---:|---:|
| input predictions | 74,458 | 74,458 |
| predictions after NMS | 54,726 | 54,614 |
| suppressed predictions | 19,732 | 19,844 |

| 指标 | baseline + fixed 10 mm NMS | hard-negative + fixed 10 mm NMS | 变化 |
|---|---:|---:|---:|
| CPM | 0.544643 | 0.665179 | +0.120536 |
| Sens @0.125 FP/scan | 0.203125 | 0.351562 | +0.148437 |
| Sens @0.25 FP/scan | 0.281250 | 0.453125 | +0.171875 |
| Sens @0.5 FP/scan | 0.390625 | 0.625000 | +0.234375 |
| Sens @1 FP/scan | 0.554688 | 0.718750 | +0.164062 |
| Sens @2 FP/scan | 0.695312 | 0.789062 | +0.093750 |
| Sens @4 FP/scan | 0.812500 | 0.835938 | +0.023438 |
| Sens @8 FP/scan | 0.875000 | 0.882812 | +0.007812 |

## 6. Bootstrap 置信区间

两组均采用 series-level bootstrap，重复 1000 次，seed = 20260615。

| 模型 | CPM | 95% CI |
|---|---:|---:|
| baseline + fixed 10 mm NMS | 0.544643 | 0.420635-0.675958 |
| hard-negative + fixed 10 mm NMS | 0.665179 | 0.589155-0.749415 |

关键低 FP/scan 指标：

| 指标 | baseline 点估计 | baseline 95% CI | hard-negative 点估计 | hard-negative 95% CI |
|---|---:|---:|---:|---:|
| Sens @0.125 FP/scan | 0.203125 | 0.049689-0.369748 | 0.351562 | 0.264045-0.453704 |
| Sens @0.25 FP/scan | 0.281250 | 0.152000-0.494505 | 0.453125 | 0.333333-0.623853 |
| Sens @0.5 FP/scan | 0.390625 | 0.258741-0.601504 | 0.625000 | 0.511811-0.750000 |

图表：

- baseline CI: `docs/world_frontier/luna16/subset2_external_validation/baseline_fixed10_nms_bootstrap/baseline_subset2_froc_bootstrap_ci.png`
- hard-negative CI: `docs/world_frontier/luna16/subset2_external_validation/hardneg_fixed10_nms_bootstrap/hardneg_subset2_froc_bootstrap_ci.png`

## 7. 科研解释

在完全外部的 subset2 上，hard-negative FPRED 相比 baseline FPRED 有明确提升：fixed 10 mm NMS CPM 从 0.5446 提升至 0.6652，绝对提升 0.1205。低 FP/scan 区间提升尤其明显，0.25 FP/scan sensitivity 从 0.2813 提升至 0.4531。

这说明 subset0 calibration 中挖掘的 hard negatives 不仅改善 subset0 evaluation，也能迁移到 subset1 和 subset2。当前最稳妥的结论是：

> Hard-negative mining 改善了跨子集候选排序，尤其在低 FP/scan 区间提升明显。

但仍不能写成完整 LUNA16 世界前沿，原因是：

1. 目前只覆盖 subset0、subset1、subset2，尚非完整 888 CT。
2. 当前仍基于 candidates_V2 + FPRED bridge，不是完整端到端 detection 官方提交。
3. subset2 hard-negative CPM 0.6652 仍低于近年完整 LUNA16 强方法。

## 8. 可写入结题/论文的审慎表述

可以写：

> 在未参与训练、hard-negative mining 或 NMS 半径选择的 LUNA16 subset2 上，hard-negative FPRED + fixed 10 mm NMS 将 CPM 从 0.5446 提升至 0.6652，并将 0.25 FP/scan sensitivity 从 0.2813 提升至 0.4531。series-level bootstrap 显示 hard-negative CPM 95% CI 为 0.5892-0.7494。

不能写：

> 该方法达到完整 LUNA16 世界前沿。

原因：该结果仍是 subset2 外部子集验证，不是完整 LUNA16 官方提交。

## 9. 下一步

1. 合并 subset1+subset2 做 pooled external FROC/CPM 与 bootstrap CI。
2. 下载 subset3，验证 hard-negative 提升是否继续稳定。
3. 做概率校准或阈值校准，专门优化 0.125/0.25 FP/scan 区间。
4. 将 subset0 calibration/evaluation、subset1、subset2 的三阶段证据写入结题报告和论文实验部分。
