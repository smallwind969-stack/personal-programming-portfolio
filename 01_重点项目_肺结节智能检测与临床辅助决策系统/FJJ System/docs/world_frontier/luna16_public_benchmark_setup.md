# LUNA16 公开基准接入记录

生成日期：2026-06-14

## 1. 目的

本轮工作把项目从“本地 review-proxy 评价”推进到“可接入 LUNA16 公开基准”的状态。当前已经真实联网下载并校验 LUNA16 小型元数据文件，尚未默认下载几十 GB 的 CT subset 压缩包。

## 2. 数据来源

Zenodo 记录：

```text
https://zenodo.org/api/records/3723295
```

对应页面为 LUNA16 Part 1/2，包含：

- `annotations.csv`
- `sampleSubmission.csv`
- `candidates.csv`
- `candidates_V2.zip`
- `evaluationScript.zip`
- `subset0.zip` 到 `subset6.zip`
- `seg-lungs-LUNA16.zip`

## 3. 已下载并校验的文件

命令：

```powershell
python experiments\luna16_data_manager.py
```

输出：

```text
docs\world_frontier\luna16\luna16_data_init_report.json
docs\world_frontier\luna16\zenodo_luna16_manifest.csv
```

校验结果：

| 文件 | 大小 | MD5 | 结构校验 |
|---|---:|---|---|
| `data/luna16/annotations.csv` | 136,986 bytes | 通过 | 1186 条标注，601 个含标注序列 |
| `data/luna16/sampleSubmission.csv` | 740 bytes | 通过 | 8 行，列名符合 LUNA16 submission |

说明：LUNA16 完整数据为 888 CT scans，但 `annotations.csv` 只覆盖含结节标注的序列。正式 FROC 评价必须使用完整 seriesuids，而不是仅用 annotations 推断 scan 数。

## 4. Submission 格式校验

新增脚本：

```powershell
python experiments\validate_luna_submission.py --submission data\luna16\sampleSubmission.csv
```

官方 sample 结果：

```text
valid=true
row_count=8
series_count=4
```

本地模型导出的 LUNA-style CSV 结果：

```powershell
python experiments\validate_luna_submission.py `
  --submission docs\world_frontier\local_luna_predictions.csv `
  --known-series data\luna16\annotations.csv
```

结果：

```text
valid=true
warnings=["unknown seriesuid count: 2"]
```

该警告符合预期，因为本地病例名不是 LUNA16 seriesuid。它证明格式正确，但也证明本地结果不能伪装成 LUNA16 官方评价。

## 5. 当前新增脚本

| 脚本 | 作用 |
|---|---|
| `experiments/luna16_data_manager.py` | 拉取 Zenodo manifest，下载并校验小型元数据 |
| `experiments/validate_luna_submission.py` | 校验 LUNA16-style submission 列名、坐标、概率和 seriesuid |
| `experiments/froc_eval.py` | 计算 LUNA-style FROC/CPM |
| `experiments/export_luna_predictions.py` | 将本地预测导出为 LUNA-style predictions |

## 6. 下一步

1. 已完成：下载 `evaluationScript.zip` 和 `candidates_V2.zip`，对齐官方 evaluation script 与 FP reduction track。
2. 已完成：获取完整 `seriesuids.csv`，当前 official seriesuids = 888。
3. 下一步：下载至少一个 subset，例如 `subset0.zip`，跑通真实 LUNA16 CT 读取。
4. 下一步：将当前模型权重适配 `.mhd/.raw` 输入，导出 LUNA16 submission。
5. 下一步：用 `experiments/froc_eval.py` 和官方 evaluation script 双重评价，比较差异。
6. 下一步：接入 MONAI lung nodule detection 作为 baseline 或工程参考。

## 7. 重要边界

当前已经接入 LUNA16 元数据，但尚未跑完整 LUNA16 官方评测。任何报告中只能写：

```text
已完成 LUNA16 元数据接入与 submission 格式校验。
```

不能写：

```text
本系统已达到 LUNA16 官方 CPM xx。
```
