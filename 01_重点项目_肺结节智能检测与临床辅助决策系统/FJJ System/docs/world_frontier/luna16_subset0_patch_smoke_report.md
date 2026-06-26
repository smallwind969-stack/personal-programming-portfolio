# LUNA16 subset0 真实 CT 接入与 patch smoke inference 报告

生成日期：2026-06-14

## 1. 本轮目标

本轮把公开基准路线从“元数据 + candidates”推进到真实 CT 体数据层：

1. 下载并解压 LUNA16 `subset0.zip`。
2. 读取 `.mhd/.raw` 体数据并生成 CT 索引。
3. 将 candidates_V2 世界坐标转换为图像索引。
4. 抽取 32³ 3D patch。
5. 使用当前 ResNet-CBAM 假阳性过滤器做 smoke inference。

## 2. subset0 下载与解压

命令：

```powershell
python experiments\luna16_data_manager.py --download-subset 0 --extract-subset --delete-zip-after-extract --reserve-gb 2
```

结果：

- `subset0.zip` 下载完成。
- MD5 通过：`1065b0f42b8c25cf29260fd924a3c3a2`。
- 解压后删除 zip 以释放磁盘空间。
- 解压得到 89 个 `.mhd/.raw` CT 体数据。

## 3. CT 索引

命令：

```powershell
python experiments\index_luna16_ct.py
```

输出：

```text
docs\world_frontier\luna16\luna16_ct_index.csv
docs\world_frontier\luna16\luna16_ct_index.json
```

当前索引结果：

- `ct_count`: 89
- 第一例尺寸：512 x 512 x 121
- 第一例 spacing：0.7617 x 0.7617 x 2.5 mm

说明：SimpleITK 在当前中文路径下读取 `.mhd` 失败，因此项目新增 `experiments/metaimage_utils.py`，直接解析 MetaImage 头并用 `numpy.memmap` 读取 `.raw`。这避免了路径编码问题，也更适合大规模 patch 抽取。

## 4. Patch 抽取

命令：

```powershell
python experiments\extract_luna16_patches.py --split val --limit 16 --patch-size 32 --out-dir docs\world_frontier\luna16\patch_smoke
```

结果：

- 请求扫描 val split 中的候选。
- 成功从 subset0 中抽取 16 个 patch。
- 生成 `patch_manifest.json`。
- 生成中心切片预览图：`patch_montage.png`。

抽取结果检查：

- 每个 patch 形状为 `32 x 32 x 32`。
- 值域在归一化 HU 范围内。
- 16 个 patch 中包含 2 个阳性候选。

## 5. ResNet-CBAM smoke inference

命令：

```powershell
python experiments\run_fpred_resnet_smoke.py --device cpu
```

输出：

```text
docs\world_frontier\luna16\patch_smoke\fpred_resnet_smoke_predictions.csv
docs\world_frontier\luna16\patch_smoke\fpred_resnet_smoke_summary.json
```

结果：

| 指标 | 数值 |
|---|---:|
| row_count | 16 |
| threshold | 0.5 |
| TP | 2 |
| FP | 2 |
| TN | 12 |
| FN | 0 |
| accuracy | 0.875 |
| sensitivity | 1.0 |
| specificity | 0.8571 |

## 6. 解释边界

这不是正式性能结果。原因：

- 只抽取了 subset0 中的 16 个 patch。
- 样本选择是 smoke test，不是完整验证集。
- 当前 ResNet-CBAM 权重不是在完整 LUNA16 FPRED 清单上重新训练得到。

可以写入汇报的表述：

```text
项目已跑通 LUNA16 subset0 真实 CT 读取、世界坐标候选 patch 抽取和当前 ResNet-CBAM smoke inference。
```

不能写：

```text
当前模型已达到 LUNA16 官方 FPRED 性能。
```

## 7. 下一步

1. 批量抽取 train/val/test patch，先限制每类数量以控制磁盘。
2. 对 ResNet-CBAM 做 LUNA16 FPRED 微调或完整重训。
3. 使用 val split 选择阈值，再在 test split 报告敏感性、特异性、AUC。
4. 将 FPRED 模型输出回接 detection FROC/CPM。
