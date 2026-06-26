# Hard-negative FPRED 的 LUNA16 subset2 第三方外部验证报告

生成日期：2026-06-15

## 1. 目的

subset0 calibration hard-negative mining 在 subset0 evaluation 上显著提升 CPM，并在 subset1 外部重评估中仍保持迁移收益。本阶段继续下载并验证 LUNA16 subset2，用作第三个未参与训练、挖掘、NMS 半径选择或 subset1 验证的外部子集。

本报告当前只报告 hard-negative FPRED 在 subset2 上的绝对表现。baseline FPRED 在 subset2 上尚未重跑，因此本报告不声称 subset2 上相对 baseline 的提升幅度。

## 2. 数据准备

subset2 下载到 D 盘：

- zip: `D:/FJJ_luna16/subset2.zip`
- size: 7,257,937,108 bytes
- MD5: `685b484b085bcdb81c525f3b1bf97c51`
- checksum: passed

下载工程说明：

Zenodo 连接曾提前断开并产生 32MB 的不完整文件。为避免坏 zip 混入实验，`experiments/luna16_data_manager.py` 新增了下载大小校验：若 `.part` 文件大小与 manifest 期望不一致，脚本会保留 `.part` 并抛出错误，不生成最终 zip。随后通过 HTTP Range 断点续传完成完整下载与 MD5 校验。

subset2 解压与索引：

- data root: `D:/FJJ_luna16/subset2`
- CT index: `docs/world_frontier/luna16/subset2_ct_index.csv`
- series list: `docs/world_frontier/luna16/subset2_seriesuids.txt`
- readiness summary: `docs/world_frontier/luna16/subset2_external_validation/subset2_readiness_summary.json`

subset2 规模：

| 项目 | 数值 |
|---|---:|
| CT series | 89 |
| official annotations | 128 |
| candidates_V2 rows | 74,458 |
| candidates_V2 class=1 rows | 181 |

## 3. Hard-negative FPRED 全量评分

权重：

- `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/best_resnet_cbam_subset0.pth`

smoke scoring：

| 项目 | 数值 |
|---|---:|
| candidates | 128 |
| predictions | 128 |
| series | 1 |
| failures | 0 |

全量评分：

| 项目 | 数值 |
|---|---:|
| candidates | 74,458 |
| predictions | 74,458 |
| series | 89 |
| failures | 0 |
| elapsed_sec | 4,442.58 |

输出：

- `docs/world_frontier/luna16/subset2_external_validation/hardneg_candidates_v2_predictions.csv`
- `docs/world_frontier/luna16/subset2_external_validation/hardneg_candidates_v2_summary.json`
- `docs/world_frontier/luna16/subset2_external_validation/hardneg_candidates_v2_failures.json`

## 4. Raw FROC

| 指标 | 数值 |
|---|---:|
| scan_count | 89 |
| annotation_count | 128 |
| prediction_count | 74,458 |
| Sens @0.125 FP/scan | 0.328125 |
| Sens @0.25 FP/scan | 0.398438 |
| Sens @0.5 FP/scan | 0.570312 |
| Sens @1 FP/scan | 0.687500 |
| Sens @2 FP/scan | 0.789062 |
| Sens @4 FP/scan | 0.835938 |
| Sens @8 FP/scan | 0.859375 |
| CPM | 0.638393 |

## 5. Fixed 10 mm NMS FROC

fixed 10 mm NMS 来源：subset0 calibration split 预先选择；subset2 不重新调半径。

NMS：

| 项目 | 数值 |
|---|---:|
| input predictions | 74,458 |
| kept predictions | 54,614 |
| suppressed predictions | 19,844 |
| radius | 10 mm |

FROC：

| 指标 | 数值 |
|---|---:|
| scan_count | 89 |
| annotation_count | 128 |
| prediction_count | 54,614 |
| Sens @0.125 FP/scan | 0.351562 |
| Sens @0.25 FP/scan | 0.453125 |
| Sens @0.5 FP/scan | 0.625000 |
| Sens @1 FP/scan | 0.718750 |
| Sens @2 FP/scan | 0.789062 |
| Sens @4 FP/scan | 0.835938 |
| Sens @8 FP/scan | 0.882812 |
| CPM | 0.665179 |

## 6. Bootstrap 置信区间

对 hard-negative FPRED + fixed 10 mm NMS 的 subset2 结果进行 series-level bootstrap：

| 项目 | 数值 |
|---|---:|
| bootstrap repeats | 1000 |
| accepted repeats | 1000 |
| seed | 20260615 |
| series | 89 |
| annotations | 128 |
| predictions after NMS | 54,614 |

| 指标 | 点估计 | 95% CI |
|---|---:|---:|
| CPM | 0.665179 | 0.589155-0.749415 |
| Sens @0.125 FP/scan | 0.351562 | 0.264045-0.453704 |
| Sens @0.25 FP/scan | 0.453125 | 0.333333-0.623853 |
| Sens @0.5 FP/scan | 0.625000 | 0.511811-0.750000 |
| Sens @1 FP/scan | 0.718750 | 0.622642-0.805556 |
| Sens @2 FP/scan | 0.789062 | 0.708609-0.868132 |
| Sens @4 FP/scan | 0.835938 | 0.757576-0.898438 |
| Sens @8 FP/scan | 0.882812 | 0.800000-0.947917 |

图表：

- `docs/world_frontier/luna16/subset2_external_validation/hardneg_fixed10_nms_bootstrap/hardneg_subset2_froc_bootstrap_ci.png`

## 7. 科研解释

hard-negative FPRED 在 subset2 上获得 fixed 10 mm NMS CPM 0.6652（95% CI: 0.5892-0.7494），高于 subset1 hard-negative fixed 10 mm NMS CPM 0.6161。这说明模型在第二个外部子集上并未崩溃，且低 FP/scan 区间表现有一定稳定性。

但本阶段尚未重跑 baseline FPRED 在 subset2 上的完整 FROC，因此不能写“subset2 上 hard-negative 相比 baseline 提升多少”。当前能写的是：

> 在第三个未参与训练或调参的外部子集 subset2 上，hard-negative FPRED + fixed 10 mm NMS 获得 CPM 0.6652（95% CI: 0.5892-0.7494）。

## 8. 下一步

1. 重跑 baseline FPRED 在 subset2 上的全量 candidates_V2 FROC，用于严格相对比较。
2. 汇总 subset1+subset2 的 external pooled FROC/CPM 与 bootstrap CI。
3. 若 subset2 baseline 对比仍显示 hard-negative 优势，再启动 subset3 或完整官方 submission 格式准备。
4. 针对 0.125/0.25 FP/scan 继续做概率校准与更严格 hard-negative split。
