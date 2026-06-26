# LUNA16 subset0 NMS 半径分区验证报告

生成日期：2026-06-15

## 1. 目的

上一阶段在 subset0 全量 89 个 CT series 上扫描 NMS 半径，发现 10 mm 半径可将 candidates_V2 bridge CPM 从 0.6020 提升到 0.6390。但该结果在同一数据上完成“选半径”和“报告性能”，存在调参乐观偏倚。本阶段将 subset0 按官方 annotation 数进行 calibration/evaluation 划分：只在 calibration 上选择 NMS 半径，再在 evaluation 上报告固定半径结果。

该设计更符合 TRIPOD+AI 与 CLAIM 2024 对透明数据分区、阈值/模型选择和测试报告的要求。

## 2. 分区方式

新增脚本：

- `experiments/make_series_calibration_split.py`
- `experiments/plot_split_nms_validation.py`

划分策略：

1. 读取 subset0 的 89 个 series。
2. 统计每个 series 的官方 annotation 数。
3. 按 annotation 数从高到低贪心分配，平衡 calibration/evaluation 的 annotation 总量。

结果：

| 分区 | series | annotations |
|---|---:|---:|
| calibration | 55 | 56 |
| evaluation | 34 | 56 |
| total | 89 | 112 |

## 3. Calibration 半径选择

| NMS radius (mm) | predictions | CPM | Sens @0.25 FP/scan |
|---:|---:|---:|---:|
| 0 | 46704 | 0.568878 | 0.214286 |
| 5 | 46519 | 0.573980 | 0.214286 |
| 10 | 33662 | 0.584184 | 0.232143 |
| 15 | 20601 | 0.571429 | 0.214286 |
| 20 | 12735 | 0.558673 | 0.214286 |
| 30 | 5864 | 0.571429 | 0.214286 |

Calibration 选择：

```text
NMS radius = 10 mm
```

## 4. Evaluation 固定半径结果

只报告 calibration 选定的 10 mm 半径作为固定后处理结果：

| Evaluation setting | predictions | CPM | Sens @0.25 FP/scan |
|---|---:|---:|---:|
| no NMS | 32431 | 0.619898 | 0.321429 |
| fixed 10 mm NMS | 23436 | 0.688776 | 0.482143 |

提升：

```text
absolute CPM gain = 0.068878
relative CPM gain = 11.11%
absolute Sens @0.25 FP/scan gain = 0.160714
```

说明：evaluation 上若事后扫描全部半径，20 mm 半径 CPM 更高；但为了避免 evaluation 调参，本报告将 10 mm 作为固定半径报告。这一点在论文中必须明确。

图表：

- `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/split_valid_nms.png`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/split_valid_nms.pdf`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/split_valid_nms.svg`

## 5. 可写入论文的审慎表述

可以写：

> 为降低同一数据集上调参带来的乐观偏倚，我们按官方 annotation 数将 LUNA16 subset0 划分为 calibration 与 evaluation 两部分。NMS 半径仅在 calibration 上选择，10 mm 半径在 evaluation 上将 CPM 从 0.6199 提升至 0.6888，并将 0.25 FP/scan sensitivity 从 0.3214 提升至 0.4821。

不能写：

> 20 mm 是 evaluation 上最优半径，因此最终选择 20 mm。

原因：20 mm 是查看 evaluation sweep 后得到的事后选择，不符合固定后处理参数的评估逻辑。

## 6. 下一步

1. 使用 calibration 选定的 10 mm NMS 继续做 hard negative mining。
2. 在 subset1/subset2 上进行固定 10 mm 外部验证。
3. 将 NMS、概率校准和 FPRED retraining 的贡献分开做消融。
