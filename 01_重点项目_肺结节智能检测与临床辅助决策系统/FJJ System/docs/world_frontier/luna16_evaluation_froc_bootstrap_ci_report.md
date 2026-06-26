# LUNA16 subset0 evaluation FROC/CPM 置信区间报告

生成日期：2026-06-15

## 1. 目的

上一阶段完成了 subset0 的 calibration/evaluation 分区验证：NMS 半径只在 calibration 上选择，固定 10 mm 后在 evaluation 上报告 FROC/CPM。本阶段进一步对 evaluation fixed 10 mm NMS 结果进行 series-level bootstrap，补充 95% 置信区间。

这一步符合 CLAIM 2024 与 TRIPOD+AI 对模型性能估计不确定性的报告要求。由于肺结节检测数据具有同一 CT 内多个候选点聚类的结构，本报告以 CT series 为重采样单位，而不是把候选点当作相互独立样本。

## 2. 方法

新增脚本：

- `experiments/bootstrap_froc.py`
- `experiments/plot_froc_bootstrap_ci.py`

输入：

- predictions：`docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/evaluation_nms_sweep/radius_10/predictions.csv`
- series：`docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/evaluation_seriesuids.txt`
- annotations：`data/luna16/annotations.csv`

Bootstrap 设置：

| 项目 | 数值 |
|---|---:|
| resampling unit | CT series |
| evaluation series | 34 |
| evaluation annotations | 56 |
| predictions after fixed 10 mm NMS | 23436 |
| bootstrap repeats | 1000 |
| seed | 20260615 |

## 3. 结果

| 指标 | 点估计 | 95% CI |
|---|---:|---:|
| CPM | 0.6888 | 0.6026-0.7804 |
| Sens @0.125 FP/scan | 0.3214 | 0.1636-0.5660 |
| Sens @0.25 FP/scan | 0.4821 | 0.2833-0.6545 |
| Sens @0.5 FP/scan | 0.5714 | 0.4545-0.7170 |
| Sens @1 FP/scan | 0.7143 | 0.5536-0.8571 |
| Sens @2 FP/scan | 0.8571 | 0.7407-0.9333 |
| Sens @4 FP/scan | 0.9286 | 0.8333-0.9841 |
| Sens @8 FP/scan | 0.9464 | 0.8750-1.0000 |

图表：

- `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/evaluation_nms_sweep/radius_10/bootstrap/froc_bootstrap_ci.png`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/evaluation_nms_sweep/radius_10/bootstrap/froc_bootstrap_ci.pdf`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/evaluation_nms_sweep/radius_10/bootstrap/froc_bootstrap_ci.svg`

## 4. 科研解释

固定 10 mm NMS 在 evaluation split 上的 CPM 点估计为 0.6888，series-level bootstrap 95% CI 为 0.6026-0.7804。低 FP/scan 区间的不确定性较宽，尤其是 0.125 FP/scan 与 0.25 FP/scan，这与 evaluation split 仅包含 34 个 CT series 和 56 个官方 annotations 有关。

因此，当前结果可以证明后处理在 subset0 evaluation split 上有稳定改善趋势，但不能宣称已经达到完整 LUNA16 官方前沿水平。下一步仍需要扩展到更多 subset，并进行固定 10 mm NMS 的外部验证。

## 5. 可写入论文的审慎表述

可以写：

> 在 evaluation split 上，采用 calibration split 预先选定的 10 mm NMS 后，系统获得 CPM 0.6888（95% CI: 0.6026-0.7804）。低 FP/scan 区间仍存在较宽置信区间，提示后续需要更大规模公开子集验证。

不能写：

> 该系统在 LUNA16 上达到 CPM 0.6888。

原因：该结果仅来自 subset0 内的 evaluation split，而非完整 LUNA16 888 CT 官方评估。
