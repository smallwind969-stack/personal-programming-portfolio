# 肺结节 MCP 工具（本机演示版）

提供三个工具：`detect_lung_nodules(case_id)`、`classify_nodules(case_id, run_id, candidate_ids)` 和 `analyze_case_candidates(case_id)`。第三个工具按真实检测返回的同批候选编号顺序调用分类；遇到检测或分类错误立即停止，输出固定错误说明，不让语言模型解释原始异常。它不执行医生复核。调用者只传病例 ID 和当前检测批次的候选 ID，DICOM 路径、模型阈值和原始候选字典不进入对话工具参数。模型评分是待医生复核的输出，尚未校准为临床恶性概率。

所有工具统一返回字典：`ok=true` 才有实际模型结果；`ok=false` 时不给 `findings`、`run_id` 或评分。常见错误码为 `CASE_OUT_OF_SCOPE`、`CASE_NOT_REGISTERED`、`RUN_EXPIRED`、`INVALID_CANDIDATE_IDS`、`MODEL_SERVICE_UNAVAILABLE`。组合工具还会拒绝候选 ID、批次、病例 ID 或评分不一致的结果，返回 `INVALID_TOOL_RESULT`。智能体应先判断 `ok`；失败即停止该病例的检测/分类链，不可将缺少候选字段解释为“未检出结节”。工具层仍在调用模型服务前拒绝范围外病例，并在签名审计中记录 `denied`。结构化失败减少解析错误，但不能单独保证语言模型最终回答真实。

MCP Python SDK 1.30 要求 Python 3.10 或更高。本机的模型服务可以继续使用已有的 Python/PyTorch 环境；MCP 建议单独建 Python 3.10 虚拟环境。先按 [模型服务说明](../model-server/README.md)准备脱敏演示病例和服务令牌，再在**启动 MCP 的同一个进程环境**配置：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MODEL_SERVER_URL = 'http://127.0.0.1:8100'
$env:MODEL_SERVER_TOKEN = '<与模型服务相同的令牌>'
$env:MCP_ALLOWED_CASE_IDS = '<本次授权的脱敏病例ID，多个用逗号分隔>'
.\.venv\Scripts\python.exe server.py
```

默认 `stdio` 传输；Docker 中的 Nexent 可使用带鉴权的 Streamable HTTP：

```powershell
$env:MCP_SERVER_HOST = '0.0.0.0'
$env:MCP_SERVER_PORT = '8200'
$env:MCP_SERVER_TOKEN = '<另行生成的随机长令牌>'
$env:MCP_AUDIT_LOG = 'D:\demo-config\mcp-tool-events.jsonl'
$env:MCP_AUDIT_KEY = '<另行生成的随机长审计密钥>'
.\.venv\Scripts\python.exe server.py --http
```

在 Nexent“添加 MCP 服务”中使用 `http://host.docker.internal:8200/mcp`，在自定义 HTTP Headers 中设置 `Authorization: Bearer <MCP_SERVER_TOKEN>`。实际联调发现该版本单独的 Bearer Token 输入栏未传递给工具发现请求，因此使用自定义 Header。HTTP 层无令牌时返回 401。`0.0.0.0` 仅供本机容器访问演示，正式部署应通过防火墙/反向代理限定来源。模型服务使用独立的 `MODEL_SERVER_TOKEN`。不要把令牌、原始病人资料或本机绝对路径写进提示词、知识库、截图与参赛材料。

`MCP_AUDIT_LOG` 和 `MCP_AUDIT_KEY` 同时配置时，每次工具处理函数执行会追加一个签名 JSONL 事件。事件记录工具名、时间、成功/错误/拒绝、运行批次及病例 ID 的密钥摘要；不记录原始病例 ID、路径、令牌或工具返回内容。只配置其中一项时调用会在进入模型服务前失败。审计文件与密钥应放在非共享的本机配置目录，不能随 Agent 配置导出；本仓库 `.runtime/` 仅供测试且已忽略。Nexent 调试后用 `deploy/verify_mcp_trace.py --case-id demo-001 --tool detect_lung_nodules --since <测试开始 Unix 秒数> --outcome error` 验证是否确有工具事件。**有工具事件仍不等于 Agent 已正确处理结果。**

`MCP_ALLOWED_CASE_IDS` 为本次演示的进程级病例范围；不配置时检测和分类都拒绝执行，列表外 ID 在进入模型服务前被拒并可记为 `denied` 事件。它防止智能体在错误后编造另一个已登记病例 ID 继续推理。每次换演示病例要重启 MCP 并更新该范围。它只适用于本机单人演示，不能代替正式系统的医生身份、会话授权和病例级访问控制。空病例烟测时可暂设为 `demo-001`，模型服务的空病例清单仍会返回 404。

**验证状态：**2026-10-09 本机 MCP SDK 1.30.0 经鉴权 HTTP 通道发现三个工具，空病例烟测显示组合工具返回 `CASE_NOT_REGISTERED` 和“未获得影像结果”，签名日志验出真实的 `detect_lung_nodules/error` 事件。纯流程及 MCP 测试 28 项通过；这只验收空病例错误路径及模拟成功分支。Nexent 内尚未刷新第三个工具，也未通过 Agent 自然提问验收；没有进行真实脱敏 DICOM 推理或安全的端到端问答。参见 [接入清单](../deploy/configure-agent.md)。
