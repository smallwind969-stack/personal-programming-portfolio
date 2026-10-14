# STEP045 完成记录：特征绑定建议智能体与企业设备适配包

日期：2026-07-20

## 本步目标

把已晋升数学模型安全接入仿真参数体系。智能体负责生成可解释的候选映射，人工负责最终确认；任何候选都不能直接激活模型或控制真实设备。

## 已实现

1. 新增 `FeatureBindingAdvisorAgent`，以确定性别名和单位规则为第一判断来源。
2. 可选接入 Ollama 或 OpenAI-compatible 本地大模型；只发送模型特征、标准字段、单位和范围，不发送原始实验行或密钥。
3. 大模型输出使用严格 JSON 合同，额外控制字段、未知特征和未知仿真参数全部拒绝。
4. 规则与模型发生冲突时保留规则结果，标记 `providerConflict` 并转人工复核。
5. 新增 SQLite 建议运行存储；API 与独立 Worker 可跨进程读取，同一实验、模型和 `commandId` 幂等。
6. 建议智能体接入统一 Agent Registry、企业设备适配工作流、命令队列和 Worker 执行注册表。
7. 新增异步入队、建议结果查询、正式绑定确认 API。
8. 新增版本化企业设备适配包，支持导入、导出、内容哈希校验和版本防覆盖。
9. 仿真页面新增“设备适配与特征绑定”入口，显示任务状态、证据、冲突、置信度、换算参数和人工确认区。
10. 只有填写确认人、确认依据并补齐全部映射后，前端才允许生成正式绑定版本。

## 关键接口

- `POST /simulation/experiments/{experimentId}/models/{modelVersion}/binding-suggestion-runs/enqueue`
- `POST /simulation/experiments/{experimentId}/models/{modelVersion}/binding-suggestion-runs`
- `GET /simulation/experiments/{experimentId}/binding-suggestion-runs/{runId}`
- `POST /simulation/experiments/{experimentId}/model-bindings`
- `POST /simulation/device-adapter-packs/export`
- `POST /simulation/device-adapter-packs/import`
- `GET /simulation/device-adapter-packs`

## 安全边界

- 建议运行的 `activatedBindingVersion` 恒为 `null`。
- 本地大模型仅提供候选，不拥有确认权限。
- Worker 只生成建议记录，不调用设备协议或控制接口。
- 正式绑定仍是研发仿真输入，不是现实产线控制指令。

## 下一步

Step046 将企业设备适配包真正纳入建议上下文：按企业、设备类型和版本选择适配包，优先复用已确认映射，并记录适配包内容哈希到正式绑定审计链。
