# 肺结节检测 Agent 科研实验索引

更新日期：2026-06-14

## 当前定位

项目已从本地 Flask 演示系统推进到“本地病例闭环 + LUNA16 公开数据子集 + FPRED 微调 + 独立候选测试 + bootstrap 置信区间 + 论文级图表”的阶段。该索引用于追踪可复现实验产物，防止结果散落。

## 核心产物

| 主题 | 文件 |
|---|---|
| 本地病例科研闭环报告 | `docs/final/肺结节智能检测系统_科研闭环阶段性报告.pdf` |
| LUNA16 数据接入说明 | `docs/world_frontier/luna16_public_benchmark_setup.md` |
| LUNA16 medium 资源统计 | `docs/world_frontier/luna16_medium_resources_report.md` |
| subset0 patch smoke test | `docs/world_frontier/luna16_subset0_patch_smoke_report.md` |
| FPRED subset0 原始评估 | `docs/world_frontier/luna16_fpred_subset0_eval_report.md` |
| FPRED subset0 微调 | `docs/world_frontier/luna16_fpred_finetune_subset0_report.md` |
| FPRED 独立测试 | `docs/world_frontier/luna16_fpred_independent_test_report.md` |
| FPRED bootstrap CI 报告 | `docs/world_frontier/luna16_fpred_bootstrap_ci_report.md` |
| FPRED bootstrap CI PDF | `docs/final/肺结节检测Agent_FPRED置信区间与论文图升级报告.pdf` |
| FPRED-FROC 桥接评估 | `docs/world_frontier/luna16_fpred_froc_bridge_report.md` |
| 完整 candidates_V2 流式 FPRED-FROC | `docs/world_frontier/luna16_fpred_candidates_v2_stream_report.md` |
| subset0 完整 candidates_V2 FPRED-FROC | `docs/world_frontier/luna16_subset0_full_candidates_v2_report.md` |
| subset0 NMS-FROC 扫描 | `docs/world_frontier/luna16_subset0_nms_sweep_report.md` |
| subset0 NMS 分区验证 | `docs/world_frontier/luna16_subset0_split_valid_nms_report.md` |
| evaluation FROC/CPM 置信区间 | `docs/world_frontier/luna16_evaluation_froc_bootstrap_ci_report.md` |

## 关键实验结果

| 实验 | 数据 | 结果 |
|---|---|---|
| 本地 review-proxy FROC | 本地 3 例、11 个 proxy reference nodules | CPM proxy = 0.6364 |
| ResNet-CBAM 原始 FPRED | subset0/val 115 candidates | AUC = 0.9759 |
| ResNet-CBAM 微调 FPRED | subset0/val 115 candidates | AUC = 0.9945；threshold 0.30 下 sensitivity = 0.9474，specificity = 0.9896 |
| FPRED 独立测试 | subset0/test 103 candidates | AUC = 0.9926；threshold 0.30 下 TP=6, FP=2, TN=94, FN=1 |
| FPRED bootstrap CI | subset0/test 103 candidates，seriesuid 级重采样 | AUC 0.9926 [0.9731, 1.0000]；sensitivity 0.8571 [0.5000, 1.0000]；specificity 0.9792 [0.9362, 1.0000] |
| FPRED-FROC 桥接 | subset0/test 10 series、7 annotations、103 predictions | bridge CPM = 0.9592；0.125 FP/scan sensitivity = 0.8571；0.5-8 FP/scan sensitivity = 1.0000 |
| 完整 candidates_V2 FPRED-FROC | subset0/test 10 series、7 annotations、9091 predictions | candidates_V2 bridge CPM = 0.7959；0.125 FP/scan sensitivity = 0.5714；0.25 FP/scan sensitivity = 0.7143；0.5-8 FP/scan sensitivity = 0.8571 |
| subset0 全量 candidates_V2 FPRED-FROC | subset0 89 series、112 annotations、79135 predictions | subset0 bridge CPM = 0.6020；0.125 FP/scan sensitivity = 0.2143；0.25 FP/scan sensitivity = 0.2589；4-8 FP/scan sensitivity > 0.92 |
| subset0 NMS-FROC 后处理 | subset0 89 series、112 annotations、radius sweep 0-30mm | 10mm NMS 最佳；CPM = 0.6390；0.25 FP/scan sensitivity = 0.3750；相对无 NMS CPM +6.14% |
| subset0 NMS 分区验证 | calibration 55 series/56 annotations；evaluation 34 series/56 annotations | calibration 选 10mm；evaluation fixed 10mm CPM = 0.6888 vs no NMS 0.6199；0.25 FP/scan sensitivity = 0.4821 vs 0.3214 |
| evaluation fixed 10mm bootstrap CI | evaluation 34 series、56 annotations、23436 predictions、1000 bootstrap | CPM = 0.6888 [0.6026, 0.7804]；0.25 FP/scan sensitivity = 0.4821 [0.2833, 0.6545] |

