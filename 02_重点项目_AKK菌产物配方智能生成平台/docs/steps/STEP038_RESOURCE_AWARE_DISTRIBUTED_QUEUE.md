# Step038：资源感知的分布式智能体队列

## 本步目标

在 Step037 的统一命令队列上增加可插拔后端边界和 Worker 资源匹配，使数据分析、仿真、优化任务能够被不同 CPU、GPU、本地 LLM 节点安全领取。

## 已完成

- 新增 `AgentCommandQueue` 协议，业务服务与具体 SQLite 实现解耦。
- 任务新增 `requiredCapabilities`，当前支持 `cpu`、`gpu`、`localLlm`。
- SQLite 队列按“任务需求是 Worker 能力子集”进行领取，并继续遵守优先级和单实验并发限制。
- 新增 Worker 注册表，记录能力、并发容量、主机标签、心跳和在线/离线状态。
- 新增队列工厂：默认 SQLite；请求 Dramatiq/Redis 但配置或依赖不可用时安全回退，并暴露原因。
- 新增 Dramatiq 2.2.0 Redis 唤醒适配器。消息只携带 `taskId`，实验参数仍保留在可审计命令账本。
- Docker Compose 增加可选 `distributed` Redis profile，默认演示部署不强制启动 Redis。
- 新增可被 Dramatiq CLI 发现的顶层 Actor 和 `distributed-agent-worker` 服务，避免分布式模式只有生产者没有消费者。
- 运行中心显示有效队列后端、待执行数和在线执行节点数。

## 边界说明

- SQLite 仍是单机演示和当前服务器部署的权威任务账本。
- Dramatiq/Redis 当前负责跨进程/跨节点唤醒，不替代命令审计、取消、租约、重放和死信状态。
- 真正多服务器生产部署仍需在后续把权威账本迁移到 PostgreSQL；本步不宣称 SQLite 共享文件具备多主机一致性。
- 所有输出仍属于“研发实验建议”，不会直接下发真实产线控制命令。

## 配置

```env
AGENT_QUEUE_BACKEND=sqlite
AGENT_REDIS_URL=redis://redis:6379/0
AGENT_WORKER_CAPABILITIES=cpu,localLlm
AGENT_WORKER_MAX_CONCURRENT=1
```

切换 Redis 唤醒层时使用 `AGENT_QUEUE_BACKEND=dramatiq-redis`，并启动 Compose 的 `distributed` profile。

## 验证记录（2026-07-20）

- 后端全量：`149 passed`。
- 资源匹配、Worker 注册、兼容领取、队列工厂、消息隔离与原有队列/Worker 定向测试：`19 passed`。
- Dramatiq 顶层 Actor 导入：`wake_agent_worker / agent-commands`。
- 前端 `npm run typecheck`：通过。
- 前端 `npm run build`：通过，共 11 个静态页面生成完成。
- 独立 Worker `python -m app.worker --once`：通过。
- Docker Compose 默认及 `distributed` profile 配置校验：通过（仅本机 Docker 配置文件访问警告）。
