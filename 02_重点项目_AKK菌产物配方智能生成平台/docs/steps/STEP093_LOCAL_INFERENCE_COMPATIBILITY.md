# STEP093：本地推理兼容性与回退链路

## 目标

确保企业已有的本地模型或 OpenAI-compatible API 可以接入字段识别等流程，同时不让模型承担确定性数据处理、模型准入或设备控制职责。

## 完成内容

- 字段识别 provider 增加 OpenAI-compatible JSON 响应回归覆盖：验证 `/v1/chat/completions` 路径、Bearer 认证和结构化候选解析。
- 保留 Ollama `/api/chat` 路径，二者统一经过 Pydantic 结构校验。
- 上游超时、HTTP 错误、非法 JSON、越权字段都会进入确定性规则回退，并保留失败类别。
- 能力状态接口只暴露脱敏后的 endpoint、模型名、可用性、延迟和回退模式，不返回 API 密钥。
- `stop-local.ps1` 的结束提示改为 ASCII，避免 Windows PowerShell 按系统代码页解析脚本时出现语法错误。

## 验证

- 新增 OpenAI-compatible provider 测试通过。
- 全量后端：`341 passed, 1 skipped`。
- 示例流程检查仍通过：数据分析 100%、仿真完成、优化完成。

## 接入方式

在服务端环境变量中配置：

```env
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=openai_compatible
LOCAL_LLM_BASE_URL=http://127.0.0.1:1234/v1
LOCAL_LLM_API_KEY=服务端密钥
LOCAL_LLM_MODEL=模型名称
SCHEMA_RECOGNITION_LLM_ENABLED=true
```

密钥只在 API 服务端读取，浏览器和实验数据资产中不保存密钥。
