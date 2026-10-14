# 多智能体运行时技术选型（Step 026）

## 结论

平台主编排层选择 **LangGraph 风格的可持久状态图**，通过自有 `AgentRuntimeAdapter` 隔离具体框架；第一版先保持确定性内存适配器，下一版增加可选 LangGraph 适配器和本地 LLM 适配器。

不直接以 AutoGen 作为新项目核心：其官方仓库已声明进入维护模式，并建议新用户转向 Microsoft Agent Framework。CrewAI 保留为“产品创新/论文协作小队”的候选子运行时，但不承担实验数据、仿真和版本晋升的核心状态机。

## 选择依据

### LangGraph：核心编排层

- 官方定位是长时间运行、有状态智能体的低层编排框架。
- 原生强调 durable execution、human-in-the-loop、memory 和状态恢复。
- 与当前平台已经实现的节点、合法边、检查点、人工中断、事件、版本和重启语义一致。
- 可把本地 LLM、规则节点、传统机器学习任务和人工审核作为不同节点，不强迫所有步骤都使用大模型。

官方仓库：https://github.com/langchain-ai/langgraph

### CrewAI：自治协作子系统候选

- `Flows` 适合受控事件流，`Crews` 适合角色化自治协作。
- 可用于后续产品创新智能体、文献研究小队和论文写作小队。
- 不作为核心版本事务层，避免自治对数据版本和设备安全边界产生越权。

官方仓库：https://github.com/crewAIInc/crewAI

### AutoGen：不作为新核心

- 官方仓库已标注 maintenance mode。
- 其多智能体对话思想仍可借鉴，但不新增核心依赖。

官方仓库：https://github.com/microsoft/autogen

### autoresearch：借鉴实验循环，不直接嵌入产线

- 借鉴“固定可修改范围、固定时间/资源预算、单一权威评估指标、保留或丢弃实验、完整结果日志”的研究循环。
- 平台中的 `ModelResearchAgent` 只能修改受控训练配置或沙箱脚本，不能修改数据清洗规则、评估基准、版本注册表或设备控制代码。
- 每轮候选模型必须经过确定性评估、风险门禁和人工批准，才能晋升为权威模型版本。

官方仓库：https://github.com/karpathy/autoresearch

## 目标接口

```python
class AgentRuntimeAdapter(Protocol):
    def start(self, definition, initial_state, context) -> RuntimeSnapshot: ...
    def advance(self, run_id, command) -> RuntimeSnapshot: ...
    def interrupt(self, run_id, reason) -> RuntimeSnapshot: ...
    def resume(self, run_id, human_decision) -> RuntimeSnapshot: ...
    def events(self, run_id) -> list[RuntimeEvent]: ...
```

上层 `AgentOrchestrator`、`SimulationRunOrchestrator`、`OptimizationOrchestrator` 只依赖该接口。运行时必须输出结构化节点结果、置信度、证据引用、风险、验证指标和审计事件，不保存或展示不可验证的隐藏思维链。

## 本地 LLM 接入原则

- 使用 OpenAI-compatible HTTP 适配器对接用户本地模型，配置 `baseUrl/model/apiKey`，不把供应商写死在业务代码。
- LLM 只负责字段候选解释、异常原因假设、方案语言组织和研究建议；清洗、单位换算、时间对齐、数学评估、版本晋升和门禁必须由确定性代码执行。
- 所有 LLM 输出先进入 Pydantic 结构化校验，再经过证据绑定与置信度校准；失败时回退规则节点并明确标记。

## 下一实现批次

1. 新建 `AgentRuntimeAdapter`、运行定义、节点结果和事件协议。
2. 把现有数据分析状态机迁移到 `DeterministicRuntimeAdapter`，保证 API/UI 不变。
3. 增加可选 `LangGraphRuntimeAdapter`，依赖未安装时安全回退。
4. 增加本地 LLM 健康检查与结构化调用适配器，但默认关闭。
5. 新增 `ModelResearchAgent` 沙箱协议，复用 autoresearch 的固定预算和权威评估思想。

## 安全边界

当前阶段不连接真实设备，不自动下发产线参数，不允许智能体直接晋升模型或结果版本。任何对权威数据、模型、仿真结果和未来设备控制的变更，都必须经过确定性校验与人工审核。
