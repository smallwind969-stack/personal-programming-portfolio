# 本地 review-proxy FROC 跑通记录

生成日期：2026-06-14

## 目的

本记录用于证明项目已经从普通 precision/recall 表升级到 LUNA16-style FROC/CPM 工具链。该结果仍然是本地代理评估，不是 LUNA16 官方成绩，也不是临床验证。

## 输入文件

- `docs/world_frontier/local_luna_predictions.csv`
- `docs/world_frontier/local_review_proxy_annotations.csv`

## 命令

```powershell
python experiments\export_luna_predictions.py --out docs\world_frontier\local_luna_predictions.csv
python experiments\export_review_proxy_annotations.py --out docs\world_frontier\local_review_proxy_annotations.csv
python experiments\froc_eval.py `
  --annotations docs\world_frontier\local_review_proxy_annotations.csv `
  --predictions docs\world_frontier\local_luna_predictions.csv `
  --out-dir docs\world_frontier\local_proxy_froc
python experiments\plot_froc_summary.py `
  --summary docs\world_frontier\local_proxy_froc\froc_summary.csv `
  --out docs\world_frontier\local_proxy_froc\froc_summary_plot.png
```

## 结果

| 指标 | 数值 |
|---|---:|
| scan_count | 2 |
| annotation_count | 11 |
| prediction_count | 7 |
| sensitivity@0.125 FP/scan | 0.636364 |
| sensitivity@0.25 FP/scan | 0.636364 |
| sensitivity@0.5 FP/scan | 0.636364 |
| sensitivity@1 FP/scan | 0.636364 |
| sensitivity@2 FP/scan | 0.636364 |
| sensitivity@4 FP/scan | 0.636364 |
| sensitivity@8 FP/scan | 0.636364 |
| proxy CPM | 0.636364 |

## 解释

当前 FROC 曲线为水平线，说明在本地代理标注中，现有模型候选可以命中的结节集合基本固定，调节概率阈值没有带来额外召回。下一步提升重点不是包装指标，而是：

1. 补全所有病例医生复核。
2. 接入 LUNA16/LIDC-IDRI 公开数据。
3. 对模型输出进行公开格式转换。
4. 建立 MONAI 或公开强 baseline 对照。
5. 运行 VNet 阈值、ResNet 阈值、CBAM 和 patch/stride 消融。

## 数据质量注意

导出时 SimpleITK 对部分 DICOM 序列提示 non-uniform sampling。正式论文必须报告该风险，并在公开数据实验中优先使用标准化的 LUNA16 `.mhd/.raw` 体数据或经过一致重采样的数据。
