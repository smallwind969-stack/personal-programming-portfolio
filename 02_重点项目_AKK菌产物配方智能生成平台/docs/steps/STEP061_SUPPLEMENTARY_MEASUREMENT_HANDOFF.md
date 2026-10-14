# Step061：补实验真实测量交接智能体

## 本步目标

把 Step060 已完成的补实验执行批次显式交接给真实测量录入流程。只有来源文件、目标字段、真实数值、单位、方法、重复次数、实际参数、异常状态和人工复核全部通过，才能生成反馈数据资产。

## 已实现

1. 新增 `SupplementaryMeasurementHandoffAgent`，为每个已完成执行批次建立唯一测量任务。
2. 自动继承执行批次、补实验计划、候选方案、父模型、可靠性报告、冻结参数和已验证文件资产血缘。
3. 从父模型注册记录读取目标字段，禁止将其他指标冒充模型目标。
4. 测量数据必须包含数值、单位、独立重复编号、时间、方法、来源资产和目标标记。
5. 来源资产必须属于 Step060 执行批次且已通过完整性校验。
6. 实现十一项反馈质量门禁：
   - 来源执行批次已完成；
   - 来源文件已验证；
   - 实际参数在冻结参数容差内；
   - 目标指标与父模型一致；
   - 至少三个目标重复；
   - 重复编号唯一；
   - 目标单位一致；
   - 测量方法完整；
   - 无污染；
   - 无设备异常；
   - 人工确认。
7. 任一技术门禁失败时禁止人工批准；驳回后保留测量和审计证据，不生成反馈数据资产。
8. 批准后生成带 `sourceType=supplementary_measurement` 的 `experimental_feedback_dataset`，但不自动发起重训练。
9. 扩展 Step058 数据集构建器，严格支持两种合法反馈来源：优化验证反馈和补实验测量反馈。
10. 工艺优化页新增“补实验测量与反馈资格”中文工作台；所有测量值默认空白，必须人工填写。

## API

- `GET/POST /experiments/{id}/supplementary-measurement-batches`
- `GET /experiments/{id}/supplementary-measurement-batches/{batchId}`
- `POST /experiments/{id}/supplementary-measurement-batches/{batchId}/submit`
- `POST /experiments/{id}/supplementary-measurement-batches/{batchId}/review`

## 安全运行验收

- 实验：`exp-06c5e0b50fd0`
- 来源执行批次：`supplement-execution-51abaf1b991d`
- 测量任务：`supplement-measurement-76eee525002e`
- 状态：`draft`
- 补实验计划：`supplement-plan-c6a663e4f5ed`
- 父模型：`model-modeling-v2`
- 父模型目标：`od600`
- 允许来源资产：`file-a6365ec6-1dd5-482e-bf15-aa504edc0b95`
- 来源文件：`step060-execution-manifest-v2.csv`
- 当前测量数量：0
- 当前质量门禁：尚未计算

验收只证明任务建立、血缘继承和空白人工录入入口工作正常。由于没有真实研发测量，本次没有提交或批准测量任务。

## 不变性核验

- `experimental_feedback_dataset` 仍为 19 个，没有因创建空白任务新增反馈数据。
- 补实验测量任务为 1 个，且保持 `draft`。
- 反馈重训练活动仍为 3 个。
- 模型注册表仍为 2 个既有版本。
- 可靠性报告仍为 2 份，最新 `admissionAllowed=false`。
- 没有自动训练、晋升、模型切换或设备控制行为。

## 自动化验证

- Step061 智能体、API 和反馈构建兼容定向测试：`13 passed`。
- 后端全量回归：`270 passed, 1 skipped`。
- 前端 TypeScript 检查通过。
- 前端生产构建通过。
- 优化页面 HTTP 200，包含“补实验测量与反馈资格”、测量任务和 `od600` 目标。
- 页面地址：`http://127.0.0.1:3001/experiments/exp-06c5e0b50fd0/optimization`。

## 下一步

Step062 应实现实验任务的跨阶段总览与闭环状态投影：在实验归档和实验详情页统一展示“数据分析→模型评估→补实验设计→执行→真实测量→重训练”的当前节点、等待原因、证据版本和人工入口，避免用户必须进入工艺优化页寻找每个环节。