## 新增脚本

| 脚本 | 用途 |
|---|---|
| `experiments/bootstrap_fpred_metrics.py` | 对 FPRED 预测 CSV 做固定阈值 bootstrap 置信区间 |
| `experiments/plot_fpred_publication_figure.py` | 生成论文级多面板图，导出 PNG/PDF/SVG |
| `experiments/build_fpred_bootstrap_pdf.py` | 生成中文 PDF 阶段报告 |
| `experiments/export_fpred_luna_predictions.py` | 将 FPRED patch 预测回贴 LUNA16 世界坐标并导出 LUNA-style prediction CSV |
| `experiments/score_luna16_candidates_stream.py` | 对 candidates_V2 候选池流式裁剪 patch 并批量运行 FPRED |
| `experiments/plot_froc_comparison.py` | 对比采样候选桥接与完整 candidates_V2 桥接 FROC |
| `experiments/froc_eval.py` | LUNA16-style FROC/CPM；已优化为按置信度降序增量 sweep，支持大规模 prediction CSV |
| `experiments/luna_prediction_nms.py` | 对 LUNA-style prediction CSV 做 series 内 3D NMS |
| `experiments/nms_froc_sweep.py` | 对 NMS 半径做 FROC/CPM 扫描 |
| `experiments/plot_nms_froc_sweep.py` | 绘制 NMS 半径、CPM、低 FP/scan sensitivity 与候选抑制关系 |
| `experiments/make_series_calibration_split.py` | 按 annotation 数平衡划分 calibration/evaluation series |
| `experiments/plot_split_nms_validation.py` | 绘制 calibration 选择半径与 evaluation 固定半径表现 |
| `experiments/bootstrap_froc.py` | 对 FROC/CPM 做 CT series 级 bootstrap 置信区间 |
| `experiments/plot_froc_bootstrap_ci.py` | 绘制 FROC/CPM 点估计与 95% CI |

## 新增图表

| 图表 | 文件 |
|---|---|
| FPRED validation-test 对照旧图 | `docs/world_frontier/luna16/patch_test_103/metrics/fpred_val_test_comparison.png` |
| FPRED publication validation 图 | `docs/world_frontier/luna16/patch_test_103/metrics/fpred_publication_validation.png` |
| FPRED publication validation PDF | `docs/world_frontier/luna16/patch_test_103/metrics/fpred_publication_validation.pdf` |
| FPRED publication validation SVG | `docs/world_frontier/luna16/patch_test_103/metrics/fpred_publication_validation.svg` |
| FPRED-FROC bridge 图 | `docs/world_frontier/luna16/patch_test_103/froc_bridge/fpred_froc_bridge.png` |
| 完整 candidates_V2 FROC 图 | `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/froc/fpred_candidates_v2_froc.png` |
| 采样 vs 完整候选 FROC 对比图 | `docs/world_frontier/luna16/patch_test_103/full_candidates_stream/froc/fpred_sampled_vs_full_froc.png` |
| subset0 candidates_V2 FROC 图 | `docs/world_frontier/luna16/subset0_full_candidates_stream/froc/fpred_subset0_candidates_v2_froc.png` |
| 10-series vs subset0 FROC 对比图 | `docs/world_frontier/luna16/subset0_full_candidates_stream/froc/fpred_10series_vs_subset0_froc.png` |
| subset0 NMS-FROC sweep 图 | `docs/world_frontier/luna16/subset0_full_candidates_stream/nms_sweep/nms_froc_sweep.png` |
| subset0 split-valid NMS 图 | `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/split_valid_nms.png` |
| evaluation FROC bootstrap CI 图 | `docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/evaluation_nms_sweep/radius_10/bootstrap/froc_bootstrap_ci.png` |

## 科研边界

当前结果可以支撑大创结题中的“公开数据验证、模型微调、独立测试、统计置信区间与 subset0 级候选池 FROC 桥接”部分，但还不能宣称完整 LUNA16 官方世界前沿。下一轮应继续扩展更多 subset，并把 FPRED 分支回接端到端 detection FROC/CPM。

## 2026-06-15 subset1 外部验证新增结果

新增报告：`docs/world_frontier/luna16_subset1_external_validation_report.md`

