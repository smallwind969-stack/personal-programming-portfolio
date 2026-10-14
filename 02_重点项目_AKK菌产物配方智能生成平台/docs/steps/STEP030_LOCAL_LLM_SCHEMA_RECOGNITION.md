# Step030：本地 LLM 字段识别智能体

日期：2026-07-20

## 本步目标

将用户本地 LLM 作为受约束的字段识别能力接入现有数据分析多智能体工作流。模型只生成字段映射候选；确定性策略负责校验、合并、回退和人工确认门禁。

## 已实现能力

- 新增供应商无关的 `SchemaRecognitionProvider` 协议。
- 新增 Ollama 与 OpenAI-compatible 本地模型提供器，采用严格 JSON 输出、低温度和有界输出。
- 模型输入仅包含资产信息、字段名和最多 3 个样本值，不提交完整文件、内容哈希、内部路径或密钥。
- Pydantic 严格拒绝未声明字段；非法 JSON、超时、不可达和禁用状态均转换为脱敏失败类别。
- 新增确定性字段安全策略：原字段存在性、标准字段命名、数据类型、置信度、单位白名单、单位维度和危险内容校验。
- 规则与 LLM 一致时生成 `merged` 候选；冲突、LLM 单独建议、未知单位、单位维度冲突和低置信度进入人工确认。
- 新增 `SchemaRecognitionAgent`，支持不可变运行快照、命令幂等和并发去重。
- 同一命令并发请求只调用一次模型；不同实验可并行调用，不被全局锁串行化。
- 新增创建/查询接口：
  - `POST /experiments/{experimentId}/schema-recognition-runs`
  - `GET /experiments/{experimentId}/schema-recognition-runs/{runId}`
- 字段识别能力已经绑定到统一数据分析工作流的 `schema-recognition` 节点；节点执行结果写入供应商无关的运行时状态。
- 前端字段识别节点新增结果卡，展示模式、提供器、候选、冲突、待确认原因、置信度和回退原因。
- 候选不会自动写入正式映射；正式映射仍只能通过既有人工确认接口提交。
- 新增 `SCHEMA_RECOGNITION_LLM_ENABLED` 显式开关，默认关闭以保证安全和稳定；设置为 `true` 后才调用本地模型。

## TDD 证据

- 首次运行因 `app.schema_recognition` 不存在而在测试收集阶段失败。
- 本地提供器/API 测试首次运行因适配器与路由不存在而失败。
- 工作流绑定测试首次因运行时缺少 `schemaRecognition` 状态而失败。
- 严格 JSON 与并发测试首次分别因额外字段被忽略、全局锁导致屏障超时而失败。
- 单位维度测试首次因 `unitDimensionConflict` 未生成而失败。
- 完成最小实现与加固后，所有上述测试转绿。

## 最终验证

- 后端全量：`py -m pytest -q`，95 项通过，0 失败。
- 前端类型：`npm.cmd run typecheck`，通过。
- 前端生产构建：`npm.cmd run build`，通过，11 个页面生成成功。
- HTTP 冒烟：上传设备 CSV → 创建字段识别运行 → 读取相同快照 → 规则安全回退；结果为 2 个候选，正式映射数量保持 0。

## 安全边界

- LLM 不修改原始数据。
- LLM 不执行单位换算或清洗。
- LLM 不训练、晋升或发布模型版本。
- LLM 不下发真实产线控制指令。
- 所有输出仍属于研发实验建议，必须经过人工和现实实验验证。

## 主要修改文件

- `apps/api/app/schema_recognition/contracts.py`
- `apps/api/app/schema_recognition/policy.py`
- `apps/api/app/schema_recognition/local_llm_provider.py`
- `apps/api/app/services/schema_recognition_agent.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/services/agent_orchestrator.py`
- `apps/api/app/schemas/experiments.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_schema_recognition_agent.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/schema-recognition-run-card.tsx`
- `apps/web/components/experiments/agent-execution-center.tsx`
- `apps/web/lib/schema-recognition-contract.test-d.ts`

## 下一步建议

Step031 将同一受约束能力协议扩展到“实验结果解释智能体”：只允许引用已验证指标、模型评估和证据版本生成结构化解释与研发建议，禁止把语言模型文本当作数学模型结果或真实生产结论。
