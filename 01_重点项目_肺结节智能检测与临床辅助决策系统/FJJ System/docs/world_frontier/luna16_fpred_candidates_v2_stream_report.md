# LUNA16 subset0/test 完整 candidates_V2 流式 FPRED-FROC 报告

生成日期：2026-06-14

## 1. 目的

上一轮 FROC 桥接只使用已经抽取的 103 个采样候选，因此结果偏乐观。本轮对同一批 10 个 subset0/test series 的完整 `candidates_V2.csv` 候选池进行流式 FPRED 推理，共 9091 个候选，不落盘中间 patch，直接输出 LUNA-style prediction CSV，并重新计算 FROC/CPM。

该实验更接近真实 FPRED 使用方式：给候选生成器产生的大量候选位置赋予结节概率，再在 FROC 口径下观察低 FP/scan 区间的敏感度。

## 2. 新增工程能力

新增脚本：

- `experiments/score_luna16_candidates_stream.py`
- `experiments/plot_froc_comparison.py`

关键优化：

- 每个 CT series 只做一次 HU clipping/normalization，避免逐候选重复归一化整幅 CT。
- patch 在内存中即时裁剪并批量送入 ResNet-CBAM，不保存 9000+ 个 `.npy` patch。
- 支持 checkpoint CSV，每完成一个 series 写盘一次，避免长任务中断后结果清零。

## 3. 数据规模

| 项目 | 数值 |
|---|---:|
| series_count | 10 |
| candidates_V2 rows | 9091 |
| candidates_V2 positives | 7 |
| output predictions | 9091 |
| failures | 0 |
| patch_size | 32 |
| batch_size | 64 |
| CPU elapsed_sec | 486.283 |

输出文件：

- `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/fpred_candidates_v2_predictions.csv`
- `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/fpred_candidates_v2_summary.json`
- `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/fpred_candidates_v2_failures.json`

LUNA-style CSV 校验结果：valid = true，errors = []，warnings = []。

## 4. FROC/CPM 结果

| 指标 | 数值 |
|---|---:|
| scan_count | 10 |
| annotation_count | 7 |
| prediction_count | 9091 |
| sensitivity_at_0.125_fp_per_scan | 0.571429 |
| sensitivity_at_0.25_fp_per_scan | 0.714286 |
| sensitivity_at_0.5_fp_per_scan | 0.857143 |
| sensitivity_at_1.0_fp_per_scan | 0.857143 |
| sensitivity_at_2.0_fp_per_scan | 0.857143 |
| sensitivity_at_4.0_fp_per_scan | 0.857143 |
| sensitivity_at_8.0_fp_per_scan | 0.857143 |
| candidates_V2 bridge CPM | 0.795918 |

图表：

- `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/froc/fpred_candidates_v2_froc.png`
- `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/froc/fpred_sampled_vs_full_froc.png`

## 5. 与采样候选桥接的差异

| 评估 | predictions | CPM |
|---|---:|---:|
| sampled candidates bridge | 103 | 0.959184 |
| full candidates_V2 bridge | 9091 | 0.795918 |

解释：103 个采样候选主要用于候选分类验证，候选池规模小，假阳性压力低，因此 FROC 桥接结果偏乐观。完整 candidates_V2 候选池包含大量非结节候选，低 FP/scan 区间的敏感度下降，更接近实际检测场景。

## 6. 可写入论文的审慎表述

可以写：

> 在同一批 subset0/test series 上，将 FPRED 从 103 个采样候选扩展到 9091 个完整 candidates_V2 候选后，bridge CPM 从 0.9592 降至 0.7959；该结果说明采样候选评估会高估端到端检测表现，完整候选池评估更能反映假阳性削减分支在实际检测链路中的压力。

不能写：

> 系统已经获得完整 LUNA16 官方 CPM 0.7959。

原因：当前仍只覆盖 10 个 series，而非完整 888 CT；同时评估对象是 candidates_V2 FPRED 桥接，不包含本项目 VNet 候选生成器的完整检测链路。

## 7. 下一步

1. 把流式评分脚本扩展到 subset0 全部 89 个 CT series。
2. 在磁盘允许时继续下载 subset1/subset2，扩大公开测试规模。
3. 增加候选去重/NMS，与 LUNA16 官方匹配策略进一步贴近。
4. 对阈值校准、温度缩放、hard negative mining 进行系统实验。
5. 最终形成 VNet candidate generation + FPRED rescoring + FROC/CPM 的端到端链路。
