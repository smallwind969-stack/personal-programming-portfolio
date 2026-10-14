# Step 081：启动与运行时一致性

## 目标

让本地演示、局域网演示和持久化数据使用同一套约定：前端 3000 端口，API 8000 端口，模型资产读取 API 运行目录中的 `promoted-models.db`，避免“服务已启动但打开了另一套空数据”的情况。

## 交付内容

- `scripts/start-local.ps1` 统一设置队列、实验运行、研究任务、模型注册表和模型产物路径。
- `scripts/start-lan.ps1` 同样设置模型注册表和产物路径，局域网访问仍使用 3000/8000。
- `scripts/check-local.ps1` 增加启动后健康检查：API 健康状态、模型资产数量、工作台页面状态码。
- 启动脚本输出固定的打开地址、健康检查地址、验证命令和停止命令。

## 验证

- PowerShell 解析检查：`start-local.ps1`、`start-lan.ps1`、`check-local.ps1` 均无语法错误。
- 启动后执行 `powershell -ExecutionPolicy Bypass -File .\scripts\check-local.ps1`，应同时得到 API 健康、模型资产数量和工作台状态码。
- 运行时模型资产必须来自 `apps/api/data/runtime/promoted-models.db`，与模型资产页和模型详情页使用同一数据源。

## 用户体验闭环

启动不再只是打开一个网页，而是明确告诉使用者：工作台入口在哪里、服务是否健康、当前可用的模型资产数量是多少，以及如何停止服务。这样数据分析、仿真模拟和工艺优化看到的是同一个可追溯运行环境。
