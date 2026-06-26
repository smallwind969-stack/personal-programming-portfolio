# LUNA16 中型资源接入与 FPRED 清单报告

生成日期：2026-06-14

## 1. 本轮目标

在已完成 `annotations.csv` 与 `sampleSubmission.csv` 小型元数据接入的基础上，本轮继续下载并解压 LUNA16 中型资源：

- `evaluationScript.zip`
- `candidates_V2.zip`

目的：让项目具备官方评价脚本、完整 seriesuid 清单、excluded annotations 和 false-positive reduction candidate 清单。

## 2. 下载与校验

命令：

```powershell
python experiments\luna16_data_manager.py --download-medium --extract-medium
```

结果：

| 文件 | 大小 | MD5 |
|---|---:|---|
| `candidates_V2.zip` | 11,439,452 bytes | 通过 |
| `evaluationScript.zip` | 21,803,068 bytes | 通过 |

解压后关键文件：

- `data/luna16/candidates_V2/candidates_V2.csv`
- `data/luna16/evaluationScript/evaluationScript/noduleCADEvaluationLUNA16.py`
- `data/luna16/evaluationScript/evaluationScript/annotations/seriesuids.csv`
- `data/luna16/evaluationScript/evaluationScript/annotations/annotations_excluded.csv`

## 3. 官方资源摘要

命令：

```powershell
python experiments\summarize_luna16_resources.py
```

输出：

```text
docs\world_frontier\luna16\luna16_resource_summary.json
```

关键数字：

| 资源 | 数值 |
|---|---:|
| official seriesuids | 888 |
| nodule annotations | 1186 |
| annotation series count | 601 |
| excluded annotations | 35192 |
| candidates_V2 rows | 754975 |
| candidates_V2 positive | 1557 |
| candidates_V2 negative | 753418 |
| candidate series count | 888 |

说明：部分网页二手资料提到 candidates 数量约 551,065；当前工程以本地 MD5 校验通过后的 `candidates_V2.csv` 实际统计为准。

## 4. FPRED 训练清单

命令：

```powershell
python experiments\make_luna16_fpred_splits.py --max-neg-per-pos 5
```

输出：

- `docs/world_frontier/luna16/fpred_candidates_balanced.csv`
- `docs/world_frontier/luna16/fpred_candidates_balanced_summary.csv`

当前抽样结果：

| split | total | positive | negative | series_count |
|---|---:|---:|---:|---:|
| train | 6458 | 1079 | 5379 | 621 |
| val | 1433 | 250 | 1183 | 131 |
| test | 1451 | 228 | 1223 | 132 |

设计原则：

- 保留全部阳性候选。
- 阴性候选按 `max_neg_per_pos=5` 采样。
- 按 seriesuid 分割，避免同一 CT 序列同时进入训练和验证/测试。

## 5. 下一步

1. 下载至少一个 CT subset，例如 `subset0.zip`，跑通 `.mhd/.raw` 读取。
2. 为 FPRED 清单实现 patch extraction：从 `.mhd` 体数据按世界坐标裁剪 3D patch。
3. 将当前 ResNet-CBAM 假阳性过滤器适配 LUNA16 candidates。
4. 用 train/val/test 清单训练或至少评估 FP reduction baseline。
5. 与 MONAI lung nodule detection bundle 进行 baseline 对齐。
