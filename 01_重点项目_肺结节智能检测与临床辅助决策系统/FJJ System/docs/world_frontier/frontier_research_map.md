# 肺结节检测 Agent 项目前沿化研究地图

生成日期：2026-06-14

## 1. 不能再使用的弱评价口径

本项目后续不应以普通准确率、单例截图或少量病例演示作为核心科研证据。肺结节检测属于 3D CT 小目标检测问题，主流公开评价口径应转向 FROC 曲线与 CPM。

LUNA16 官方任务要求模型在原始 CT 上输出候选结节位置与概率，检测性能通常按多个 false positives per scan 水平下的 sensitivity 评价。项目内新增的 `experiments/froc_eval.py` 已按这一口径实现基础版 FROC/CPM。

## 2. 公开基准与数据源

| 数据/基准 | 用途 | 对项目的意义 | 来源 |
|---|---|---|---|
| LIDC-IDRI | 胸部 CT + 四名放射科医师两阶段标注 | 肺结节检测/恶性风险研究的核心公开数据源 | TCIA: https://www.cancerimagingarchive.net/collection/lidc-idri/ |
| LUNA16 | 基于 LIDC-IDRI 的自动结节检测挑战 | 必须对齐的检测评价基准，使用 FROC/CPM | Grand Challenge: https://luna16.grand-challenge.org/ |
| LUNA16 Data | annotations、candidates、sample submission | 可用于候选生成、假阳性过滤、FROC 评价 | https://luna16.grand-challenge.org/Data/ |
| MONAI Lung Nodule CT Detection | LUNA16 相关 3D 检测 bundle | 可作为工程对齐和预训练/推理参考 | NVIDIA NGC: https://catalog.ngc.nvidia.com/orgs/nvidia/teams/monaitoolkit/models/monai_lung_nodule_ct_detection |
| Medical Segmentation Decathlon Task06 Lung | 肺部肿瘤分割 | 可作为分割能力和泛化实验补充，不等同 LUNA16 检测 | MSD: https://medicaldecathlon.com/ |

## 3. 近年前沿方法的共性

当前强方法通常不只做单一分类，而是围绕以下链路展开：

1. 3D 候选生成：3D U-Net、3D RPN、Faster R-CNN 变体、多尺度编码器。
2. 假阳性过滤：3D CNN、ResNet、注意力模块、多尺度 patch。
3. 评价闭环：FROC、CPM、false positives per scan，而非简单 accuracy。
4. 临床可用性：推理速度、医生复核、人机协同、随访建议边界。
5. 泛化验证：公开数据集训练/测试、本地小样本复核、外部数据集验证。

已有公开论文中，LUNA16 上 CPM 约 0.90 以上才有资格被称为接近强基线。例如 3D RPN 类方法报道过 CPM 0.901，多尺度注意力方法报道过 CPM 0.927，近年多尺度卷积方法报道过 CPM 0.929。项目不能拿当前 3 例 review-proxy 结果与这些数字直接比较，必须先接入公开基准。

## 4. 临床 Agent 的边界

随访建议不能由大模型自由发挥。后续 Agent 应将建议拆成：

- 结构化影像事实：大小、类型、位置、毛刺、分叶、胸膜牵拉、增长情况。
- 风险上下文：年龄、吸烟史、肿瘤史、症状、既往 CT。
- 指南提示：Fleischner 2017、NCCN Lung Cancer Screening 更新等。
- 安全声明：AI 建议不能替代影像科、呼吸科或胸外科医生决策。

参考来源：

- Fleischner Society 2017 pulmonary nodule guideline, Radiology. DOI: 10.1148/radiol.2017161659
- NCCN Guidelines Insights: Lung Cancer Screening, Version 1.2025. PubMed: https://pubmed.ncbi.nlm.nih.gov/39819601/

## 5. 当前项目到前沿水平的差距

