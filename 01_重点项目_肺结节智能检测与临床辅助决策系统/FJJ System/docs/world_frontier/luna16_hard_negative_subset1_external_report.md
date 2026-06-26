# Hard-negative FPRED 的 LUNA16 subset1 外部重评估报告

生成日期：2026-06-15

## 1. 目的

上一阶段 hard-negative mining 在 subset0 calibration/evaluation 分区下显著提升 fixed 10 mm NMS FROC：subset0 evaluation CPM 从 0.6888 提升至 0.8648。但由于 hard negatives 来自同一 subset0 的 calibration split，该结果仍需要外部子集验证。

本阶段使用 hard-negative FPRED 权重对 LUNA16 subset1 全量 candidates_V2 重新评分，并固定使用 subset0 calibration 预先确定的 10 mm NMS，不在 subset1 上重新调参。

## 2. 数据与权重

数据：

- subset1 CT series: 89
- official annotations: 128
- candidates_V2 rows: 71,012
- data root: `D:/FJJ_luna16`
- series list: `docs/world_frontier/luna16/subset1_seriesuids.txt`

权重：

- baseline FPRED: `docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth`
- hard-negative FPRED: `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/best_resnet_cbam_subset0.pth`

重要边界：

- subset1 未参与 hard-negative mining。
- subset1 未参与 hard-negative FPRED 训练。
- subset1 未用于 NMS 半径选择。

## 3. 工程修复

subset1 hard-negative 重评分过程中发现 `experiments/score_luna16_candidates_stream.py` 存在跨 series 缓存 CT 图像与归一化数组的问题。在长时间全量评分时，内存会随 series 累积，最终触发 `numpy.core._exceptions._ArrayMemoryError`。

修复：

- 移除跨 series 的 `images` 和 `normalized_images` 缓存。
- 每个 series 独立加载、归一化、评分，处理完即可释放。
- 新增 `--progress-summary`，每处理完一个 series 写入轻量 JSON 进度文件，便于长任务断点审计。

相关测试：

- `tests/test_score_luna16_candidates_stream.py`

## 4. 全量评分

hard-negative FPRED 对 subset1 全量 candidates_V2 评分：

| 项目 | 数值 |
|---|---:|
| candidates | 71,012 |
| predictions | 71,012 |
| series | 89 |
| failures | 0 |
| final predictions | `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/subset1_candidates_v2_predictions.csv` |

评分中途两次命令超时，第三段暴露内存问题；修复后通过 checkpoint/resume 完成最终 predictions 写出。

## 5. subset1 raw FROC 对比

| 指标 | baseline FPRED raw | hard-negative FPRED raw | 变化 |
|---|---:|---:|---:|
| CPM | 0.553571 | 0.577009 | +0.023438 |
| Sens @0.125 FP/scan | 0.179688 | 0.242188 | +0.062500 |
| Sens @0.25 FP/scan | 0.351562 | 0.367188 | +0.015626 |
| Sens @0.5 FP/scan | 0.476562 | 0.460938 | -0.015624 |
| Sens @1 FP/scan | 0.554688 | 0.609375 | +0.054687 |
| Sens @2 FP/scan | 0.679688 | 0.695312 | +0.015624 |
| Sens @4 FP/scan | 0.773438 | 0.804688 | +0.031250 |
| Sens @8 FP/scan | 0.859375 | 0.859375 | 0.000000 |

## 6. subset1 fixed 10 mm NMS 对比

fixed 10 mm NMS 来源：subset0 calibration split 预先选择；subset1 不重新调半径。

| 指标 | baseline FPRED + fixed 10 mm NMS | hard-negative FPRED + fixed 10 mm NMS | 变化 |
|---|---:|---:|---:|
| predictions after NMS | 51,599 | 51,573 | -26 |
| CPM | 0.579241 | 0.616071 | +0.036830 |
| Sens @0.125 FP/scan | 0.242188 | 0.367188 | +0.125000 |
| Sens @0.25 FP/scan | 0.367188 | 0.429688 | +0.062500 |
| Sens @0.5 FP/scan | 0.500000 | 0.484375 | -0.015625 |
| Sens @1 FP/scan | 0.578125 | 0.609375 | +0.031250 |
| Sens @2 FP/scan | 0.726562 | 0.718750 | -0.007812 |
| Sens @4 FP/scan | 0.789062 | 0.828125 | +0.039063 |
| Sens @8 FP/scan | 0.851562 | 0.875000 | +0.023438 |

## 7. Bootstrap 置信区间

对 hard-negative FPRED + fixed 10 mm NMS 的 subset1 结果进行 series-level bootstrap：

| 项目 | 数值 |
|---|---:|
| bootstrap repeats | 1000 |
| accepted repeats | 1000 |
| seed | 20260615 |
| series | 89 |
| annotations | 128 |
| predictions after NMS | 51,573 |

| 指标 | 点估计 | 95% CI |
|---|---:|---:|
| CPM | 0.616071 | 0.521669-0.709890 |
| Sens @0.125 FP/scan | 0.367188 | 0.201613-0.490741 |
| Sens @0.25 FP/scan | 0.429688 | 0.303030-0.547368 |
| Sens @0.5 FP/scan | 0.484375 | 0.380952-0.635659 |
| Sens @1 FP/scan | 0.609375 | 0.506494-0.736842 |
| Sens @2 FP/scan | 0.718750 | 0.610390-0.838235 |
| Sens @4 FP/scan | 0.828125 | 0.731884-0.895161 |
| Sens @8 FP/scan | 0.875000 | 0.797101-0.924528 |

图表：

- `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/subset1_fixed10_nms_bootstrap/hardneg_subset1_froc_bootstrap_ci.png`

## 8. 科研解释

hard-negative FPRED 在未参与训练和调参的 subset1 上仍然提升了 fixed 10 mm NMS CPM：从 0.5792 提升至 0.6161。低假阳性区间提升更明显，0.125 FP/scan sensitivity 从 0.2422 提升至 0.3672，0.25 FP/scan sensitivity 从 0.3672 提升至 0.4297。

这说明 subset0 calibration hard-negative mining 学到的排序改进具有一定跨子集迁移性，不只是同 subset 内 evaluation 的偶然提升。但该提升幅度远小于 subset0 evaluation 上的 0.8648，提示模型仍存在跨子集域差异或候选分布差异。

## 9. 可写入结题/论文的审慎表述

可以写：

> 在未参与训练、hard-negative mining 或 NMS 半径选择的 LUNA16 subset1 上，hard-negative FPRED + fixed 10 mm NMS 将 CPM 从 0.5792 提升至 0.6161，并将 0.125 FP/scan sensitivity 从 0.2422 提升至 0.3672。series-level bootstrap 显示 CPM 95% CI 为 0.5217-0.7099。

不能写：

> hard-negative FPRED 已经达到完整 LUNA16 世界前沿。

原因：subset1 虽然证明了跨子集提升，但绝对 CPM 仍明显低于近年完整 LUNA16 强方法，且尚未覆盖 subset2-9 或官方完整提交。

## 10. 下一步

1. 下载 subset2，作为第三个未参与训练/调参的外部子集。
2. 对 subset2 固定报告 baseline FPRED 与 hard-negative FPRED 的 raw / fixed 10 mm NMS FROC。
3. 若 subset2 仍提升，再合并 subset1+subset2 做跨子集统计报告。
4. 继续 hard-negative mining 但必须重新设计三阶段 split：calibration mining / validation selection / external testing。
