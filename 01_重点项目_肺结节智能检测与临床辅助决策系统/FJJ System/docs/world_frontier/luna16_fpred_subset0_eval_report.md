# LUNA16 subset0 FPRED 批量候选级评估报告

生成日期：2026-06-14

## 1. 目的

本报告将前一轮 16 个 patch 的 smoke test 扩展为 subset0 范围内的批量候选级 FPRED 实验。实验目标是验证：

1. 能从真实 LUNA16 subset0 CT 中批量抽取候选 patch。
2. 当前 ResNet-CBAM 假阳性过滤器可以批量前向。
3. 能输出候选级 ROC/AUC、敏感性、特异性、精确率和 F1。

该结果不是完整 LUNA16 官方成绩。

## 2. 候选清单

命令：

```powershell
python experiments\make_subset_patch_manifest.py `
  --split val `
  --positives 32 `
  --negatives 96 `
  --out docs\world_frontier\luna16\subset0_val_patch_candidates_128.csv
```

实际结果：

| 项目 | 数值 |
|---|---:|
| subset0 可用序列 | 89 |
| val split 中 subset0 候选 | 115 |
| 选中候选 | 115 |
| 阳性候选 | 19 |
| 阴性候选 | 96 |

说明：subset0 的 val split 中只有 19 个阳性候选可用，因此未强行凑满 32 个阳性。

## 3. Patch 抽取

命令：

```powershell
python experiments\extract_luna16_patches.py `
  --candidates docs\world_frontier\luna16\subset0_val_patch_candidates_128.csv `
  --split val `
  --limit 115 `
  --patch-size 32 `
  --out-dir docs\world_frontier\luna16\patch_eval_115
```

结果：

```text
requested=115
ok=115
```

输出：

- `docs/world_frontier/luna16/patch_eval_115/patch_manifest.json`
- 115 个 `32 x 32 x 32` `.npy` patch

## 4. 当前 ResNet-CBAM 批量评估

命令：

```powershell
python experiments\run_fpred_resnet_smoke.py `
  --manifest docs\world_frontier\luna16\patch_eval_115\patch_manifest.json `
  --out docs\world_frontier\luna16\patch_eval_115\fpred_resnet_predictions.csv `
  --summary docs\world_frontier\luna16\patch_eval_115\fpred_resnet_summary.json `
  --device cpu
```

阈值 0.5 结果：

| 指标 | 数值 |
|---|---:|
| row_count | 115 |
| TP | 17 |
| FP | 12 |
| TN | 84 |
| FN | 2 |
| accuracy | 0.8783 |
| sensitivity | 0.8947 |
| specificity | 0.8750 |

## 5. ROC/AUC 与阈值评估

命令：

```powershell
python experiments\evaluate_fpred_predictions.py `
  --predictions docs\world_frontier\luna16\patch_eval_115\fpred_resnet_predictions.csv `
  --out-dir docs\world_frontier\luna16\patch_eval_115\metrics
```

结果：

| 指标 | 数值 |
|---|---:|
| prediction_count | 115 |
| positive_count | 19 |
| negative_count | 96 |
| AUC | 0.9759 |
| best F1 threshold | 0.9 |
| best F1 | 0.8205 |
| best F1 sensitivity | 0.8421 |
| best F1 specificity | 0.9583 |

图：

```text
docs\world_frontier\luna16\patch_eval_115\metrics\fpred_eval_roc_thresholds.png
```

## 6. 解释边界

这个实验比 smoke test 更完整，但仍不能写成 LUNA16 官方性能。原因：

- 只使用 subset0 且只覆盖 val split 中可用的 115 个候选。
- 当前 ResNet-CBAM 权重不是在完整 LUNA16 FPRED train split 上训练得到。
- 还没有在 test split 上锁定阈值后报告最终性能。
- 没有做多折或全 888 CT 的评估。

可以写：

```text
项目已在 LUNA16 subset0 上完成候选级 FPRED 批量评估闭环，当前 115 个候选的 AUC 为 0.9759。
```

不能写：

```text
项目已达到 LUNA16 官方世界前沿水平。
```

## 7. 下一步

1. 下载更多 subset 或释放磁盘后扩展到完整 LUNA16。
2. 批量抽取 train/val/test patch。
3. 在 train 上微调 ResNet-CBAM，在 val 上选阈值，在 test 上报告 AUC/敏感性/特异性。
4. 将 FPRED 分类概率转回 CAD candidate probability，接入 detection FROC/CPM。