| 实验 | 数据 | 结果 |
|---|---|---|
| subset1 candidates_V2 FPRED scoring | subset1 89 series、128 annotations、71,012 predictions | failures = 0 |
| subset1 raw FROC | subset1 89 series、128 annotations、71,012 predictions | CPM = 0.5536；0.125 FP/scan sensitivity = 0.1797；0.25 FP/scan sensitivity = 0.3516 |
| subset1 fixed 10mm NMS FROC | subset1 89 series、128 annotations、51,599 predictions | CPM = 0.5792；0.125 FP/scan sensitivity = 0.2422；0.25 FP/scan sensitivity = 0.3672 |
| subset1 fixed 10mm NMS bootstrap CI | 1000 series-level bootstrap，seed 20260615 | CPM = 0.5792 [0.4582, 0.6838] |

新增图表：`docs/world_frontier/luna16/subset1_external_validation/fixed10_nms_bootstrap/subset1_froc_bootstrap_ci.png`

工程升级：`experiments/luna16_data_manager.py` 已新增 `--resume-download`，支持 `.part` 文件与 HTTP Range 断点续传，用于 subset1/subset2 等 6GB 级大文件。

科研边界更新：subset1 外部验证说明 fixed 10mm NMS 有跨子集迁移收益，但绝对 CPM 仍低于近年 LUNA16 前沿结果。下一步应优先做 hard-negative mining、概率校准与更多子集固定协议验证。

## 2026-06-15 hard-negative mining 新增结果

新增报告：`docs/world_frontier/luna16_hard_negative_mining_report.md`

| 实验 | 数据 | 结果 |
|---|---|---|
| subset0 calibration hard-negative mining | 55 calibration series，79,135 predictions | selected hard negatives = 512；selected series = 53；probability range = 0.5585-0.9988 |
| hard-negative patch extraction | 512 selected candidates | extracted ok = 512 |
| merged FPRED training manifest | base 256 patches + hard-negative 512 patches | total = 768；positive = 64；negative = 704 |
| hard-negative FPRED val | val 115 candidates | AUC = 0.9973 |
| hard-negative FPRED subset0 evaluation raw FROC | 34 series、56 annotations、32,431 predictions | CPM = 0.7117 |
| hard-negative FPRED subset0 evaluation fixed 10mm NMS | 34 series、56 annotations、23,406 predictions | CPM = 0.8648；0.25 FP/scan sensitivity = 0.7857 |
| hard-negative fixed 10mm bootstrap CI | 1000 series-level bootstrap，seed 20260615 | CPM = 0.8648 [0.7560, 0.9317] |

新增脚本：`experiments/mine_hard_negatives.py`、`experiments/merge_patch_manifests.py`

新增图表：`docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/evaluation_fixed10_nms_bootstrap/hardneg_evaluation_froc_bootstrap_ci.png`

科研边界更新：hard-negative mining 在 subset0 calibration/evaluation 分区下产生大幅提升，但新权重尚未完成 subset1 外部重评估，因此不能直接宣称完整 LUNA16 世界前沿。下一步应使用 hard-negative FPRED 权重重跑 subset1 全量 candidates_V2。

## 2026-06-15 hard-negative FPRED subset1 外部重评估

新增报告：`docs/world_frontier/luna16_hard_negative_subset1_external_report.md`

| 实验 | 数据 | 结果 |
|---|---|---|
| hard-negative FPRED subset1 全量评分 | subset1 89 series、71,012 candidates | predictions = 71,012；failures = 0 |
| hard-negative FPRED subset1 raw FROC | subset1 89 series、128 annotations、71,012 predictions | CPM = 0.5770；baseline raw CPM = 0.5536 |
| hard-negative FPRED subset1 fixed 10mm NMS | subset1 89 series、128 annotations、51,573 predictions | CPM = 0.6161；baseline fixed 10mm CPM = 0.5792 |
| hard-negative subset1 fixed 10mm bootstrap CI | 1000 series-level bootstrap，seed 20260615 | CPM = 0.6161 [0.5217, 0.7099] |

新增图表：`docs/world_frontier/luna16/fpred_hardneg_subset0_calibration/subset1_fixed10_nms_bootstrap/hardneg_subset1_froc_bootstrap_ci.png`

工程修复：`experiments/score_luna16_candidates_stream.py` 移除跨 series 图像缓存，避免长任务内存累积；新增 `--progress-summary` 轻量 JSON 进度输出。

科研边界更新：hard-negative FPRED 在未参与训练、挖掘或 NMS 半径选择的 subset1 上仍有提升，说明排序改进具有一定跨子集迁移性。但 subset1 CPM = 0.6161 仍低于近年完整 LUNA16 前沿，因此下一步应下载 subset2 做第三方外部验证，并继续优化低 FP/scan 区间。

## 2026-06-15 hard-negative FPRED subset2 第三方外部验证

新增报告：`docs/world_frontier/luna16_hard_negative_subset2_third_party_report.md`

