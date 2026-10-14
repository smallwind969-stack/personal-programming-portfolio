# Step037 仿真/优化统一队列与任务治理

## 本步结果

统一命令队列已经从数据分析扩展到仿真模拟和工艺优化，并补齐跨进程领域运行存储、优先级、实验级并发上限、取消和死信重放。

## 统一 Worker 分派

支持的目标：

- `dataAnalysis`
- `simulation`
- `optimization`

支持的后台动作：

- 数据分析：推进、终止。
- 仿真：创建、推进、停止、失败重试。
- 优化：创建、正式提交、重训阶段推进。

候选方案编辑、临时仿真试算和人工验收仍保持同步，因为它们属于用户即时交互或人工决策，不应被后台 worker 代替。

## 领域运行持久化

- 新增通用 `SqliteDomainRunStore`。
- 仿真运行和优化运行按独立 namespace 保存完整聚合 JSON。
- API 和 worker 可从同一个 SQLite 文件读取运行。
- 一个进程修改运行后，另一个进程刷新即可看到最新状态。
- Docker API 与 worker 共用 `/app/data/domain-runs.db`。

## 队列治理

- 命令优先级范围 `-10..10`，领取时高优先级优先。
- 默认每个实验最多一个有效租约任务，避免同一实验同时修改多个状态图。
- 不同实验可以由不同 worker 并行执行。
- 排队任务可立即取消。
- 已领取任务记录取消请求，由持有租约的 worker 确认取消。
- 死信可重放为新的命令，保留 `parentTaskId` 追溯链。
- 重放任务重新从零计算尝试次数，不能篡改原死信。
- target/action 不匹配在 API 校验阶段拒绝。

## API

- `POST /experiments/{experimentId}/agent-commands`
- `POST /agent-runtime/commands/{taskId}/cancel`
- `POST /agent-runtime/commands/{taskId}/replay`

## 前端

- 仿真创建、推进、停止和重试改走统一后台队列。
- 优化创建、提交和重训推进改走统一后台队列。
- 数据分析任务卡新增优先级、取消任务和死信重放操作。
- 后台任务失败、取消或超时会显示明确错误，不伪装成完成。

## 验证记录

- 队列治理、领域 worker 与领域持久化专项测试：`15 passed`
- 后端全量测试：`143 passed`
- 前端 TypeScript：通过
- 前端生产构建：通过
- worker 启动检查：通过
- Docker Compose 配置：通过
- `git diff --check`：通过

## 当前边界

- SQLite 适用于单机或单共享卷部署，不是多地域消息系统。
- 产品创新的本地 LLM 调用尚未进入队列。
- 取消是协作式取消；已经完成的原子领域变更不会反向回滚。
- 还没有 Redis、Dramatiq 或 Celery 适配器，也没有全局资源配额。
- 所有输出仍为研发实验建议，不连接真实设备。

## 下一步

Step038 将增加可插拔分布式队列协议与 Dramatiq/Redis 适配器，同时保留 SQLite 本地模式；并建立 GPU/CPU/LLM 资源池、实验优先级策略和 worker 能力标签，为多企业并发训练与仿真调度打基础。
