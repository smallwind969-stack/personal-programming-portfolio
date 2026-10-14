# Step036 智能体命令队列与独立 Worker

## 本步结果

数据分析智能体的“推进”和“终止”操作已经从浏览器请求中的同步执行，升级为：

`前端提交命令 → API 持久化入队 → worker 获取租约 → 心跳续租 → LangGraph 执行 → 提交新 revision`

## 已实现

- SQLite 智能体命令队列。
- 命令 ID + SHA-256 请求指纹幂等。
- `queued / leased / completed / deadLetter` 状态转换。
- `BEGIN IMMEDIATE` 原子领取，避免两个 worker 同时获得同一任务。
- 每次领取生成独立 `leaseToken` fencing token。
- worker 名称、令牌、有效期三重租约校验。
- 后台心跳线程在长任务执行期间自动续租。
- 租约过期后允许其他 worker 接管。
- 旧 worker 的完成请求会被拒绝，不能覆盖新 worker。
- 可重试异常按次数重新排队，revision 冲突等确定性错误直接进入死信。
- 队列和 LangGraph 同时使用命令幂等与 revision CAS，形成双重保护。
- worker 可从 SQLite 恢复 API 进程创建的业务运行映射。
- API 进程可重新读取 worker 提交的新 runtime revision。
- 新增独立 worker 模块：`python -m app.worker`。
- Docker Compose 新增 `agent-worker` 服务，与 API 共用运行时和队列持久化目录。

## API

- `POST /experiments/{experimentId}/agent-runs/{runId}/commands`
- `GET /agent-runtime/commands/{taskId}`
- `GET /agent-runtime/queue/status`

## 前端

- “推进一环节演示”改为“提交下一环节任务”。
- “终止当前运行”改为“提交终止任务”。
- 页面轮询命令状态，在 worker 完成后重新读取最新运行。
- 展示任务编号、队列状态、执行次数、租约 worker 和租约到期时间。
- 顶部展示队列后端和待执行数量。

## 验证记录

- 队列与 worker 专项测试：`9 passed`
- 独立 Orchestrator/worker 恢复与 revision 可见性测试：通过
- 运行时相关组合测试：`20 passed`
- 后端全量测试：`137 passed`
- 前端 TypeScript：通过
- 前端生产构建：通过
- worker `--once` 启动检查：通过
- Docker Compose 配置解析：通过

## 当前边界

- SQLite 队列适用于当前单机演示；多主机部署需要 Redis/Postgres/云消息队列适配器。
- 人工验收仍为同步命令，因为它需要用户即时确认；普通推进和终止已经走后台队列。
- 产品创新、仿真和工艺优化尚未全部迁移到统一命令队列。
- 没有真实设备控制，所有输出仍为研发实验建议。

## 下一步

Step037 将把仿真模拟与工艺优化也迁入统一任务队列，并增加任务优先级、实验级并发上限、取消命令和死信重放；随后再提供 Redis/Dramatiq 或 Celery 适配器，用于多机部署。
