# LUNA16 subset0 calibration hard-negative mining 报告

生成日期：2026-06-15

## 1. 目的

subset1 外部验证显示 fixed 10 mm NMS 有跨子集迁移收益，但绝对 CPM 仍不足。低 FP/scan 区间仍是主要短板。本阶段引入 hard-negative mining：从 subset0 calibration series 中挖掘高置信度假阳性，用于 FPRED 再训练，并在未参与挖掘的 subset0 evaluation split 上验证。

核心原则：

- hard negatives 只来自 subset0 calibration series。
- subset0 evaluation series 不进入 hard-negative mining。
- subset1 不进入 hard-negative mining。
- fixed 10 mm NMS 仍沿用 subset0 calibration 预先确定的半径，不在 evaluation 上重新调参。

## 2. Hard-negative 挖掘

新增脚本：

- `experiments/mine_hard_negatives.py`
- `experiments/merge_patch_manifests.py`

新增测试：

- `tests/test_hard_negative_mining.py`
- `tests/test_merge_patch_manifests.py`

挖掘定义：

1. 读取 subset0 全量 candidates_V2 FPRED predictions。
2. 仅保留 calibration split 中的 55 个 series。
3. 排除命中官方 annotation 的 true positive 候选；命中规则为距离 annotation 中心不超过 `diameter_mm / 2`。
4. 选择概率不低于 0.5 的高分假阳性。
5. 限制每个 series 最多 16 个，最终取 512 个。

结果：

| 项目 | 数值 |
|---|---:|
| allowed calibration series | 55 |
| input predictions | 79,135 |
| calibration annotations | 56 |
| selected hard negatives | 512 |
| selected series | 53 |
| max selected probability | 0.998774 |
| min selected probability | 0.558479 |

输出：

- `docs/world_frontier/luna16/hard_negative_mining/subset0_calibration_hard_negatives.csv`
- `docs/world_frontier/luna16/hard_negative_mining/hard_negative_summary.json`

## 3. Patch 提取与训练集

从 hard-negative candidate CSV 中提取 32³ patch：

| 项目 | 数值 |
|---|---:|
| requested hard-negative patches | 512 |
| extracted ok | 512 |

输出：

- `docs/world_frontier/luna16/hard_negative_mining/patch_hard_neg_512/patch_manifest.json`

合并训练集：

| 来源 | 数量 |
|---|---:|
| base train manifest | 256 |
| hard-negative patches | 512 |
| merged train total | 768 |
| positive | 64 |
| negative | 704 |

输出：

- `docs/world_frontier/luna16/hard_negative_mining/train_manifest_base256_hn512.json`
- `docs/world_frontier/luna16/hard_negative_mining/train_manifest_base256_hn512_summary.json`

## 4. FPRED hard-negative 微调

输入权重：

- `docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth`

输出目录：

- `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration`

训练设置：

| 项目 | 数值 |
|---|---:|
| train patches | 768 |
| val patches | 115 |
| epochs | 2 |
| batch size | 8 |
| learning rate | 0.00005 |
| device | CPU |

候选分类验证：

| 模型 | val AUC | 说明 |
|---|---:|---|
| baseline FPRED 微调 | 0.9945 | `docs/world_frontier/luna16/fpred_finetune_subset0/training_summary.json` |
| hard-negative FPRED | 0.9973 | `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/training_summary.json` |

注意：hard-negative 模型在默认 0.5 阈值下更保守，敏感性下降。因此不能只用固定分类阈值判断效果，必须回到 CT 候选池 FROC。

## 5. subset0 evaluation FROC 验证

使用 hard-negative FPRED 权重对 subset0 evaluation split 全量 candidates_V2 重新评分：

| 项目 | 数值 |
|---|---:|
| evaluation series | 34 |
| annotations | 56 |
| candidates / predictions | 32,431 |
| scoring failures | 0 |

### 5.1 Raw FROC

