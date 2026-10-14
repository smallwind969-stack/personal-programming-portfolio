# STEP124：可靠的本地启动流程

## 问题与原因

本地运行脚本启动的是 Next.js 生产服务。此前脚本只启动服务、不构建前端，因此源代码更新后可能继续展示上一轮 `.next` 构建产物。

## 交付内容

- `scripts/start-local.ps1` 默认执行前端生产构建，再停止旧进程并启动 API、后台任务与 Web 服务；
- 若研发调试确实需要跳过构建，可显式使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -SkipWebBuild
```

- 构建失败时脚本会停止，不会关闭当前已运行的服务后再留下不可用终端；
- 构建成功后才切换到新的 API/Web 进程。

## 验证记录

- 使用默认启动命令完成一次完整构建和重启；
- API 健康检查返回 `200`；
- 实验详情页返回 `200`；
- `scripts/check-local.ps1` 通过。
