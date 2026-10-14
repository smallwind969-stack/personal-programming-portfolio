# Step051：数据清洗与时间轴对齐智能体

日期：2026-07-20

## 本步骤目标

把原有“清洗预览”升级为真正参与建模数据生产的多智能体节点。它必须执行真实换算和对齐，保存运行版本与质量证据，并在进入建模前设置可审计的人工作业门禁。

## 已完成

- 新增持久化 `CleaningAlignmentAgent`。
- 每次运行生成独立 `runId`、递增版本号、创建时间。
- 根据已确认字段映射执行真实单位换算：
  - `target = source × scale + offset`
  - 支持转换前后样例证据。
- 将不同格式时间统一为 UTC ISO 8601。
- 按标准时间字段合并多设备数据，生成用于后续建模的对齐宽表。
- 生成数据质量报告：
  - 缺失值；
  - 无效数值；
  - 无效时间；
  - 重复时间；
  - 未映射字段。
- 对输入资产、映射和配置生成不可变输入指纹。
- 对清洗输出生成 SHA-256 输出哈希。
- 输入数据发生变化后，旧运行会被判定为过期，禁止用于创建新快照。
- 质量报告存在问题时进入 `needsReview`，必须记录操作人和人工判断依据后才能放行。
- 建模数据集快照现在保存：
  - `cleaningRunId`；
  - `cleaningOutputHash`；
  - 实际对齐结果行。
- 训练数据导出优先使用快照中已经锁定的清洗对齐结果。
- 新增中文工作台，展示算法状态、质量指标、换算公式、转换样例、输入指纹、输出哈希和人工复核入口。
- 建模快照按钮增加前置门禁：清洗未完成或待人工复核时不可创建。

## 新增接口

- `POST /experiments/{experimentId}/cleaning-alignment-runs`
- `GET /experiments/{experimentId}/cleaning-alignment-runs`
- `GET /experiments/{experimentId}/cleaning-alignment-runs/latest`
- `POST /experiments/{experimentId}/cleaning-alignment-runs/{runId}/review`

## 自动验证

- 后端全量测试：`217 passed, 1 skipped`
- 前端 TypeScript 检查：通过
- Next.js 生产构建：通过
- Worker 命令入口：通过
- Docker Compose 配置：通过
- `git diff --check`：通过，仅有既有行尾转换提醒

自动测试覆盖：

- 华氏温度到摄氏温度的真实数值换算；
- 时间戳 UTC 规范化；
- 质量问题门禁与人工放行；
- 输入变化后的过期指纹拦截；
- 服务重启后的运行记录恢复；
- 快照对清洗运行和输出哈希的血缘绑定。

## 运行态验收

验收实验：`exp-0ab16e9a23ea`

- 清洗运行：`clean-align-01c8333c7957`
- 输入指纹：`sha256:3b20b132f913fb4b612ef4ab0b8c4959aec5868672a971a551ba052aacd3bed9`
- 输出哈希：`sha256:258986523edda4fbee0d40552b48839abb8e227379b2658cdaf493f6eee8681c`
- 生成对齐结果：1 行
- 数据质量问题：0
- 快照：`dataset-2e1e47fe-e090-4494-8893-46513bd18bf7`
- 快照已绑定上述清洗运行和输出哈希。
- 前端代理再次执行后生成运行版本 2：`clean-align-a9c5cb40e409`

运行态截图：`artifacts/step051-analysis.png`

## 架构定位

`DataCollectionLocalizationAgent` 继续负责数据接入业务编排；`ExperimentFileService` 仍是底层文件工具。`CleaningAlignmentAgent` 是接入确认之后、建模快照之前的独立专业智能体，不替代数据收集定位智能体。

## 下一步

Step052 将把特征工程从演示节点升级为版本化智能体：定义目标变量和可用特征、自动生成时序/统计/过程特征、执行数据泄漏检查、保存特征字典与特征集版本，并让建模智能体只能消费通过人工确认的特征集。
