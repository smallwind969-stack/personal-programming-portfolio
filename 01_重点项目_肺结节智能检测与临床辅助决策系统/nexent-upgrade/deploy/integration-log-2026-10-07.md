# 2026-10-07 本机 Nexent 联调记录

## 范围

本次仅验证单人比赛演示环境的服务发现、模型连通和安全降级。模型服务使用**空病例清单**，没有导入患者影像或知识库，也没有进行真实 DICOM 推理。

## 已验证

| 检查项 | 实际结果 | 证据边界 |
|---|---|---|
| Docker Nexent → Windows MCP | `http://host.docker.internal:8200/mcp`，自定义 `Authorization` 请求头；平台显示“连接成功”“2 个工具” | 只证明注册、鉴权与工具发现 |
| MCP SDK HTTP 握手 | 发现 `detect_lung_nodules(case_id)`、`classify_nodules(case_id, run_id, candidate_ids)` | 已核对参数 schema |
| 未登记病例 | 空病例清单下调用 `detect_lung_nodules("demo-001")`，`isError=True`、HTTP 404 | 未产生影像结果；错误未含本机影像路径 |
| 本机大语言模型 | Ollama `qwen3:8b` 经 `host.docker.internal:11434/v1` 在 Nexent 检测为“可用” | 只证明模型 API 连通 |
| Agent 草稿 | “肺结节辅助复核（演示待验证）”已配置本地模型、角色/使用要求和两个 MCP 工具 | 草稿未发布 |

## 调试失败与处理

首次向 Agent 输入 `demo-001` 的检测请求时，Nexent 调试轨迹未出现有效的工具调用，而是提示需要可执行的工具调用格式，并进入后续无效推理。人工停止。该结果不能用于声称 Agent 已能完成检测或安全降级；下一轮应以固定、无医学数据的工具调用用例定位模型与 Nexent 执行协议的兼容性，再评估模型、参数或 Agent 模式。

随后按相同空病例用例做对照：

| 模型与配置 | 调试观察 | 判定 |
|---|---|---|
| Qwen3 8B，OpenAI 兼容接口 | Ollama 的当前版本在请求 `think=false` 时仍把 `<think>` 内容写入正文；Nexent 未获得可执行动作 | 连通，但未通过工具调用验收 |
| Qwen2.5 7B，默认运行策略 | 输出自定义的假 `detect_lung_nodules`、假“运行结果”和报告路径；没有实际 MCP 调用 | 不安全，不能发布 |
| Qwen2.5 7B，明确禁止模拟，开启严格输出协议、自验证，最多 5 步 | 仍尝试脚本/子进程方式；自验证阻断无证据答复，提示无法给出已验证答案 | 阻断生效，工具调用仍失败 |
| Qwen2.5 Coder 7B，同样的严格策略 | 重定义工具并调用 `run_skill_script`；自验证指出任务未完成，要求真实调用 `detect_lung_nodules` | 阻断生效，工具调用仍失败 |

