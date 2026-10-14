# Step057：真实实验反馈与重训练资格闭环

## 本步目标

把工艺优化后的批准参数带回真实小试或中试，建立可追溯的验证批次；真实测量通过质量门禁和人工确认后，生成可供后续机器学习智能体使用的数据资产。本步不自动重训练、不自动晋升模型，也不发送真实产线控制指令。

## 已实现

1. 新增 `ExperimentalFeedbackAgent`，负责验证批次、测量回流、质量门禁、人工复核和数据资产沉淀。
2. 验证批次强制绑定：优化运行、工艺参数版本、预测结果版本、父模型版本和父仿真运行。
3. 支持记录实验规模、批次编号、计划时间、实际温度、pH、培养时间、搅拌速度、测量方法、重复样、污染和设备异常。
4. 质量门禁检查：
   - 血缘完整；
   - 实际参数处于批准容差；
   - 模型目标至少 3 个重复样；
   - 单位一致；
   - 测量方法完整；
   - 无污染；
   - 无设备异常；
   - 研发负责人确认。
5. 通过后生成不可混淆的 `feedback-dataset-*` 数据资产，实验工作区标记为“可以创建重训练活动”，当前模型版本保持不变。
6. 工艺优化页面新增“验证批次与重训练资格”工作台，展示完整门禁证据和人工操作入口。
7. 新增实验级 API：
   - `GET/POST /experiments/{id}/validation-batches`
   - `GET /experiments/{id}/validation-batches/{batchId}`
   - `POST /experiments/{id}/validation-batches/{batchId}/submit`
   - `POST /experiments/{id}/validation-batches/{batchId}/review`
   - `GET /experiments/{id}/optimization-runs`

## 验收结果

- 后端完整测试：`236 passed, 1 skipped`。
- 前端 TypeScript 检查通过。
- 前端生产构建通过。
- 运行时演示批次：`STEP057-DEMO-001`。
- 验证批次：`validation-batch-af1d0123768e`。
- 质量门禁：全部通过。
- 生成数据资产：`feedback-dataset-af990d6ea732`。
- 页面地址：`http://127.0.0.1:3001/experiments/exp-food-012/optimization`。

## 边界说明

- 当前“通过门禁”仅表示数据具备进入重训练候选集的资格。
- 机器学习智能体必须在下一步创建独立重训练活动，重新执行数据快照、训练、时间外验证、可靠性评估和人工晋升。
- 演示初始化血缘明确标记为 Step057 demo，不冒充新的真实实验数据。