| 指标 | baseline raw | hard-negative raw |
|---|---:|---:|
| CPM | 0.6199 | 0.7117 |
| Sens @0.125 FP/scan | 0.2679 | 0.1964 |
| Sens @0.25 FP/scan | 0.3214 | 0.3393 |
| Sens @0.5 FP/scan | 0.4821 | 0.7679 |
| Sens @1 FP/scan | 0.6071 | 0.8393 |
| Sens @2 FP/scan | 0.8036 | 0.9107 |
| Sens @4 FP/scan | 0.8929 | 0.9643 |
| Sens @8 FP/scan | 0.9643 | 0.9643 |

### 5.2 Fixed 10 mm NMS FROC

| 指标 | baseline fixed 10 mm NMS | hard-negative fixed 10 mm NMS |
|---|---:|---:|
| predictions after NMS | 23,436 | 23,406 |
| CPM | 0.6888 | 0.8648 |
| Sens @0.125 FP/scan | 0.3214 | 0.6964 |
| Sens @0.25 FP/scan | 0.4821 | 0.7857 |
| Sens @0.5 FP/scan | 0.5714 | 0.8393 |
| Sens @1 FP/scan | 0.7143 | 0.8929 |
| Sens @2 FP/scan | 0.8571 | 0.9464 |
| Sens @4 FP/scan | 0.9286 | 0.9464 |
| Sens @8 FP/scan | 0.9464 | 0.9464 |

## 6. Bootstrap 置信区间

对 hard-negative FPRED + fixed 10 mm NMS 的 subset0 evaluation 结果进行 series-level bootstrap：

| 项目 | 数值 |
|---|---:|
| bootstrap repeats | 1000 |
| accepted repeats | 1000 |
| seed | 20260615 |
| series | 34 |
| annotations | 56 |
| predictions after NMS | 23,406 |

| 指标 | 点估计 | 95% CI |
|---|---:|---:|
| CPM | 0.8648 | 0.7560-0.9317 |
| Sens @0.125 FP/scan | 0.6964 | 0.0625-0.8548 |
| Sens @0.25 FP/scan | 0.7857 | 0.6182-0.8929 |
| Sens @0.5 FP/scan | 0.8393 | 0.7308-0.9259 |
| Sens @1 FP/scan | 0.8929 | 0.7857-0.9623 |
| Sens @2 FP/scan | 0.9464 | 0.8545-1.0000 |
| Sens @4 FP/scan | 0.9464 | 0.8750-1.0000 |
| Sens @8 FP/scan | 0.9464 | 0.8750-1.0000 |

图表：

- `docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/evaluation_fixed10_nms_bootstrap/hardneg_evaluation_froc_bootstrap_ci.png`

## 7. 科研解释

hard-negative mining 在 subset0 evaluation split 上显著改善 fixed 10 mm NMS FROC：CPM 从 0.6888 提升到 0.8648，0.25 FP/scan sensitivity 从 0.4821 提升到 0.7857。这说明 FPRED 的主要瓶颈确实来自高分假阳性排序，而不仅是 NMS 后处理。

该结果已经接近近年 LUNA16 论文中较强方法的区间，但还不能直接宣称世界前沿，原因有二：

1. hard negatives 来自 subset0 calibration，同一 subset 内 evaluation 的结果仍可能存在数据域相近带来的乐观性。
2. 新 hard-negative 权重尚未在 subset1 上完成全量重评估；跨子集泛化仍需验证。

## 8. 可写入结题/论文的审慎表述

可以写：

> 基于 calibration split 的 hard-negative mining 将 subset0 evaluation fixed 10 mm NMS CPM 从 0.6888 提升至 0.8648，并将 0.25 FP/scan sensitivity 从 0.4821 提升至 0.7857。series-level bootstrap 显示 CPM 95% CI 为 0.7560-0.9317。

不能写：

> hard-negative 模型已经达到完整 LUNA16 世界前沿。

原因：该结论仍需 subset1 或更多外部子集用新权重重评估。

## 9. 下一步

1. 使用 hard-negative FPRED 权重重跑 subset1 全量 candidates_V2。
2. 在 subset1 上固定 10 mm NMS，比较 baseline FPRED 与 hard-negative FPRED。
3. 若 subset1 也明显提升，再继续下载 subset2 作为第三方验证。
4. 将 hard-negative mining、NMS、bootstrap CI 写入结题报告和论文实验部分。
