from __future__ import annotations

from app.agent_registry.models import AgentManifest, WorkflowManifest, WorkflowNodeManifest
from app.agent_registry.registry import AgentCatalog


def _agent(key: str, name: str, description: str, capabilities: list[str], input_schema: str, output_schema: str, *, kind: str = "specialist", worker: list[str] | None = None, framework: str = "langgraph") -> AgentManifest:
    return AgentManifest(
        agentKey=key, version="1.0.0", displayName=name, description=description, kind=kind,
        framework=framework, capabilities=capabilities, requiredWorkerCapabilities=worker or ["cpu"],
        inputSchema=input_schema, outputSchema=output_schema,
        safetyBoundary=["仅输出研发实验建议", "不得直接控制真实产线", "关键结论保留人工确认"],
    )


AGENTS = [
    _agent("featureBindingAdvisor", "特征绑定建议智能体", "结合模型清单、标准字段、单位规则、设备适配包和可选本地大模型生成候选绑定，所有候选必须人工确认。", ["feature-binding-suggestion", "unit-compatibility", "adapter-pack", "local-llm-optional", "human-review-required"], "BindingAdvisorContext", "FeatureBindingSuggestionRun"),
    _agent("dataAnalysisSupervisor", "数据分析协调", "协调数据整理、建模、评估和人工验收环节。", ["workflow-routing", "checkpoint-resume", "human-review"], "ExperimentAgentRunRequest", "ExperimentAgentRun", kind="supervisor"),
    _agent("dataCollectionLocalization", "数据收集定位智能体", "定位多设备文件、识别来源并生成不可变资产指纹。", ["file-discovery", "source-localization", "asset-fingerprint"], "ExperimentFileBundle", "LocalizedDataAssets"),
    _agent("schemaRecognition", "字段识别智能体", "识别企业字段别名、时间格式、单位和低置信映射。", ["schema-matching", "unit-detection", "review-candidates", "local-llm-optional"], "LocalizedDataAssets", "SchemaRecognitionResult"),
    _agent("cleaningAlignment", "清洗对齐智能体", "执行确定性缺失值、异常值、单位转换和时间轴对齐。", ["data-cleaning", "unit-conversion", "time-alignment"], "SchemaRecognitionResult", "AlignedDataset"),
    _agent("featureEngineering", "特征工程智能体", "生成带公式、窗口和来源说明的可复现特征。", ["feature-extraction", "formula-audit", "lag-features"], "AlignedDataset", "FeatureDataset"),
    _agent("modeling", "数学建模智能体", "训练并比较候选模型，保存参数、指标和数据版本。", ["model-training", "cross-validation", "hyperparameter-search", "gpu-optional"], "FeatureDataset", "ModelCandidateSet"),
    _agent("researchExperiment", "研究实验智能体", "锁定评测器与预算，组织基线、单变量候选和保留/丢弃实验记录。", ["baseline-control", "single-change-experiment", "keep-discard-log", "promotion-gate"], "ResearchTrialRequest", "ResearchTrial"),
    _agent("modelEvaluation", "模型评估智能体", "评估误差、稳定性、漂移和仿真准入条件。", ["model-evaluation", "confidence-calibration", "simulation-gate"], "ModelCandidateSet", "ModelEvaluationReport"),
    _agent("resultInterpretation", "结果解释智能体", "将确定性指标转成有证据引用、风险和验证项的解释。", ["evidence-grounding", "result-explanation", "experiment-suggestions", "local-llm-optional"], "ModelEvaluationReport", "ResultInterpretation"),
    _agent("humanReview", "人工确认节点", "保存决策人、理由、修改内容和正式验收版本。", ["approval", "rejection", "audit-trail"], "ReviewPackage", "HumanDecision", kind="humanGate", framework="human"),
    _agent("productInnovation", "产品需求研判", "把自然语言产品设想转成可验证、可版本化的需求。", ["requirement-structuring", "cost-estimation", "risk-screening", "local-llm-optional"], "ProductIdea", "ProductRequirementVersion"),
    _agent("simulation", "仿真模拟运行", "根据验收模型和产线参数生成阶段化仿真与预测证据。", ["process-simulation", "parameter-visualization", "reliability-report"], "SimulationRequest", "SimulationRun"),
    _agent("optimization", "工艺条件优化", "生成候选工艺、人工调参并建立模型重训版本。", ["process-optimization", "candidate-ranking", "model-retraining", "gpu-optional"], "OptimizationRequest", "OptimizationRun"),
]


