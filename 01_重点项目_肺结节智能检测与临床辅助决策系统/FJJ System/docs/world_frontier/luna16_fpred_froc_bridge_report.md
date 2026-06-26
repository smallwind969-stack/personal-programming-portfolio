# LUNA16 subset0 FPRED-FROC 桥接评估报告

生成日期：2026-06-14

## 1. 目的

上一阶段已经证明 FPRED 分支在 subset0 独立候选测试集上具有较高 AUC，并补充了 bootstrap 置信区间。本阶段进一步把 FPRED 输出回贴到 LUNA16 世界坐标，导出 LUNA-style prediction CSV，并用 FROC/CPM evaluator 做候选池驱动的检测桥接评估。

这一步的意义是：从“候选分类模型表现”前进到“检测评价接口表现”。它仍然不是完整官方 LUNA16 detection track，因为候选池仅来自当前已抽取的 subset0/test 103 个 candidates，而不是完整 888 CT 的端到端候选生成结果。

## 2. 新增与修复

新增脚本：

- `experiments/export_fpred_luna_predictions.py`

修复脚本：

- `experiments/froc_eval.py`

修复内容：当传入 subset seriesuids 时，FROC evaluator 现在会同时过滤 annotations 和 predictions，summary 中的 `annotation_count` 也使用过滤后的真实数量。此前 CPM 计算已在内部过滤，但 summary 仍可能显示全量 annotations，容易误导。

## 3. 数据流

```text
subset0_test_patch_candidates_128.csv
        + patch_manifest.json
        + fpred_resnet_finetuned_test_predictions.csv
        -> fpred_luna_style_predictions.csv
        -> froc_eval.py
        -> froc_summary.csv / froc_points.csv / fpred_froc_bridge.png
```

导出的 LUNA-style prediction CSV 字段：

```text
seriesuid, coordX, coordY, coordZ, probability
```

坐标来自原始 LUNA16 candidates CSV；概率来自微调后的 FPRED 模型；脚本会校验 candidate、manifest、prediction 三方的 `seriesuid/class/patch` 顺序一致。

## 4. 结果

| 指标 | 数值 |
|---|---:|
| scan_count | 10 |
| annotation_count | 7 |
| prediction_count | 103 |
| sensitivity_at_0.125_fp_per_scan | 0.857143 |
| sensitivity_at_0.25_fp_per_scan | 0.857143 |
| sensitivity_at_0.5_fp_per_scan | 1.000000 |
| sensitivity_at_1.0_fp_per_scan | 1.000000 |
| sensitivity_at_2.0_fp_per_scan | 1.000000 |
| sensitivity_at_4.0_fp_per_scan | 1.000000 |
| sensitivity_at_8.0_fp_per_scan | 1.000000 |
| bridge CPM | 0.959184 |

图表：

- `docs/world_frontier/luna16/patch_test_103/froc_bridge/fpred_froc_bridge.png`
- `docs/world_frontier/luna16/patch_test_103/froc_bridge/fpred_froc_bridge.pdf`
- `docs/world_frontier/luna16/patch_test_103/froc_bridge/fpred_froc_bridge.svg`

## 5. 审慎解释

可以写：

> 在 subset0/test 的候选池桥接评估中，微调后的 FPRED 分支导出的 LUNA-style predictions 在 10 个 series、7 个官方 annotation 上获得 bridge CPM 0.9592，提示该分支在候选坐标回贴后能够保持较高的 FROC 敏感度。

不能写：

> 本系统在 LUNA16 官方完整 detection track 上获得 CPM 0.9592。

原因：当前评估没有覆盖完整 888 CT，也没有运行完整候选生成器，只对已经抽取并推理过的 subset0/test candidates 进行桥接验证。

## 6. 下一步

1. 扩展更多 LUNA16 subset，增加 series 和 annotation 数。
2. 对每个可用 series 抽取更完整的 candidates_V2，而不只使用采样 candidates。
3. 批量运行 FPRED 推理，导出完整 subset-level LUNA-style CSV。
4. 用同一 `froc_eval.py` 汇总 subset-level FROC/CPM，并与公开基线进行对照。
5. 最终目标是完整 detection track 的 candidate generation + FPRED + FROC/CPM，而不是只停留在 FPRED 分类。
