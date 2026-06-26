# LUNA16 subset1 外部验证报告

生成日期：2026-06-15

## 1. 目的

上一阶段在 LUNA16 subset0 内完成了 calibration/evaluation 分区验证：NMS 半径只在 calibration 上选择，固定 10 mm 后在 evaluation 上报告 CPM 0.6888（95% CI: 0.6026-0.7804）。本阶段将该固定 10 mm NMS 迁移到新的 LUNA16 subset1，作为外部子集验证。

该实验用于回答一个更严格的问题：subset0 上选出的后处理策略能否迁移到未参与选择的 CT 子集。

## 2. 数据与可复现路径

subset1 数据下载到 D 盘，以避免 C 盘空间不足：

- data root: `D:/FJJ_luna16`
- zip: `D:/FJJ_luna16/subset1.zip`
- MD5: `2eda28bb123543074f5cd849499b87ff`，已通过校验
- extracted CT: 89 series
- series list: `docs/world_frontier/luna16/subset1_seriesuids.txt`
- CT index: `docs/world_frontier/luna16/subset1_ct_index.csv`
- readiness summary: `docs/world_frontier/luna16/subset1_external_validation/subset1_readiness_summary.json`

subset1 规模：

| 项目 | 数值 |
|---|---:|
| CT series | 89 |
| official annotations | 128 |
| candidates_V2 rows | 71,012 |
| candidates_V2 class=1 rows | 170 |

## 3. 工程升级

为支持 subset1 这种 6GB 级文件，本阶段增强了 `experiments/luna16_data_manager.py`：

- 新增 `.part` 临时文件下载。
- 新增 HTTP Range 断点续传请求。
- 新增 `--resume-download` 命令行参数。
- 保留 MD5 校验与 annotation/sample submission schema validation。

新增/更新测试：

- `tests/test_luna16_data_manager.py::test_partial_download_path_keeps_final_file_name_visible`
- `tests/test_luna16_data_manager.py::test_build_download_request_uses_range_when_partial_exists`
- `tests/test_luna16_data_manager.py::test_build_download_request_restarts_when_overwrite`

## 4. FPRED 全量候选评分

使用 subset0 微调得到的 FPRED 权重：

- `docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth`

先进行 smoke scoring：

- candidates: 128
- predictions: 128
- series: 1
- failures: 0
- output: `docs/world_frontier/luna16/subset1_external_validation/smoke_predictions.csv`

随后进行 subset1 全量 candidates_V2 评分：

- predictions: 71,012
- series: 89
- failures: 0
- output: `docs/world_frontier/luna16/subset1_external_validation/fpred_candidates_v2_predictions.csv`

评分过程使用 checkpoint/resume。中途两次达到命令超时，但 checkpoint 文件保留并最终完成全量预测。

## 5. Raw FROC

输入：

- annotations: `data/luna16/annotations.csv`
- predictions: `docs/world_frontier/luna16/subset1_external_validation/fpred_candidates_v2_predictions.csv`
- seriesuids: `docs/world_frontier/luna16/subset1_seriesuids.txt`

结果：

| 指标 | 数值 |
|---|---:|
| scan_count | 89 |
| annotation_count | 128 |
| prediction_count | 71,012 |
| Sens @0.125 FP/scan | 0.179688 |
| Sens @0.25 FP/scan | 0.351562 |
| Sens @0.5 FP/scan | 0.476562 |
| Sens @1 FP/scan | 0.554688 |
| Sens @2 FP/scan | 0.679688 |
| Sens @4 FP/scan | 0.773438 |
| Sens @8 FP/scan | 0.859375 |
| CPM | 0.553571 |

## 6. Fixed 10 mm NMS 外部验证

固定 10 mm NMS 来源：subset0 calibration split 预先选择；subset1 不重新调半径。

NMS 结果：

| 项目 | 数值 |
|---|---:|
| input predictions | 71,012 |
| kept predictions | 51,599 |
| suppressed predictions | 19,413 |
| series | 89 |
| radius | 10 mm |

FROC 结果：

| 指标 | raw | fixed 10 mm NMS | 变化 |
|---|---:|---:|---:|
| CPM | 0.553571 | 0.579241 | +0.025670 |
| Sens @0.125 FP/scan | 0.179688 | 0.242188 | +0.062500 |
| Sens @0.25 FP/scan | 0.351562 | 0.367188 | +0.015626 |
| Sens @0.5 FP/scan | 0.476562 | 0.500000 | +0.023438 |
| Sens @1 FP/scan | 0.554688 | 0.578125 | +0.023437 |
| Sens @2 FP/scan | 0.679688 | 0.726562 | +0.046874 |
| Sens @4 FP/scan | 0.773438 | 0.789062 | +0.015624 |
| Sens @8 FP/scan | 0.859375 | 0.851562 | -0.007813 |

## 7. Bootstrap 置信区间

对 fixed 10 mm NMS 结果进行 series-level bootstrap：

| 项目 | 数值 |
|---|---:|
| bootstrap repeats | 1000 |
| accepted repeats | 1000 |
| seed | 20260615 |
| resampling unit | CT series |
| series | 89 |
| annotations | 128 |
| predictions | 51,599 |

| 指标 | 点估计 | 95% CI |
|---|---:|---:|
| CPM | 0.579241 | 0.458172-0.683761 |
| Sens @0.125 FP/scan | 0.242188 | 0.020833-0.457143 |
| Sens @0.25 FP/scan | 0.367188 | 0.166667-0.548673 |
| Sens @0.5 FP/scan | 0.500000 | 0.335664-0.607143 |
| Sens @1 FP/scan | 0.578125 | 0.465649-0.697674 |
| Sens @2 FP/scan | 0.726562 | 0.594595-0.810606 |
| Sens @4 FP/scan | 0.789062 | 0.708029-0.859155 |
| Sens @8 FP/scan | 0.851562 | 0.787097-0.927007 |

图表：

- `docs/world_frontier/luna16/subset1_external_validation/fixed10_nms_bootstrap/subset1_froc_bootstrap_ci.png`

## 8. 科研解释

fixed 10 mm NMS 在 subset1 上从 CPM 0.5536 提升到 0.5792，说明 subset0 calibration 选出的后处理策略具有一定迁移收益。但提升幅度小于 subset0 evaluation，并且 CPM 95% CI 较宽，低 FP/scan 区间仍然不稳定。

该结果比只做 subset0 更成熟，因为它提供了一个真正未参与 NMS 半径选择的外部子集验证。同时，它也更清楚地暴露了当前系统距离 LUNA16 前沿水平的差距：低 FP/scan sensitivity 和跨子集泛化仍然是下一步主攻方向。

## 9. 可写入结题/论文的审慎表述

可以写：

> 在未参与 NMS 半径选择的 LUNA16 subset1 上，固定 10 mm NMS 将 CPM 从 0.5536 提升至 0.5792，并将 0.125 FP/scan sensitivity 从 0.1797 提升至 0.2422。series-level bootstrap 显示 CPM 95% CI 为 0.4582-0.6838。

不能写：

> fixed 10 mm NMS 已证明达到 LUNA16 前沿水平。

原因：subset1 外部验证显示有迁移收益，但绝对 CPM 与近年前沿方法仍有明显差距。

## 10. 下一步

1. 对 subset1 的高分假阳性进行 hard-negative mining。
2. 在不泄露 evaluation/subset1 测试信息的前提下重新微调 FPRED。
3. 固定 10 mm NMS 与 retrained FPRED 做消融比较。
4. 继续下载 subset2 或构建 subset0+subset1 calibration / subset2 evaluation 的三阶段验证。
