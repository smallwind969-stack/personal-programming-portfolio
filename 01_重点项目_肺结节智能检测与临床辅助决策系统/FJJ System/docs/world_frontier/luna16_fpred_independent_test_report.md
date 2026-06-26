# LUNA16 subset0 FPRED 独立测试报告

生成日期：2026-06-14

## 1. 目的

上一阶段在 subset0/train 上微调 ResNet-CBAM，并在 subset0/val 上选择阈值。本阶段固定验证集选择的阈值 `0.30`，在 subset0/test 上进行一次独立测试。

该流程遵循医学 AI 报告中的基本原则：模型选择和阈值选择在 validation set 完成，test set 用于独立报告，不再根据 test 结果反向调参。

## 2. 数据

test 候选生成：

```powershell
python experiments\make_subset_patch_manifest.py `
  --split test `
  --positives 32 `
  --negatives 96 `
  --out docs\world_frontier\luna16\subset0_test_patch_candidates_128.csv
```

实际候选：

| split | candidates | positive | negative |
|---|---:|---:|---:|
| test | 103 | 7 | 96 |

说明：subset0/test 可用阳性候选只有 7 个，因此未强行补足 32 个阳性。

Patch 抽取：

```powershell
python experiments\extract_luna16_patches.py `
  --candidates docs\world_frontier\luna16\subset0_test_patch_candidates_128.csv `
  --split test `
  --limit 103 `
  --patch-size 32 `
  --out-dir docs\world_frontier\luna16\patch_test_103
```

结果：

```text
requested=103
ok=103
```

## 3. 模型与阈值

模型：

```text
docs\world_frontier\luna16\fpred_finetune_subset0\best_resnet_cbam_subset0.pth
```

阈值：

```text
0.30
```

阈值来源：subset0/val 上 best F1 阈值。

## 4. 独立测试结果

命令：

```powershell
python experiments\run_fpred_resnet_smoke.py `
  --manifest docs\world_frontier\luna16\patch_test_103\patch_manifest.json `
  --weights docs\world_frontier\luna16\fpred_finetune_subset0\best_resnet_cbam_subset0.pth `
  --out docs\world_frontier\luna16\patch_test_103\fpred_resnet_finetuned_test_predictions.csv `
  --summary docs\world_frontier\luna16\patch_test_103\fpred_resnet_finetuned_test_summary.json `
  --threshold 0.30 `
  --device cpu
```

固定阈值 0.30：

| 指标 | 数值 |
|---|---:|
| row_count | 103 |
| TP | 6 |
| FP | 2 |
| TN | 94 |
| FN | 1 |
| accuracy | 0.9709 |
| sensitivity | 0.8571 |
| specificity | 0.9792 |

ROC/AUC：

```powershell
python experiments\evaluate_fpred_predictions.py `
  --predictions docs\world_frontier\luna16\patch_test_103\fpred_resnet_finetuned_test_predictions.csv `
  --out-dir docs\world_frontier\luna16\patch_test_103\metrics
```

| 指标 | 数值 |
|---|---:|
| AUC | 0.9926 |
| positive_count | 7 |
| negative_count | 96 |

图：

```text
docs\world_frontier\luna16\patch_test_103\metrics\fpred_val_test_comparison.png
```

## 5. 与验证集对比

| split | n | positive | negative | AUC |
|---|---:|---:|---:|---:|
| val | 115 | 19 | 96 | 0.9945 |
| test | 103 | 7 | 96 | 0.9926 |

固定阈值 test 表现：

| threshold | sensitivity | specificity | accuracy |
|---:|---:|---:|---:|
| 0.30 | 0.8571 | 0.9792 | 0.9709 |

## 6. 解释边界

该结果比 validation-only 报告更可信，因为阈值已固定后才评估 test。仍需强调：

- 只覆盖 LUNA16 subset0，而非完整 888 CT。
- test 阳性只有 7 个，置信区间会很宽。
- 当前训练只跑 2 epoch，未做系统调参。
- 未接回完整 detection FROC/CPM。

可以写：

```text
在 LUNA16 subset0 的独立 test 候选级实验中，微调后的 ResNet-CBAM 在固定阈值 0.30 下获得 sensitivity 0.8571、specificity 0.9792，候选级 AUC 为 0.9926。
```

不能写：

```text
本系统已达到完整 LUNA16 官方世界前沿水平。
```

## 7. 下一步

1. 扩展到更多 subset，增加 test 阳性数量。
2. 重训 FPRED 模型并固定模型选择策略。
3. 使用 test 上固定阈值输出的概率回接 FROC/CPM。
4. 增加置信区间或 bootstrap。
