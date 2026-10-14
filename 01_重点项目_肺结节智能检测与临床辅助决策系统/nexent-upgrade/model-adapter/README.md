# 本机 Ollama 原生接口适配层（实验）

Nexent v2.7.0 的自定义大语言模型使用 OpenAI 兼容接口，而本机 Ollama 0.11.7 在该接口下把 Qwen3 的 `<think>` 标记写进正文。此适配层对外提供最小 `/v1/chat/completions` 和 `/v1/models`，对内调用 Ollama 原生 `/api/chat`，强制 `think=false`。它不改写 `<code>`、不执行工具、不制造观测结果；若原生输出仍含 `<think>`，返回 502。

在本机 Python 3.10 环境中安装 `requirements.txt` 后运行：

```powershell
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:ADAPTER_MODEL_ID = 'qwen3:8b'
python app.py
```

默认只监听宿主机 `127.0.0.1:11435`。本机 Docker Desktop 中的 Nexent 已验证可访问 `http://host.docker.internal:11435/v1/models`；可把 `http://host.docker.internal:11435/v1` 用于新建的**测试模型**。适配层不鉴权，所以不可改为公网或局域网监听，不能作为正式部署服务。它把 Ollama 的完整回复收齐后再转换成 OpenAI SSE 格式，不提供逐 token 流式体验。

2026-10-08 无病例探针：非流式与流式请求均返回干净的 `<code>print(detect_lung_nodules(case_id="demo-001"))</code>` 动作；单元测试 5 项通过。**这只证明格式和连通性**，不证明模型会在自然提问下选择工具。

接入 Nexent 的实际对照：自然语言检测请求没有产生 `CallToolRequest`，模型直接说“检测任务已启动”，平台最终自检却显示通过。随后明确给出固定 `<code>` 动作的探针产生一次真实检测调用，空病例清单返回 `CASE_NOT_REGISTERED`，签名审计验真通过；但 Agent 最终答复却是英文的 `malformed_action` 协议错误提示，既没报告病例未登记，也没说明“未获得影像结果”。独立失败降级门禁判定未通过。详见 `../deploy/integration-log-2026-10-07.md`。因此此适配层当前仍只用于实验；不得把模型连通、工具可发现、单次工具调用或平台自检通过描述成完整病例处理能力。
