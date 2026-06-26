# LUNA16 subset0 完整 candidates_V2 FPRED-FROC 报告

生成日期：2026-06-14

## 1. 目的

本阶段将 FPRED 评估从 10 个 series 扩展到已解压的 LUNA16 subset0 全部 89 个 CT series。实验使用 `candidates_V2.csv` 中属于 subset0 的完整候选池，共 79135 个候选位置，并用微调后的 ResNet-CBAM FPRED 模型进行流式 patch 推理，最终输出 LUNA-style prediction CSV 与 FROC/CPM。

这一步是从“局部候选池验证”走向“公开数据子集级检测评价”的关键升级。它仍不是完整 LUNA16 官方 888 CT 结果，但已经覆盖 subset0 全量 CT，而不再只是 10 个测试 series。

## 2. 工程改进

本阶段修复和增强了长任务链路：

- `score_luna16_candidates_stream.py` 增加 `--resume-from`，支持从已有 prediction CSV 跳过已评分候选。
- checkpoint 写盘会自动创建父目录，避免长任务因目录不存在而失败。
- FROC evaluator 从逐阈值重复扫描改为按置信度降序增量 sweep，使 79135 条 predictions 的 FROC 从超时变为约数秒完成。
- 保留 `evaluate_froc_slow` 作为单元测试参考，验证快速版本与慢速版本在小样本上完全一致。

## 3. 数据规模

| 项目 | 数值 |
|---|---:|
| subset0 CT series | 89 |
| candidates_V2 rows | 79135 |
| candidates_V2 candidate positives | 138 |
| official annotations in subset0 | 112 |
| resumed predictions | 9091 |
| newly scored predictions | 70044 |
| total predictions | 79135 |
| failures | 0 |
| CPU elapsed_sec for newly scored | 3354.927 |

输出：

- `docs/world_frontier/luna16/subset0_seriesuids.txt`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/fpred_candidates_v2_predictions.csv`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/fpred_candidates_v2_summary.json`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/fpred_candidates_v2_validation.json`

LUNA-style CSV 校验：valid = true，errors = []，warnings = []。

## 4. subset0 FROC/CPM

| 指标 | 数值 |
|---|---:|
| scan_count | 89 |
| annotation_count | 112 |
| prediction_count | 79135 |
| sensitivity_at_0.125_fp_per_scan | 0.214286 |
| sensitivity_at_0.25_fp_per_scan | 0.258929 |
| sensitivity_at_0.5_fp_per_scan | 0.410714 |
| sensitivity_at_1.0_fp_per_scan | 0.625000 |
| sensitivity_at_2.0_fp_per_scan | 0.839286 |
| sensitivity_at_4.0_fp_per_scan | 0.928571 |
| sensitivity_at_8.0_fp_per_scan | 0.937500 |
| subset0 candidates_V2 CPM | 0.602041 |

图表：

- `docs/world_frontier/luna16/subset0_full_candidates_stream/froc/fpred_subset0_candidates_v2_froc.png`
- `docs/world_frontier/luna16/subset0_full_candidates_stream/froc/fpred_10series_vs_subset0_froc.png`

## 5. 科研解释

与 10 个 series 的局部 candidates_V2 桥接相比，subset0 全量 CPM 明显降低：

| 评估范围 | series | annotations | predictions | CPM |
|---|---:|---:|---:|---:|
| 10-series candidates_V2 bridge | 10 | 7 | 9091 | 0.795918 |
| subset0 full candidates_V2 bridge | 89 | 112 | 79135 | 0.602041 |

这说明局部小样本会高估模型表现。扩大到 subset0 全量后，低 FP/scan 区间的敏感度不足成为主要短板：0.125 FP/scan 仅 0.2143，0.25 FP/scan 仅 0.2589，但在 4-8 FP/scan 区间敏感度超过 0.92。后续优化应集中在候选概率排序、校准、hard negative mining 与 NMS，而不是继续只报告候选分类 AUC。

## 6. 可写入论文的审慎表述

可以写：

> 在 LUNA16 subset0 全部 89 个 CT series 上，FPRED 分支对 79135 个 candidates_V2 候选进行流式评分，得到 subset0 candidates_V2 bridge CPM 0.6020。模型在 4-8 FP/scan 区间保持较高敏感度，但低 FP/scan 区间表现不足，提示后续需要针对假阳性排序和概率校准进行优化。

不能写：

> 本系统已经达到完整 LUNA16 官方世界前沿水平。

原因：当前只覆盖 subset0，而不是完整 888 CT；并且评估使用 candidates_V2 候选池，不等价于本项目 VNet 候选生成器端到端官方提交。

## 7. 下一步

1. 在 subset0 上加入候选 NMS/去重，降低重复候选对 FP/scan 的压力。
2. 基于 validation split 做温度缩放或阈值校准，提高低 FP/scan 排序质量。
3. 做 hard negative mining：从高置信 FP 中抽样再训练 FPRED。
4. 在磁盘允许时扩展到 subset1/subset2，逐步接近完整 888 CT 评价。
5. 构建最终论文结果表：本地病例闭环、FPRED 候选分类、10-series bridge、subset0 bridge、后续消融。
