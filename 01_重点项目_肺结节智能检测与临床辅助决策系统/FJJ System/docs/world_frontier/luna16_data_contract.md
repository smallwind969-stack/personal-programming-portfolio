# LUNA16 数据接入契约

本文件定义项目接入 LUNA16/LIDC-IDRI 时必须遵守的数据格式。不要把本地 `doctor_review.json` 的 review-proxy 指标与 LUNA16 CPM 直接混用。

## 1. 标注文件

路径示例：

```powershell
data\luna16\annotations.csv
```

必需列：

```text
seriesuid,coordX,coordY,coordZ,diameter_mm
```

含义：

- `seriesuid`: CT 序列 ID。
- `coordX/coordY/coordZ`: 世界坐标，单位 mm。
- `diameter_mm`: 结节直径，用于匹配半径。

## 2. 预测文件

路径示例：

```powershell
outputs\luna16\predictions.csv
```

必需列：

```text
seriesuid,coordX,coordY,coordZ,probability
```

含义：

- `probability`: 候选结节概率，越大越可信。
- 同一真实结节被多个预测命中时，只能计 1 个 TP，其余重复预测计入 FP。

## 3. 可选序列清单

路径示例：

```powershell
data\luna16\seriesuids.txt
```

每行一个 `seriesuid`。若不提供，评价脚本会从 annotations 与 predictions 中合并推断 scan 数量；正式实验应提供固定清单。

## 4. 运行 FROC/CPM

```powershell
python experiments\froc_eval.py `
  --annotations data\luna16\annotations.csv `
  --predictions outputs\luna16\predictions.csv `
  --seriesuids data\luna16\seriesuids.txt `
  --out-dir docs\world_frontier\froc_eval
```

输出：

- `froc_points.csv`: 不同概率阈值下的 TP、FP、FN、sensitivity、FP/scan。
- `froc_summary.csv`: 7 个官方 FP/scan 水平下的 sensitivity 和 CPM。

## 5. 论文写作约束

- 只有完成公开基准评价后，才允许写“与公开方法比较”。
- 本地 3 例结果只能写作系统可行性与闭环验证。
- review-proxy recall 不能写成 clinical sensitivity。
- Agent 随访建议必须写明“辅助提示，不能替代医生决策”。

## 6. 当前项目中的转换工具

本项目已经新增本地到 LUNA-style 的转换桥：

```powershell
python experiments\export_luna_predictions.py --out docs\world_frontier\local_luna_predictions.csv
python experiments\export_review_proxy_annotations.py --out docs\world_frontier\local_review_proxy_annotations.csv
```

说明：

- `export_luna_predictions.py` 默认只导出模型候选。
- `export_review_proxy_annotations.py` 将保存的模型确认项和医生新增项合并为本地代理标注。
- 未来 `/detect` 返回结果已加入 `coordX/coordY/coordZ` 字段；历史复核记录则通过 DICOM/ITK 元数据从 `(x, y, slice_idx)` 转换到物理坐标。
- 若 SimpleITK 提示 non-uniform sampling，必须在报告中列为数据质量风险。

当前本地代理 FROC 输出：

```text
docs\world_frontier\local_proxy_froc\froc_summary.csv
docs\world_frontier\local_proxy_froc\froc_summary_plot.png
```

## 7. 公开元数据初始化

项目新增 LUNA16 数据管理脚本：

```powershell
python experiments\luna16_data_manager.py
```

当前已验证：

- `data/luna16/annotations.csv`: 1186 条标注，601 个含标注序列，MD5 通过。
- `data/luna16/sampleSubmission.csv`: 8 行官方样例，MD5 通过。

Submission 校验：

```powershell
python experiments\validate_luna_submission.py --submission data\luna16\sampleSubmission.csv
```

本地导出预测 CSV 可通过格式校验，但因 seriesuid 为本地中文病例名，不属于 LUNA16 官方序列，不能用于官方成绩声明。
