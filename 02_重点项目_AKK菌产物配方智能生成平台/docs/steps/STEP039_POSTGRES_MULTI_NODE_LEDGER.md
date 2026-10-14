# Step039：PostgreSQL 多节点智能体权威账本

## 已完成

- 实现 `PostgresAgentCommandQueue`，覆盖入队、幂等、领取、心跳、完成、失败重试、取消、死信重放和 Worker 注册协议。
- 提供幂等数据库迁移，使用 JSONB 保存任务载荷、能力需求和节点标签。
- 使用 `FOR UPDATE SKIP LOCKED` 实现多 Worker 非阻塞领取。
- 使用租约 token 和过期时间实现 fencing，拒绝旧 Worker 写回。
- 数据库层强制执行单实验并发上限、Worker `maxConcurrent` 上限和 CPU/GPU/本地 LLM 能力匹配。
- 将命令账本后端和消息派发后端拆分：`AGENT_QUEUE_BACKEND` 选择 SQLite/PostgreSQL，`AGENT_DISPATCH_BACKEND` 选择轮询/Dramatiq Redis。
- 状态接口和前端增加后端组合、节点占用任务数和可用槽位。
- Docker `distributed` profile 增加 PostgreSQL 17、健康检查、持久化卷和分布式 Worker 依赖。
- 锁定 `psycopg[binary,pool]==3.3.4`。

## 配置示例

```env
AGENT_QUEUE_BACKEND=postgres
DATABASE_URL=postgresql://akk:secret@postgres:5432/akk_platform
AGENT_QUEUE_NAMESPACE=production
AGENT_DISPATCH_BACKEND=dramatiq-redis
AGENT_REDIS_URL=redis://redis:6379/0
```

## 验证边界

本机 Docker Engine 当前未运行，因此真实 PostgreSQL 集成测试由 `TEST_POSTGRES_URL` 控制并明确标记为 skipped；契约测试、SQL 不变量检查、驱动真实导入、SQLite 回归、前后端构建和 Compose 配置仍执行。不得把 skipped 项描述为真实数据库已通过。

## 验证记录（2026-07-20）

- 后端全量：`153 passed, 1 skipped`；唯一跳过项为需要 `TEST_POSTGRES_URL` 的真实 PostgreSQL 集成测试。
- PostgreSQL/队列专项：`22 passed, 1 skipped`。
- Psycopg 3.3.4、连接池模块和 PostgreSQL 队列：真实导入通过。
- Dramatiq 顶层 Actor：真实导入通过。
- 前端 `npm run typecheck`：通过。
- 前端 `npm run build`：通过，共生成 11 个静态页面。
- 独立 Worker `python -m app.worker --once`：通过。
- Docker Compose `distributed` profile：配置校验通过；本机 Docker Engine 未运行，未启动 PostgreSQL 容器。
- `git diff --check`：通过，仅有既有 LF/CRLF 提示。

## 研发安全边界

本步骤只扩展智能体计算调度，不接入真实设备控制。仿真与优化输出仍为“研发实验建议”，需要人工确认和现实实验验证。