| 实验 | 数据 | 结果 |
|---|---|---|
| subset2 下载与校验 | `D:/FJJ_luna16/subset2.zip`，7,257,937,108 bytes | MD5 passed：685b484b085bcdb81c525f3b1bf97c51 |
| subset2 readiness | subset2 89 series | annotations = 128；candidates_V2 = 74,458；class=1 candidates = 181 |
| hard-negative FPRED subset2 全量评分 | subset2 89 series、74,458 candidates | predictions = 74,458；failures = 0 |
| hard-negative FPRED subset2 raw FROC | subset2 89 series、128 annotations、74,458 predictions | CPM = 0.6384 |
| hard-negative FPRED subset2 fixed 10mm NMS | subset2 89 series、128 annotations、54,614 predictions | CPM = 0.6652；0.125 FP/scan sensitivity = 0.3516；0.25 FP/scan sensitivity = 0.4531 |
| hard-negative subset2 fixed 10mm bootstrap CI | 1000 series-level bootstrap，seed 20260615 | CPM = 0.6652 [0.5892, 0.7494] |

新增图表：`docs/world_frontier/luna16/subset2_external_validation/hardneg_fixed10_nms_bootstrap/hardneg_subset2_froc_bootstrap_ci.png`

工程边界更新：subset2 下载过程中发现 Zenodo 会提前断开连接并留下短文件，`experiments/luna16_data_manager.py` 已增加 manifest size 校验，短下载只保留 `.part` 并抛错，不再生成坏 zip。

科研边界更新：subset2 是第三方外部子集，hard-negative FPRED fixed 10mm CPM = 0.6652，说明跨子集表现没有崩溃。但 baseline FPRED 尚未在 subset2 重跑，因此当前不能声明 subset2 上的相对提升幅度。

## 2026-06-15 subset2 baseline vs hard-negative 对比

新增报告：`docs/world_frontier/luna16_subset2_baseline_vs_hard_negative_report.md`

| 实验 | 数据 | 结果 |
|---|---|---|
| baseline FPRED subset2 全量评分 | subset2 89 series、74,458 candidates | predictions = 74,458；failures = 0 |
| baseline FPRED subset2 raw FROC | subset2 89 series、128 annotations、74,458 predictions | CPM = 0.5357 |
| baseline FPRED subset2 fixed 10mm NMS | subset2 89 series、128 annotations、54,726 predictions | CPM = 0.5446；0.25 FP/scan sensitivity = 0.2813 |
| hard-negative FPRED subset2 fixed 10mm NMS | subset2 89 series、128 annotations、54,614 predictions | CPM = 0.6652；0.25 FP/scan sensitivity = 0.4531 |
| subset2 fixed 10mm 对比 | 同一 subset2、同一 fixed 10mm NMS | CPM absolute gain = +0.1205；0.25 FP/scan sensitivity absolute gain = +0.1719 |

新增图表：`docs/world_frontier/luna16/subset2_external_validation/baseline_fixed10_nms_bootstrap/baseline_subset2_froc_bootstrap_ci.png`

科研边界更新：subset2 完成 baseline 对照后，可以审慎表述 hard-negative FPRED 在第三方外部子集上相对 baseline 有明确提升。但该结果仍是 subset2 bridge evaluation，不是完整 LUNA16 官方提交。

## 2026-06-15 subset1+subset2 pooled 外部验证

新增报告：`docs/world_frontier/luna16_pooled_subset1_subset2_external_validation_report.md`

| 实验 | 数据 | 结果 |
|---|---|---|
| pooled external merge | subset1 + subset2 | 178 series，256 annotations |
| baseline FPRED pooled fixed 10 mm NMS | 106,325 predictions | CPM = 0.5580，95% CI = 0.4568-0.6461 |
| hard-negative FPRED pooled fixed 10 mm NMS | 106,187 predictions | CPM = 0.6339，95% CI = 0.5802-0.7010 |
| pooled relative gain | 同一 subset1+subset2、同一 fixed 10 mm NMS | CPM absolute gain = +0.0759，0.25 FP/scan sensitivity absolute gain = +0.1445 |
| paired bootstrap gain | 1000 paired series-level bootstrap，seed 20260615 | CPM gain = +0.0759，95% CI = +0.0101 to +0.1579，gain>0 比例 = 0.9880 |

新增图表：`docs/world_frontier/luna16/pooled_subset1_subset2_external/pooled_external_validation_froc_ci.png`

科研边界更新：pooled 外部验证说明 hard-negative FPRED 的收益不是单一 subset 偶然现象，且主要集中在低 FP/scan 区间。但当前仍属于 candidates_V2 false-positive reduction bridge evaluation；下一步应加入 subset3/subset4，并继续向完整 LUNA16 官方协议靠拢。
