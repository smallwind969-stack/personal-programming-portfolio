# LUNA16 subset0 FPRED 置信区间与论文图升级报告

生成日期：2026-06-14

## 1. 研究定位

本阶段不再把肺结节检测 Agent 仅作为系统演示，而是把其 FPRED 假阳性削减分支纳入可复现的医学影像 AI 研究流程：固定训练/验证/测试划分，固定验证集阈值，再在独立测试候选集上报告 AUC、敏感度、特异度、精确率、F1 及 bootstrap 95% 置信区间。

外部规范依据：

- LUNA16 官方挑战以 FROC 敏感度与每扫描假阳性率作为检测评价核心，因此本项目后续完整检测评价仍应回接 FROC/CPM，而不能只报告候选分类 AUC：[LUNA16 Evaluation](https://luna16.grand-challenge.org/Evaluation/)。
- LUNA16 数据来自公开挑战及 Zenodo 归档，本项目当前已完成 subset0 的 CT 索引、候选 patch 抽取、FPRED 微调和独立候选测试：[LUNA16 Zenodo Part 1/2](https://zenodo.org/records/3723295)。
- 医学影像 AI 论文应遵循 CLAIM 2024 等报告规范，明确数据来源、划分、阈值选择、独立测试和局限性：[CLAIM 2024 Update](https://www.equator-network.org/reporting-guidelines/checklist-for-artificial-intelligence-in-medical-imaging-claim-a-guide-for-authors-and-reviewers/)。

## 2. 数据与模型

本轮实验使用已下载并解析的 LUNA16 subset0。

| 数据划分 | 候选数 | 阳性 | 阴性 | 用途 |
|---|---:|---:|---:|---|
| train | 256 | 64 | 192 | ResNet-CBAM FPRED 微调 |
| validation | 115 | 19 | 96 | 模型选择与阈值选择 |
| independent test | 103 | 7 | 96 | 固定阈值后的独立测试 |

模型：`docs/world_frontier/luna16/fpred_finetune_subset0/best_resnet_cbam_subset0.pth`

固定阈值：`0.30`

阈值来源：validation set 中 F1 较优阈值，测试集只用于一次性锁定报告，不反向调参。

## 3. Bootstrap 统计设计

新增脚本：

- `experiments/bootstrap_fpred_metrics.py`
- `experiments/plot_fpred_publication_figure.py`

bootstrap 设置：

| 项目 | validation | independent test |
|---|---:|---:|
| bootstrap 次数 | 2000 | 2000 |
| 随机种子 | 20260614 | 20260614 |
| 重采样单位 | candidate | seriesuid |
| 固定阈值 | 0.30 | 0.30 |

说明：测试集预测文件包含 `seriesuid`，因此测试集采用扫描/病例级重采样，更接近医学影像评估口径。验证集预测文件未保存 `seriesuid`，因此使用候选级重采样。

## 4. 结果

### 4.1 独立测试集

| 指标 | 点估计 | 95% CI |
|---|---:|---:|
| AUC | 0.9926 | 0.9731-1.0000 |
| accuracy | 0.9709 | 0.9302-1.0000 |
| precision | 0.7500 | 0.3333-1.0000 |
| sensitivity | 0.8571 | 0.5000-1.0000 |
| specificity | 0.9792 | 0.9362-1.0000 |
| F1 | 0.8000 | 0.4444-1.0000 |

固定阈值 0.30 下的混淆矩阵：

|  | Pred + | Pred - |
|---|---:|---:|
| True + | 6 | 1 |
| True - | 2 | 94 |

### 4.2 验证集对照

| 指标 | validation | independent test |
|---|---:|---:|
| AUC | 0.9945 | 0.9926 |
| accuracy | 0.9826 | 0.9709 |
| precision | 0.9474 | 0.7500 |
| sensitivity | 0.9474 | 0.8571 |
| specificity | 0.9896 | 0.9792 |
| F1 | 0.9474 | 0.8000 |

## 5. 新增论文级图表

已生成三种格式：

- `docs/world_frontier/luna16/patch_test_103/metrics/fpred_publication_validation.png`
- `docs/world_frontier/luna16/patch_test_103/metrics/fpred_publication_validation.pdf`
- `docs/world_frontier/luna16/patch_test_103/metrics/fpred_publication_validation.svg`

该图包含三个面板：独立测试集指标及 95% bootstrap CI、验证集与测试集固定阈值对照、测试集混淆矩阵。它适合直接进入结题汇报和论文结果部分。

## 6. 可写入论文的审慎结论

在 LUNA16 subset0 的独立候选级测试中，微调后的 ResNet-CBAM FPRED 分支在固定阈值 0.30 下获得 AUC 0.9926（95% CI: 0.9731-1.0000），敏感度 0.8571（95% CI: 0.5000-1.0000），特异度 0.9792（95% CI: 0.9362-1.0000）。结果提示该分支在公开数据子集上具备较强的假阳性削减能力，但由于测试集阳性候选仅 7 个，敏感度与精确率置信区间较宽，仍需扩展至更多 LUNA16 子集并回接完整 FROC/CPM 检测评价。

不能写成：

> 本系统已经达到完整 LUNA16 官方世界前沿水平。

可以写成：

> 本阶段结果证明，系统已从本地病例演示升级为具备公开数据、固定阈值、独立测试、置信区间和论文级图表的可复现科研闭环。

## 7. 下一轮必须继续推进

1. 在磁盘允许的前提下扩展到更多 LUNA16 subset，增加测试阳性数。
2. 将 FPRED 概率回接到完整 detection candidate 流，生成 LUNA-style prediction CSV。
3. 使用官方或等价 FROC/CPM 脚本评价端到端检测，而不只评价候选分类。
4. 增加模型消融：原始 ResNet-CBAM、微调 ResNet-CBAM、不同阈值策略、是否使用 CBAM。
5. 按 CLAIM 2024 补齐论文方法学披露：数据来源、排除标准、预处理、阈值选择、统计区间、局限性。
