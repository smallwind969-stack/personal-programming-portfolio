# Step058：真实反馈重训练智能体

## 本步目标

将 Step057 已确认的真实实验反馈接入机器学习闭环：形成不可变派生数据集，在独立反馈留出批次上比较现役模型和候选模型，通过技术硬门禁与人工批准后注册新模型，并立即进入独立可靠性复核。

## 已实现

1. 新增 `FeedbackDerivedDatasetBuilder`：
   - 合并父模型历史训练数据和确认反馈数据；
   - 根据父模型特征契约映射温度、pH、搅拌速度等标准工艺字段；
   - 锁定父数据快照、父数据指纹、反馈数据版本和派生数据指纹；
   - 最后 3 个独立反馈批次固定为外部时间后留出集；
   - 同一批次的技术重复样不会被冒充为独立批次。
2. 扩展真实 sklearn 运行器，支持显式 `confirmed_feedback_batches` 留出集，现役模型与全部候选使用完全相同的评测行。
3. 新增 `FeedbackRetrainingAgent` 五阶段工作流：
   - 反馈数据装配；
   - 现役模型外部评估；
   - Ridge、RandomForest、GradientBoosting 候选训练；
   - 新旧模型比较与硬门禁；
   - 人工晋升复核。
4. 硬门禁包括独立批次数、最佳试验、R²、MAE、RMSE、相对现役模型改进和模型产物完整性；任何失败均不能人工绕过。
5. 批准动作复用现有 ResearchCampaign 晋升和内容寻址模型注册表；父模型、父数据集和父模型产物始终只读。
6. 新模型注册后自动创建独立模型可靠性报告。未经该报告人工确认，实验工作区和仿真准入不切换到新模型。
7. 新增实验级 API：
   - `GET/POST /experiments/{id}/feedback-retraining-runs`
   - `GET /experiments/{id}/feedback-retraining-runs/{runId}`
   - `POST /experiments/{id}/feedback-retraining-runs/{runId}/advance`
   - `POST /experiments/{id}/feedback-retraining-runs/{runId}/review`
8. 工艺优化页面新增“真实反馈重训练活动”中文工作台，展示阶段进程、数据指纹、新旧指标、逐项门禁和人工晋升入口。

## 真实运行验收

### 信息量不足的运行

- 运行：`feedback-retraining-fc4296c18463`
- 仅 3 个参数近似相同的独立批次。
- 随机森林虽略优于现役模型，但外部留出 R² 为负。
- 系统正确阻止晋升，失败证据保留在活动账本。

### 通过重训练技术门禁的运行

- 运行：`feedback-retraining-331f9c1efd74`
- 派生数据集：`feedback-derived-dataset-e25a906f5d44`
- 父模型：`model-modeling-v1`
- 进入训练的新增独立反馈：12 批。
- 固定外部留出：3 批。
- 现役模型：R² `-1.4143124679`，MAE `0.3457649769`，RMSE `0.4574280423`。
- Ridge：R² `0.562641`，MAE `0.191715`，RMSE `0.194691`。
- RandomForest：R² `0.808204`，MAE `0.108688`，RMSE `0.128928`。
- GradientBoosting：R² `0.797595`，MAE `0.127885`，RMSE `0.132445`。
- 九项技术硬门禁全部通过。
- 人工批准后注册：`model-modeling-v2`。
- 独立可靠性报告：`model-eval-51e28c1604ba`。

## 双门禁结果

新模型虽然通过重训练技术门禁，但独立可靠性评分为 `0.636381`，低于仿真准入线 `0.700`，报告状态保持 `needsReview`、`admissionAllowed=false`。实验工作区继续使用 `model-modeling-v1`，证明系统不会因一次重训练活动而静默替换仿真模型。

## 验证

- 后端完整测试：`248 passed, 1 skipped`。
- 前端 TypeScript 检查通过。
- 前端生产构建通过。
- 页面服务端渲染：HTTP 200，并包含重训练工作台、新模型版本和可靠性报告编号。
- 页面地址：`http://127.0.0.1:3001/experiments/exp-06c5e0b50fd0/optimization`。

## 下一步

Step059 应实现“可靠性不足后的定向补实验建议”：根据漂移、覆盖率、残差和特征边界，自动生成下一轮最有信息量的实验参数组合，但仍由研发人员批准后执行。
