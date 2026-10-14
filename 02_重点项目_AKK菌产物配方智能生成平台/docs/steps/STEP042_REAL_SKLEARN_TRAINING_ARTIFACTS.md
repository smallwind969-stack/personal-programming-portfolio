# STEP042 完成记录：真实 sklearn 训练与内容寻址产物

日期：2026-07-20

## 已实现

1. 新增 `SklearnResearchRunner`，使用梯度提升回归执行真实 fit/predict。
2. 实验快照可导出不可变指纹约束的数值训练数据。
3. 基线创建时在真实模式下执行真实训练，不再沿用前端传入的演示指标。
4. 每次候选保存真实 MAE、RMSE、R²、特征、目标、模型类型和数据指纹。
5. 新增 SHA-256 内容寻址模型仓库与篡改检测。
6. API、普通 Worker、分布式 Worker 共享 Runner 开关和模型产物目录。
7. 保留显式 mock 回退，并记录回退原因。

## 验证

- 后端：`170 passed, 1 skipped`。
- sklearn 真实训练测试生成 `.joblib` 与 `.json` 产物并验证篡改拒绝。
- `RESEARCH_RUNNER=sklearn` 加载结果：`real_runner sklearn-gradient-boosting-v1 None`。
- 前端：TypeScript 检查及 Next.js 生产构建通过。
- Worker CLI 导入通过。
- Docker Compose 配置校验通过；仅出现本机 Docker 用户配置读取警告。

## 边界

目前真实训练面向小规模表格数值数据；尚未将已晋升模型用于仿真实时推理。joblib 产物只能在可信内部环境使用，不接受外部不可信文件加载。

## 下一步

Step043 建立晋升模型注册表与可信推理服务，让仿真智能体读取指定模型版本完成预测，同时保留模型版本、输入范围和置信区间追溯。

