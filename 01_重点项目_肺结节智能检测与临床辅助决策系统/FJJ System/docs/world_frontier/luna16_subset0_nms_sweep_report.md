# LUNA16 subset0 candidates_V2 NMS-FROC 扫描报告

生成日期：2026-06-15

## 1. 目的

上一阶段在 LUNA16 subset0 全部 89 个 CT series 上运行完整 candidates_V2 FPRED 评分，得到 bridge CPM 0.6020。低 FP/scan 区间表现不足，提示候选排序和重复候选控制是主要瓶颈。本阶段对 LUNA-style prediction CSV 增加每个 series 内的 3D NMS 后处理，并扫描不同 NMS 半径，观察 CPM 与低 FP/scan sensitivity 的变化。

## 2. 方法

新增脚本：

- `experiments/luna_prediction_nms.py`
- `experiments/nms_froc_sweep.py`
- `experiments/plot_nms_froc_sweep.py`

NMS 策略：

1. 按 `seriesuid` 分组。
2. 每个 series 内按 `probability` 从高到低排序。
3. 依次保留高概率候选，并抑制给定半径内的低概率候选。
4. 输出仍为 LUNA-style CSV：`seriesuid,coordX,coordY,coordZ,probability`。

扫描半径：

```text
0, 5, 10, 15, 20, 30 mm
```

## 3. 结果

| NMS radius (mm) | predictions | suppressed | Sens @0.25 FP/scan | Sens @1.0 FP/scan | CPM |
|---:|---:|---:|---:|---:|---:|
| 0 | 79135 | 0 | 0.258929 | 0.625000 | 0.602041 |
| 5 | 78848 | 287 | 0.258929 | 0.633929 | 0.605867 |
| 10 | 57098 | 22037 | 0.375000 | 0.696429 | 0.639031 |
| 15 | 34699 | 44436 | 0.366071 | 0.732143 | 0.636480 |
| 20 | 21478 | 57657 | 0.366071 | 0.714286 | 0.630102 |
| 30 | 9757 | 69378 | 0.383929 | 0.723214 | 0.631378 |

最佳半径：

```text
10 mm
```

最佳 CPM：

```text
0.639031
```

相对无 NMS：

```text
absolute CPM gain = 0.036990
relative CPM gain = 6.14%
```

图表：

- `docs/world_frontier/luna16/subset0_full_candidates_stream/nms_sweep/nms_froc_sweep.png`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/nms_sweep/nms_froc_sweep.pdf`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/nms_sweep/nms_froc_sweep.svg`

## 4. 科研解释

适度 NMS 能减少重复候选和部分近邻假阳性，从而提升低 FP/scan 区间表现。10 mm 半径使 CPM 从 0.6020 提升到 0.6390，并将 0.25 FP/scan sensitivity 从 0.2589 提升到 0.3750。半径继续增大后，prediction_count 大幅下降，但 CPM 没有继续提升，说明过强 NMS 可能抑制真实结节附近有用候选。

这是一项后处理工程优化，不应被包装成模型本体能力提升。更严谨的下一步是：在 validation subset 上选择 NMS 半径，再在独立 subset 上报告固定半径结果。

## 5. 可写入论文的审慎表述

可以写：

> 在 LUNA16 subset0 全候选桥接评估中，3D NMS 后处理改善了低 FP/scan 区间表现；10 mm NMS 半径将 candidates_V2 bridge CPM 从 0.6020 提升至 0.6390，并将 0.25 FP/scan sensitivity 从 0.2589 提升至 0.3750。

不能写：

> 10 mm 是最终最优 NMS 半径，并且该结果等同于完整官方 LUNA16 测试成绩。

原因：本轮半径选择和评估都在 subset0 上完成，尚未做跨 subset 的独立验证。

## 6. 下一步

1. 将 subset0 划分为 calibration/evaluation series，避免同一 subset 内选半径又报告半径。
2. 基于 NMS 后的高置信 FP 做 hard negative mining。
3. 对概率进行温度缩放或 isotonic calibration，改善排序。
4. 在可用磁盘允许时扩展 subset1/subset2，做固定 NMS 半径外部验证。
