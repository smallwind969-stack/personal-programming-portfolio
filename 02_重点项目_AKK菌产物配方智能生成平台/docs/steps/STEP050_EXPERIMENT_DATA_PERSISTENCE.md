# Step050：实验数据资产持久化与重启恢复

日期：2026-07-20

## 已完成

- 新增 `SqliteExperimentDataStore`。
- 原始文件使用 SHA-256 内容寻址存储。
- SQLite 持久化：
  - 文件资产及解析行；
  - 文件审计事件；
  - 字段人工确认集合；
  - 数据收集定位智能体运行；
  - 建模数据集快照。
- API 启动时自动恢复上述状态。
- 已确认接入运行恢复后仍保留人工确认后的标准字段和单位。
- 新增原始文件完整性校验：
  - 对象缺失返回冲突；
  - 内容 hash 不一致返回冲突；
  - 页面显示“SHA-256 已验证”。
- 新增软删除：
  - 必须填写操作人；
  - 必须填写删除原因；
  - 元数据不再出现在活动资产列表；
  - 原始内容对象继续保留；
  - 生成带操作人和原因的删除审计。
- 快照门禁加强：
  - 无活动文件禁止创建；
  - 无人工字段确认禁止创建；
  - 字段映射引用已删除文件时禁止创建。
- Docker API、Worker 与分布式 Worker 共用 `/app/data` 持久卷。

## 新增接口

- `GET /experiments/{experimentId}/files/{assetId}/integrity`
- `DELETE /experiments/{experimentId}/files/{assetId}`

## 环境变量

- `EXPERIMENT_DATA_STORE_PATH`
- `EXPERIMENT_OBJECT_STORE_PATH`

## 自动验证

- Step050 持久化测试：`5 passed`
- 后端全量测试：`213 passed, 1 skipped`
- TypeScript：通过
- Next.js 生产构建：通过
- Worker：通过
- Docker Compose：通过

## 真实重启恢复验收

验收实验：`exp-0ab16e9a23ea`

服务重启前创建并确认：

- 文件资产：`file-947d7b5b-0713-475a-9868-60bddbddf3e6`
- 接入运行：`intake-4155fc550a4a`
- 快照：`dataset-203a28a5-293f-450a-9bec-948f9eda1822`

完全停止并重新启动 API 后验证：

- 活动文件恢复：1；
- 接入运行状态：`confirmed`；
- 字段映射恢复：2；
- 快照 ID 完全一致；
- 原始文件完整性：`true`；
- 存储方案：`content-addressed-sha256`；
- 浏览器恢复接入运行并显示“SHA-256 已验证”。

## 下一步

Step051 将数据清洗、单位实际换算和时间轴对齐从现有预览工具升级为有版本、有参数、有质量报告的持久化智能体运行，并把转换前后数据差异完整展示给用户。
