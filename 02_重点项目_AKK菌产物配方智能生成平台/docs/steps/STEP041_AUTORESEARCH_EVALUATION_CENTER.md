# Step041：智能体评测与训练实验中心

## 已完成

- 参考 autoresearch 建立固定基线、固定预算、单变量候选和 keep/discard/crash 实验循环。
- 新增独立 `researchExperiment` 研究实验智能体，平台目录扩展到 13 个智能体。
- 建立 SQLite campaign 账本，支持跨服务实例恢复、创建幂等、候选幂等和不可变产物指纹。
- 锁定数据快照、评测器、主指标、方向与预算；候选修改受保护字段会被拒绝。
- 新增可替换 `ResearchEvaluationRunner` 协议，并验证真实 Runner 可在不修改上层逻辑时接入。
- 当前确定性展示 Runner 明确标注为 `mock_evaluation`，不冒充真实训练。
- 研究实验智能体可自动提出下一项单参数候选，用户也可人工指定候选。
- 候选试验进入统一后台命令队列，由 Worker 执行并继承租约、重试、死信与资源调度。
- 晋升必须满足最佳候选、最低改进、R²、MAE 四类门禁，并由人工签署。
- 新增 campaign 创建、查询、候选、自动迭代和晋升 API。
- 数据分析页面新增训练实验中心，展示试验表、指标变化、后台状态与模型晋升记录。

## 当前边界

- 当前 Runner 是规则化 mock，用于展示完整流程；没有声称已经训练真实模型。
- 真实 sklearn/PyTorch Runner、隔离训练容器和 GPU 产物仓库将在下一阶段接入。
- 所有晋升模型仍属于“研发实验建议”，不能直接控制产线。

## 验证记录

- 后端全量：`166 passed, 1 skipped`；唯一跳过项仍为未配置 `TEST_POSTGRES_URL` 的真实 PostgreSQL 集成测试。
- campaign、Runner、自动候选、API 和 Worker 专项：全部通过。
- 目录运行状态：LangGraph `1.2.9`、13 个智能体、2 条工作流。
- 当前 Runner 状态：`mock_evaluation`，页面与 API 均如实披露。
- 独立 Worker：运行通过。
- 前端 `npm run typecheck`：通过。
- 前端 `npm run build`：通过，共生成 11 个静态页面。
- Docker Compose `distributed` profile：配置校验通过。
- `git diff --check`：通过，仅有既有 LF/CRLF 提示。