本机日志仅出现 MCP `ListToolsRequest`，空病例模型服务没有收到 Agent 发起的 `/detect`。因此“模型连接可用”“工具在 Agent 中可见”均不能替代真实工具调用证据。Nexent 官方文档说明其 Agent 使用 CodeAgent，动作必须以 `<code>...</code>` 中的 Python 执行；本机三个模型在当前配置下未满足这一要求。参考：[Nexent Start Chat](https://modelengine-group.github.io/nexent/en/user-guide/start-chat.html)、[Ollama OpenAI 兼容接口](https://docs.ollama.com/api/openai-compatibility)。

## 测试与状态

- 模型服务契约测试：15 通过、1 跳过（Windows 符号链接权限）；MCP 测试：9 通过、1 跳过；旧系统相关测试：7 通过。
- `lung-nodule-demo` 联调时已启用，结束后已停用；临时 HTTP MCP 与模型服务已停止。Nexent 中的 Agent 草稿和模型配置保留。
- 可复验脚本：`deploy/smoke_test.py`，要求空病例清单与环境变量中的临时令牌；它只验 MCP 握手、受控 schema 和未知病例 404，不把模型对话当作成功。
- 使用的是临时测试令牌；下一次启动服务前应生成随机长令牌，并更新 Nexent 的自定义请求头。不要把令牌写进导出配置、截图或参赛文件。
- 本机 Nexent 页面曾提示“智能体导出成功”，但本轮未取得可核验的 JSON/ZIP 文件；参赛附件仍需后续导出、检查脱敏并归档。

## 下一轮验收门槛

1. Agent 对未登记病例确实调用 `detect_lung_nodules`，工具返回错误后明确说明没有影像结果。
2. 授权、脱敏 DICOM 病例完成检测与分类，并记录 `case_id`、`run_id`、`candidate_id`、模型版本和工具轨迹。
3. 医生未确认时只显示待复核；医生确认后才进入最终结节列表。
4. 经专家审核的知识条目带来源、版本和适用范围后再入库；取得可提交的 Agent 导出与脱敏界面截图。

## 10 月 7 日后续：运行证据只读核验

模型服务新增带令牌的 `GET /runs/{case_id}/{run_id}`，只读取当前服务进程保存的有效批次。分类评分只在 `/identify` 真正执行后进入该缓存；再次检测使旧批次失效。医生工作台新增“从模型服务核验”，后端向该接口取回候选编号及评分后只读显示，未接收 Agent 自述的结节列表。工作台随访接口改为读取已保存的服务端复核记录，不再直接使用浏览器提交的复核 JSON。该阶段契约测试使用模拟推理引擎；真实影像和坐标映射未验收，Agent 工具调用的后续对照见下文。

## 继续联调：真实调用与结果处理分开验收

复启空病例模型服务与 MCP 后，SDK 独立握手、工具发现、未知病例 404 再次通过。Qwen2.5 Coder 7B 在 Nexent 调试中仍输出不存在的 `runtime_metadata` 和 `run_skill_script`，没有真实 `CallToolRequest`；自验证阻断其最终完成声明。Ollama 原生 `/api/chat` 的 Qwen3 8B 在 `think=false` 和极简提示下能给出正确 `<code>` 动作，而现用 OpenAI 兼容接口会把 `<think>` 标签放进正文；加入 `/no_think` 后为空思考标签加代码。

Qwen3 8B 第一次 Nexent `/no_think` 调试自行定义了假的 `detect_lung_nodules`，输出虚构的 `no_image_data`，**平台自验证误判为通过**。此轨迹没有 MCP 调用。随后使用仅含实际调用动作的固定用例，Nexent 显示 `1 tool call`，MCP 服务处理了 `detect_lung_nodules("demo-001")`，模型服务返回预期 404；签名审计中该病例的有效工具事件在 SDK 烟测的 1 条之外增加了 Agent 调用记录。故“Agent 能调用 MCP”已获得可核验的无病例证据，但**端到端任务仍不通过**：模型随后把工具错误字符串当成字典调用 `.get()`，又虚构 `case_123` 并向工具再次发起请求；病例白名单拒绝了该请求，人工停止。

为避免靠界面文案判断成功，MCP 处理函数现可在配置 `MCP_AUDIT_LOG` 与 `MCP_AUDIT_KEY` 后写入签名 JSONL 事件，仅存病例 ID 的密钥摘要、工具、时间、结果和批次，不存原始 ID/路径/令牌。`deploy/verify_mcp_trace.py` 可以按测试时间窗验签。下一轮验收须**同时**满足：真实工具事件存在；工具错误后的 Agent 停止并准确说明“病例未登记、没有影像结果”，不得假定“未检出结节”或继续编造病例；真实脱敏病例推理完成。当前草稿仍不得发布。

针对“把工具错误字符串当字典”的故障，MCP 工具返回已改成统一字典契约：成功含 `ok=true`，未知病例、越权病例、过期批次等失败含 `ok=false` 与错误码，失败不含候选、批次或评分。签名审计继续把这些调用记为 `error` 或 `denied`。单元测试 19 项通过；新的鉴权 HTTP MCP 烟测也通过工具发现、空病例 `CASE_NOT_REGISTERED`、范围外病例 `CASE_OUT_OF_SCOPE`，签名审计各核验到 1 条对应事件，原始病例 ID 与审计密钥未写入日志。测试结束后停止了临时服务。Nexent 对话复验尚待执行，不能把此代码变更写成已解决模型幻觉。

针对实际出现的虚构 `case_123` 请求，MCP 现在要求启动进程明确设置 `MCP_ALLOWED_CASE_IDS`。检测与分类对列表外 ID、以及未配置范围的请求，均在接触模型服务前拒绝；拒绝事件可签名记录为 `denied`。这是单人演示的静态范围约束，正式多用户系统仍需医生身份和会话级病例授权。空病例 SDK 烟测已通过：`demo-001` 到模型服务返回 404，`case_123` 在 MCP 层被拒；两条事件分别验签为 `error`、`denied`，审计文件不含原始病例 ID。测试后已停用 Nexent 演示 MCP，并停止临时 MCP/模型服务进程。

## 10 月 8 日：结构化错误的 Nexent 对话复验

本机再次启动空病例模型服务和 MCP，Nexent `lung-nodule-demo` 连通性校验显示成功并启用。演示 Agent 的“使用要求”新增：收到工具响应必须先检查 `ok`，失败时停止、不得读取候选或换病例 ID。页面刷新后可见该设置已保存。

固定用例要求 Qwen3 8B 对 `demo-001` 真实调用检测并在 `ok=false` 时降级。实际调试最终输出的是包含 `detect_lung_nodules(...)`、`result.get('ok')` 和 `final_answer(...)` 的 **Python 代码文本**，界面显示“最终自检通过”，但 MCP 服务只记录 `ListToolsRequest`，没有 `CallToolRequest`；本轮签名审计文件未生成。故这次仍未测试到新版结构化错误在 Agent 内的处理，失败边界位于模型输出至 CodeAgent 可执行动作的转换处。不能以代码文本或平台自检通过证明真实推理。测试中没有患者影像。

已增加 `deploy/verify_agent_failure.py` 作为独立空病例验收门禁：必须同时有该病例的一条签名 `error` 检测事件、没有第二次工具调用，以及最终回答明确写出 `CASE_NOT_REGISTERED` 和“未获得影像结果”，且不得作阴性/风险结论。用上述失败对话文本和空审计文件运行时返回失败；相关单元测试与 MCP 测试共 24 项通过。该脚本读取人工保存的最终回答，**不能独立证明文本确由 Nexent 生成**；答辩证据仍须包含脱敏调试轨迹、测试时间窗和服务端审计。中断后 Docker 引擎不再运行，临时模型/MCP 服务也已停止；再次调试前需检查 Nexent 中 MCP 是否仍处于启用状态。

后续恢复 Docker 后，检查到 `lung-nodule-demo` 仍处于“已启用、未连接”；已在 Nexent 页面停用并核对按钮变为“启用”。读取原容器运行日志可进一步定位：在该固定用例里，前两次模型输出因 `unsupported_or_tag_only_output` 被严格协议拒绝并触发静默修复；第三次仍输出 `<think>` 加 Markdown `python` 代码块，平台记录 `phase=commit` 并把该原文作为 `Final answer`。Nexent v2.7.0 的 [`core_agent.py` 源码](https://github.com/ModelEngine-Group/nexent/blob/v2.7.0/sdk/nexent/core/agents/core_agent.py) 中，`_accept_exhausted_raw_output` 在连续两次协议错误后允许将第三次可见输出作为最终答案候选；[`output_protocol.py`](https://github.com/ModelEngine-Group/nexent/blob/v2.7.0/sdk/nexent/core/agents/output_protocol.py) 则要求可执行动作具有完整 `<code>...</code>` 包装。日志与源码相符：这个调试答案是协议修复耗尽后的**原文回退**，不是工具执行结果。当前平台“严格输出协议与静默修复”“自验证”均为开启状态，不能把它们视为来源证明。

对同一本机 Qwen3 8B 做无病例直连探针：经 Ollama 的 OpenAI 兼容接口，普通请求把较长的 `<think>` 正文放进 `content`；加 `/no_think` 后仍带空 `<think>...</think>` 前缀，再接正确 `<code>` 动作；OpenAI 请求体额外传 `think=false` 也未消除该前缀。Nexent 当前模型配置界面没有原生 Ollama 服务商，只有自定义 OpenAI 兼容接入。下一技术切片应验证本机 Ollama 原生 `/api/chat` 到 Nexent OpenAI 接口的受控适配是否能交付干净的 CodeAgent 动作，再以签名工具事件和最终回答门禁决定能否继续；适配器不能替代医学复核，也不能把无工具调用伪装成成功。

## 10 月 8 日：原生无思考适配层的真实对话对照

新增仅监听 `127.0.0.1:11435` 的本机适配层：对外提供 OpenAI 兼容 `/v1/chat/completions`，对内使用 Ollama `/api/chat` 且设置 `think=false`，拒绝含 `<think>` 的正文。非流式与 SSE 转换的单元测试 5 项通过；Docker 中的 Nexent 能连接新建的“本机 Qwen3 8B（原生适配测试）”模型。服务端配置了空病例清单、仅允许 `demo-001` 的 MCP，以及临时签名审计；没有真实患者影像。Nexent 此自定义 OpenAI 接口需要非空 API Key 字段，测试模型填入无鉴权能力的本机占位字符串；适配层本身只绑定回环地址，不校验该字符串。

| 对照 | Nexent 观察 | 独立证据与判定 |
|---|---|---|
| 自然语言请求检测 `demo-001` | 首个动作是 `final_answer("检测任务已启动...")`，最终界面“自检通过” | MCP 只有工具发现，没有检测调用；不能宣称任务已启动或推理成功 |
| 用户明确提供唯一 `<code>detect_lung_nodules(case_id="demo-001")</code>` 动作 | 界面显示 `1 tool call`；MCP 服务记录 `CallToolRequest`，模型服务 `/detect` 返回 404 | 签名审计仅有该病例一条 `detect_lung_nodules/error`，事件 ID `9a228ebbd094483c84e8d7e210bdb23c`；证明真实调用，但没有影像结果 |
| 真实错误之后的最终回复 | 模型答 `The previous response violated the Agent output protocol (malformed_action). Please provide the correct input.`，平台最终自检误判通过 | `verify_agent_failure.py` 判定失败：没有 `CASE_NOT_REGISTERED` 和“未获得影像结果” |

这轮定位出两个独立瓶颈：自然请求未稳定触发工具；即使工具确实返回结构化错误，Agent 仍可能误述原因，平台自检不能替代签名事件与回答内容的独立验收。适配层只清除思考标记，不保证策略遵循。应将关键流程控制与错误映射收进确定性编排，在取得授权脱敏病例和医生审核前，草稿不得发布，也不能声称真实 DICOM 推理或临床有效性。

## 10 月 9 日：确定性病例候选流程

新增纯 Python `mcp-server/safe_workflow.py` 与 MCP 工具 `analyze_case_candidates(case_id)`。该工具调用已有的受控检测/分类处理函数，按检测返回的同批候选 ID 分类；`ok=false`、病例/批次/候选不一致、无效评分均停止并返回固定错误说明，不返回候选或评分。成功结果始终标记 `review_status=pending`，不代表医生复核。空候选只说明“模型未给出候选，仍需医生复核影像”，不作阴性诊断。

验证：MCP 测试 28 项通过，模型适配与失败门禁测试 9 项通过；实际本机鉴权 HTTP MCP 烟测发现 3 个工具。使用空病例清单调用组合工具，返回 `CASE_NOT_REGISTERED` 和“未获得影像结果”；签名审计验证工具调用序列为检测 `error`、范围外检测 `denied`、组合工具内部检测 `error`，审计文件未含原始病例 ID 或临时令牌。测试后停止 8100/8200 临时服务。此结果仍未覆盖 Nexent 自然问答、真实脱敏 DICOM 推理、模型准确度或医生复核界面。

随后恢复本机 Docker Nexent v2.7.0 与 Ollama，把服务刷新为“3 个工具”，Agent 草稿只绑定 `analyze_case_candidates`，并将角色和使用要求改为先调用唯一工具、错误时原样报告 `error_code`/`summary`。页面刷新后确认配置持久化；没有发布 Agent。

自然语言请求分析 `demo-001` 时，模型直接给出“当前没有可用的影像结果”并由平台自检判为通过；服务端无 `CallToolRequest`，签名审计文件尚不存在。再用明确包含完整 `<code>` 的固定动作对照，MCP 确实收到组合工具调用，但 CodeAgent 输出缺少语句分隔，连续重复调用同一病例。人工停止后，按本轮开始时间验签得到 **4 条** `detect_lung_nodules/error` 事件，均为同一允许病例；没有分类事件，也没有可验收的最终回答。独立降级门禁要求恰好一条错误事件，因此本轮失败。测试使用空病例清单，没有患者影像；临时 MCP、模型、适配层与 Ollama 服务已停止，Nexent MCP 已停用。

结论：单步工具把**一次调用内部**的检测、分类和错误映射变成确定性流程，但并不能强制本机 Qwen3 8B 在自然提问时发起调用，也不能阻止 Agent 在调用后重复尝试。可执行演示包的主流程应由本机工作台直接使用确定性病例工具结果，Nexent 作为可审计的辅助问答层；Nexent 自然对话要独立满足“一次真实调用、准确停止”的门禁后再作为正式入口。