| 维度 | 当前状态 | 前沿/投稿所需状态 | 下一步 |
|---|---|---|---|
| 数据规模 | 本地 3 例，607 张 DICOM | LUNA16/LIDC-IDRI 级别公开基准 + 本地复核集 | 接入 LUNA16 annotations 和 candidates |
| 真值标准 | doctor_review.json 构成 review-proxy | 结节级标注，明确直径、坐标和匹配半径 | 完成医生复核并导出标准 CSV |
| 检测指标 | precision/recall proxy | FROC、CPM、sensitivity at FP/scan | 使用 `experiments/froc_eval.py` |
| 调参 | 已暴露 VNet/ResNet 阈值 | 系统网格搜索 + 验证集选择 | 增加批量实验与结果缓存 |
| 模型强度 | VNet + ResNet-CBAM + 双分支识别 | 与 MONAI/LUNA16 强基线对齐或消融比较 | 建立 baseline 对照 |
| 工程性能 | CPU 单例 229-316 秒 | GPU 推理、缓存、可复现实验日志 | 增加缓存和 GPU 配置文档 |
| Agent 安全 | 有基础安全声明 | 指南约束、缺失信息追问、禁忌输出审计 | 建立指南规则层与测试 |

## 6. 下一阶段实验里程碑

1. `M1`: 下载或挂载 LUNA16 元数据，跑通 annotations/predictions CSV 校验。
2. `M2`: 将当前模型输出转换为 LUNA16 submission 格式：`seriesuid,coordX,coordY,coordZ,probability`。
3. `M3`: 用 FROC/CPM 在公开格式上评价，生成可复现表格。
4. `M4`: 与 MONAI lung nodule detection bundle 或公开 baseline 对齐，形成强基线比较。
5. `M5`: 做消融：无 CBAM、无 ResNet 过滤、不同 VNet 阈值、不同 patch/stride。
6. `M6`: Agent 层接入指南约束，输出“建议 + 证据 + 缺失信息 + 安全边界”。

## 7. 本轮已完成的前沿化动作

- 新增 LUNA16-style `experiments/froc_eval.py`。
- 新增 FROC 单元测试，覆盖重复预测只算一个 TP 的关键规则。
- 明确当前 PDF 结果属于本地阶段性证据，不包装成临床验证。
- 将下一阶段目标从“写论文”改为“公开基准 + FROC + 消融 + 指南约束 Agent”。
- 新增 `agent/guideline_rules.py`，为 follow-up Agent 提供 Fleischner-like 指南提示、筛查场景提示、缺失信息审计和禁用语安全审计。
- 新增 `experiments/audit_followup_agent.py`，已对 3 个真实本地病例完成离线安全审计，当前 `failed=[]`。
- 新增 `experiments/luna16_data_manager.py`，已联网下载并校验 LUNA16 `annotations.csv` 与 `sampleSubmission.csv`。
- 新增 `experiments/validate_luna_submission.py`，已验证官方 sample submission 通过，本地导出 CSV 格式有效但不属于 LUNA16 seriesuid。
- 已下载并解压 `evaluationScript.zip` 与 `candidates_V2.zip`；当前本地统计 `candidates_V2.csv` 为 754975 行，覆盖 888 个 CT 序列。
- 新增 `experiments/make_luna16_fpred_splits.py`，生成 9342 条平衡 FPRED 候选清单，按 seriesuid 划分 train/val/test。
- 已下载并解压 LUNA16 `subset0.zip`，索引 89 个真实 CT 体数据。
- 新增 MetaImage 直读层、patch 抽取脚本和 ResNet-CBAM smoke inference，已在 subset0 中抽取 16 个 32³ patch 并完成模型前向验证。
- 新增 subset-aware 候选清单与 FPRED 评估器；已在 subset0/val 的 115 个候选 patch 上完成 ResNet-CBAM 批量评估，候选级 AUC=0.9759。
- 新增 `experiments/train_fpred_resnet.py`，完成 subset0/train 256 patch 上的 ResNet-CBAM 微调；subset0/val 115 patch 候选级 AUC 提升至 0.9945。
- 固定 val 选择阈值 0.30，在 subset0/test 103 patch 上完成独立测试；test AUC=0.9926，sensitivity=0.8571，specificity=0.9792。
