# Step060：补实验执行批次智能体

## 本步目标

把 Step059 已批准的补实验计划转换为研发人员可以实际执行、逐环节确认、上传原始数据并人工复核的执行批次，同时保持“无真实测量不生成结果、不自动训练、不控制设备”的边界。

## 已实现

1. 新增 `SupplementaryExperimentExecutionAgent`，独立保存补实验执行血缘，不伪装成工艺优化验证批次。
2. 只允许从当前、已批准且未过期的 `supplement-plan-*` 创建执行批次。
3. 每个计划候选只能创建一个执行批次；`commandId` 支持幂等重试，批次编号在实验内唯一。
4. 冻结计划版本、候选方案、模型、可靠性报告、工艺参数、模型特征、重复次数和采样要求。
5. 实现六环节顺序状态机：
   - 实验准备；
   - 设备与环境确认；
   - 参数执行；
   - 采样与重复测量；
   - 原始数据归档；
   - 人工完成确认。
6. 前一环节未完成时禁止越序；采样完成后明确进入“等待原始数据”。
7. 原始数据归档必须关联当前实验的数据资产，并通过内容寻址 SHA-256 完整性校验。
8. 全部步骤完成后进入人工复核；批准形成不可变完成记录，驳回则重新打开人工确认环节并保留审计事件。
9. 工艺优化页新增“补实验执行批次”中文工作台，展示当前环节、等待环节、完成环节、冻结参数、采样要求、上传入口、资产状态和人工复核。
10. 修复 Windows CRLF 文本持久化时换行转换导致内容摘要不一致的问题：对象存储改为 UTF-8 字节写入和读取，保证上传原文与摘要一致。

## API

- `GET/POST /experiments/{id}/supplementary-execution-batches`
- `GET /experiments/{id}/supplementary-execution-batches/{batchId}`
- `POST /experiments/{id}/supplementary-execution-batches/{batchId}/start`
- `POST /experiments/{id}/supplementary-execution-batches/{batchId}/steps/{stepKey}`
- `POST /experiments/{id}/supplementary-execution-batches/{batchId}/assets`
- `POST /experiments/{id}/supplementary-execution-batches/{batchId}/review`

## 真实运行验收

- 实验：`exp-06c5e0b50fd0`
- 来源设计：`supplementary-design-975bd111afdb`
- 来源计划：`supplement-plan-c6a663e4f5ed`
- 来源候选：`supplement-candidate-coverageRecovery`
- 执行批次：`supplement-execution-51abaf1b991d`
- 批次编号：`SUP-20260721-RUNTIME-01`
- 冻结参数：38.0 ℃、pH 6.94、48 h、196 rpm
- 独立重复要求：3 次
- 六个步骤最终状态：全部 `completed`
- 关联资产：`file-a6365ec6-1dd5-482e-bf15-aa504edc0b95`
- 资产文件：`step060-execution-manifest-v2.csv`
- 资产摘要：`7aa1b08a3860f3af9d864bb17b2220013f18abe6b84020bfd57423e6ed2ecd38`
- 完整性校验：`true`
- 人工复核：`approved`
- 批次最终状态：`completed`

验收文件明确标记为系统工作流样例、不是实际研发测量；本次验收没有录入或伪造产物测量结果。

## 边界核验

- 模型注册表仍为 2 个既有版本：`model-modeling-v2`、`model-modeling-v1`。
- 可靠性报告仍为 2 份，最新报告 `admissionAllowed=false`。
- Step057 验证批次仍为 19 个，没有因 Step060 自动生成真实反馈批次。
- Step058 重训练活动仍为 3 个，没有因执行批次完成而自动训练。
- 没有发送任何设备控制命令。

## 自动化验证

- Step060 智能体与 API 定向测试：`6 passed`。
- CRLF 内容完整性回归测试通过。
- 后端全量回归：`261 passed, 1 skipped`。
- 前端 TypeScript 检查通过。
- 前端生产构建通过。
- 优化页面 HTTP 200，服务端输出包含“补实验执行批次”和真实验收批次编号。
- 页面地址：`http://127.0.0.1:3001/experiments/exp-06c5e0b50fd0/optimization`。

## 下一步

Step061 应实现“执行批次到真实测量反馈”的显式交接：从已完成执行批次创建测量录入任务，继承计划和资产血缘，要求目标指标、单位、方法和至少三个独立重复，经过质量与人工门禁后才生成反馈数据资产。该交接仍不得自动训练或切换模型。
