# LUNA16 subset0 FPRED ResNet-CBAM 微调实验报告

生成日期：2026-06-14

## 1. 实验目的

上一阶段已在 LUNA16 subset0/val 的 115 个候选 patch 上完成当前 ResNet-CBAM 权重的候选级评估。本阶段进一步完成小规模微调闭环：

1. 从 subset0 的 train split 中抽取平衡候选 patch。
2. 加载现有 `fpr_v7_best_rec_0.9612.pth` 权重。
3. 在 subset0/train 上微调 2 个 epoch。
4. 在 subset0/val 上输出 AUC、敏感性、特异性、精确率和 F1。
5. 保存 best checkpoint 与验证预测结果。

该实验仍不是完整 LUNA16 官方成绩，但已经形成了可复现的训练-验证闭环。

## 2. 数据

训练候选：

```powershell
python experiments\make_subset_patch_manifest.py `
  --split train `
  --positives 64 `
  --negatives 192 `
  --out docs\world_frontier\luna16\subset0_train_patch_candidates_256.csv
```

验证候选：

```powershell
python experiments\make_subset_patch_manifest.py `
  --split val `
  --positives 32 `
  --negatives 96 `
  --out docs\world_frontier\luna16\subset0_val_patch_candidates_128.csv
```

实际样本：

| split | patches | positive | negative |
|---|---:|---:|---:|
| train | 256 | 64 | 192 |
| val | 115 | 19 | 96 |

## 3. 训练设置

命令：

```powershell
python experiments\train_fpred_resnet.py `
  --epochs 2 `
  --batch-size 8 `
  --lr 0.0001 `
  --device cpu
```

设置：

- 模型：ResNet18_3D_CBAM
- 初始化权重：`models/fpr_v7_best_rec_0.9612.pth`
- 损失函数：weighted cross entropy
- 优化器：Adam
- batch size：8
- epoch：2
- 设备：CPU

输出：

- `docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth`
- `docs/world_frontier/luna16/fpred_finetune_subset0/best_val_predictions.csv`
- `docs/world_frontier/luna16/fpred_finetune_subset0/training_summary.json`

## 4. 结果

训练日志：

| epoch | train loss | val AUC | threshold 0.5 sensitivity | threshold 0.5 specificity | threshold 0.5 precision |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.3070 | 0.9901 | 0.9474 | 0.9167 | 0.6923 |
| 2 | 0.1148 | 0.9945 | 0.8947 | 0.9896 | 0.9444 |

微调后标准评估：

```powershell
python experiments\evaluate_fpred_predictions.py `
  --predictions docs\world_frontier\luna16\fpred_finetune_subset0\best_val_predictions.csv `
  --out-dir docs\world_frontier\luna16\fpred_finetune_subset0\metrics
```

| 指标 | 数值 |
|---|---:|
| prediction_count | 115 |
| positive_count | 19 |
| negative_count | 96 |
| AUC | 0.9945 |
| best F1 threshold | 0.30 |
| best F1 | 0.9474 |
| best F1 sensitivity | 0.9474 |
| best F1 specificity | 0.9896 |

与未微调当前权重对比：

| 实验 | AUC | threshold 0.5 FP | threshold 0.5 FN | threshold 0.5 specificity |
|---|---:|---:|---:|---:|
| 原始 ResNet-CBAM | 0.9759 | 12 | 2 | 0.8750 |
| subset0 微调后 | 0.9945 | 1 | 2 | 0.9896 |

## 5. 图表

```text
docs\world_frontier\luna16\fpred_finetune_subset0\metrics\fpred_finetuned_roc_thresholds.png
```

## 6. 解释边界

该实验可以证明项目已经具备公开数据上的 FPRED 微调闭环，但不能宣称世界前沿性能。原因：

- 只使用 subset0，而非完整 888 CT。
- 训练集和验证集规模仍小。
- 只训练 2 个 epoch，没有做完整超参搜索。
- 还没有在独立 test split 上报告锁定阈值后的最终结果。

可以写：

```text
项目已在 LUNA16 subset0 上完成 ResNet-CBAM FPRED 微调闭环，115 个验证候选的候选级 AUC 从 0.9759 提升至 0.9945。
```

不能写：

```text
项目已达到 LUNA16 官方世界前沿水平。
```

## 7. 下一步

1. 下载更多 subset 或迁移到更大硬盘。
2. 扩大 train/val/test patch 抽取规模。
3. 固定 val 阈值，在 test split 上报告最终性能。
4. 将 FPRED 输出整合回 FROC/CPM，评估完整检测链路。