DATA_NODES = [
    WorkflowNodeManifest(nodeId="data-collection", agentKey="dataCollectionLocalization", stageLabel="数据收集", inputSummary=["设备文件清单", "实验目标与批次信息"], methodSummary=["文件类型探测", "企业命名规则匹配", "SHA-256 资产指纹"], metricSummary=["文件解析率", "来源定位率"], outputSummary=["原始数据资产清单", "设备来源定位结果"]),
    WorkflowNodeManifest(nodeId="schema-recognition", agentKey="schemaRecognition", stageLabel="字段识别", inputSummary=["原始字段", "企业字段词典"], methodSummary=["别名词典匹配", "单位维度校验", "置信度阈值"], metricSummary=["自动识别率", "平均置信度"], outputSummary=["标准字段映射", "人工确认建议"]),
    WorkflowNodeManifest(nodeId="cleaning-alignment", agentKey="cleaningAlignment", stageLabel="清洗对齐", inputSummary=["标准字段映射", "设备时间序列"], methodSummary=["IQR 异常检测", "短缺口插值", "统一时间窗"], metricSummary=["时间对齐率", "缺失率"], outputSummary=["清洗数据版本", "处理规则审计表"]),
    WorkflowNodeManifest(nodeId="feature-engineering", agentKey="featureEngineering", stageLabel="特征工程", inputSummary=["对齐数据", "目标变量"], methodSummary=["滚动统计", "变化率", "滞后特征"], metricSummary=["候选特征数", "异常提示数"], outputSummary=["特征集版本", "公式与窗口清单"]),
    WorkflowNodeManifest(nodeId="modeling", agentKey="modeling", stageLabel="数学建模", inputSummary=["特征集", "目标变量"], methodSummary=["候选模型比较", "训练/验证拆分", "交叉验证"], metricSummary=["训练轮次", "候选模型数"], outputSummary=["模型版本", "超参数记录"]),
    WorkflowNodeManifest(nodeId="model-evaluation", agentKey="modelEvaluation", stageLabel="模型评估", inputSummary=["候选模型", "验证集"], methodSummary=["MAE、RMSE、R²", "折间稳定性", "数据漂移检查"], metricSummary=["泛化指标", "置信区间"], outputSummary=["模型评估报告", "仿真准入建议"]),
    WorkflowNodeManifest(nodeId="human-review", agentKey="humanReview", stageLabel="人工确认", requiresHuman=True, inputSummary=["风险与模型评估", "待确认字段映射"], methodSummary=["逐项确认", "记录决策人与理由", "生成只读验收版本"], metricSummary=["待确认项", "正式准入状态"], outputSummary=["人工决策记录", "模型验收版本"]),
]


def build_builtin_catalog() -> AgentCatalog:
    catalog = AgentCatalog()
    for manifest in AGENTS:
        catalog.register_agent(manifest)
    catalog.register_workflow(WorkflowManifest(
        workflowKey="experiment-data-analysis", version="1.0.0", displayName="实验数据分析工作流",
        description="从数据收集定位到模型人工验收的确定性 LangGraph 子图。", nodes=DATA_NODES,
        edges={DATA_NODES[index].nodeId: [DATA_NODES[index + 1].nodeId] for index in range(len(DATA_NODES) - 1)}, entryNodeId=DATA_NODES[0].nodeId,
    ))
    catalog.register_workflow(WorkflowManifest(
        workflowKey="experiment-rd-loop", version="1.0.0", displayName="实验研发闭环",
        description="产品需求、数据分析、仿真和优化组成的企业研发闭环。",
        nodes=[
            WorkflowNodeManifest(nodeId="product-innovation", agentKey="productInnovation", stageLabel="产品创新"),
            WorkflowNodeManifest(nodeId="data-analysis", agentKey="dataAnalysisSupervisor", stageLabel="数据分析"),
            WorkflowNodeManifest(nodeId="simulation", agentKey="simulation", stageLabel="仿真模拟"),
            WorkflowNodeManifest(nodeId="optimization", agentKey="optimization", stageLabel="工艺优化"),
        ],
        edges={"product-innovation": ["optimization"], "data-analysis": ["simulation"], "simulation": ["optimization"]},
        entryNodeId="data-analysis",
    ))
    catalog.register_workflow(WorkflowManifest(
        workflowKey="enterprise-device-adaptation", version="1.0.0", displayName="企业设备适配工作流",
        description="复用字段识别、特征绑定建议和人工确认节点，将企业设备字段安全接入仿真模型。",
        nodes=[
            WorkflowNodeManifest(nodeId="schema-recognition", agentKey="schemaRecognition", stageLabel="字段识别"),
            WorkflowNodeManifest(nodeId="binding-advisor", agentKey="featureBindingAdvisor", stageLabel="特征绑定建议"),
            WorkflowNodeManifest(nodeId="human-review", agentKey="humanReview", stageLabel="人工确认", requiresHuman=True),
        ],
        edges={"schema-recognition": ["binding-advisor"], "binding-advisor": ["human-review"]},
        entryNodeId="schema-recognition",
    ))
    return catalog


agent_catalog = build_builtin_catalog()
