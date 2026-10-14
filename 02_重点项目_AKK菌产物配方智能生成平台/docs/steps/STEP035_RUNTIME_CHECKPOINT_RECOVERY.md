# Step035 可恢复运行时与 SQLite 检查点

## 本步结果

智能体状态图不再只能保存在 Python 进程内。平台现在拥有可选的 SQLite 持久化运行时，并且 LangGraph 可使用官方 `SqliteSaver` 跨适配器实例恢复和继续执行。

## 采用的现成架构

- `langgraph==1.2.9`
- `langgraph-checkpoint-sqlite==3.1.0`
- 官方 `SqliteSaver`
- LangGraph `thread_id`、checkpoint 和 interrupt-after 语义

平台同时保留中立快照表，用来保存 LangGraph 私有检查点之外的审计事件、revision、图定义和命令幂等记录。

## 已实现

- 新增 `SqliteRuntimeCheckpointStore`。
- 新增 `PersistentRuntimeAdapter`。
- 保存完整 `RuntimeSnapshot`、`RuntimeGraphDefinition` 和已处理命令 ID。
- SQLite 使用 WAL、完整同步和单事务 UPSERT。
- 跨实例恢复后继续保留 CAS revision、事件、人工检查点和命令幂等。
- 写入失败时，确定性运行时会回滚内存变更，不返回伪成功。
- 损坏 JSON、重复运行或 LangGraph/平台快照错位不会被静默忽略。
- LangGraph 持久化模式使用官方 `SqliteSaver`，内存模式继续使用 `InMemorySaver`。
- 运行时工厂支持：
  - `deterministic`
  - `deterministic-sqlite`
  - `langgraph`
  - `langgraph-sqlite`
- `/agent-runtime/status` 新增检查点后端、持久化状态和可恢复运行数量。
- 数据分析执行中心新增“运行检查点”展示。
- Docker Compose 为 API 挂载 `./data/runtime:/app/data`。
- 设置 `LANGGRAPH_STRICT_MSGPACK=true`，遵循官方 SQLite checkpointer 安全建议。

## 配置

```env
AGENT_RUNTIME_BACKEND=langgraph
AGENT_RUNTIME_CHECKPOINT_PATH=/app/data/agent-runtime.db
LANGGRAPH_STRICT_MSGPACK=true
```

不配置路径时，状态接口会明确显示“仅进程内存”，不再将其描述成可跨重启恢复。

## 验证记录

- SQLite 运行时专项测试：`4 passed`
- LangGraph/工厂/持久化组合测试：`14 passed`
- 后端全量测试：`128 passed`
- 前端 TypeScript：通过
- 前端生产构建：通过
- Docker Compose 配置解析：通过

## 当前边界

- 运行时状态图已经可恢复，但产品需求版本、上传文件索引和其他领域仓库仍有部分内存实现。
- SQLite 适合当前单机演示；多副本服务需迁移到官方 PostgresSaver 与外部任务队列。
- 后台 worker、任务租约、心跳和超时接管尚未实现。
- 所有输出仍为研发实验建议，不连接真实产线。

## 下一步

Step036 将实现后台任务队列适配层、任务租约与心跳：HTTP 请求只负责创建命令，worker 获取租约后执行节点，并通过幂等命令和检查点实现安全重试。
