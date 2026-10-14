# STEP043 完成记录：晋升模型注册与可信仿真推理

日期：2026-07-20

## 已实现

1. 新增 SQLite 晋升模型注册表，保存模型版本、实验、campaign、trial、数据快照、产物摘要、特征范围、指标和人工批准信息。
2. 模型版本注册幂等；相同版本不能被不同训练血缘覆盖。
3. sklearn Runner 保存每个特征的训练最小值和最大值。
4. 只有 `real_runner` 且通过指标门禁、完成人工批准、血缘完整的模型才进入可推理注册表；mock 不会注册成真实模型。
5. 新增受控 joblib 加载：只接受本系统内容寻址 URI，加载前校验 SHA-256，并复核模型内特征合同。
6. 推理按具名特征重排输入，拒绝缺失、非数值、非有限值和默认情况下的训练范围外输入。
7. 显式允许外推时返回 `extrapolated` 和越界特征列表。
8. 新增实验级真实模型推理 API：`POST /simulation/experiments/{experimentId}/promoted-model/predict`。
9. 新增已批准模型版本列表 API：`GET /simulation/experiments/{experimentId}/promoted-models`。
10. 通用仿真响应和前端结果区明确展示预测来源；规则仿真标记为 `rule_model`，不会伪装成真实训练模型。

## 真实闭环验证

自动化集成测试执行了：构造数值数据 → sklearn 真实训练 → 生成内容寻址产物 → 人工批准 → 注册模型版本 → 摘要校验 → 加载模型 → 具名特征预测。

- 真实 Runner：`real_runner sklearn-gradient-boosting-v1`
- 模型注册表：持久化 SQLite 路径成功加载。
- 后端：`178 passed, 1 skipped`；跳过项仍为需要 Docker daemon 的 PostgreSQL 在线集成测试。
- 前端：TypeScript 检查通过，Next.js 生产构建通过。
- Worker：真实 Runner 与模型注册表配置下导入及 CLI 通过。
- Docker Compose：配置校验通过；仅有本机 Docker 用户配置文件权限警告。

## 安全边界

- 不接受任意文件路径或外部上传的 joblib。
- joblib 仅限企业内部可信训练产物，且必须先通过摘要校验。
- 真实预测仍是“研发实验建议”，需要小试、中试和人工审核，不直接形成设备控制指令。
- 输入超出训练分布时默认拒绝，避免无提示外推。

## 下一步

Step044 将建立“仿真变量映射合同”：把设备字段字典和标准工艺变量映射到模型特征，支持一个实验的多目标模型组合，并把真实预测转换成仿真仪表盘可展示的产物指标和置信区间。

