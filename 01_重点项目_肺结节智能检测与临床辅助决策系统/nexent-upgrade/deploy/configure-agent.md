# Nexent 接入与验收清单

状态：**本机 Nexent 已完成带令牌 HTTP MCP 注册、连通性校验与启用测试，显示 2 个工具；Qwen3 8B 的固定空病例用例取得一次有签名审计的真实工具调用及预期 404。但错误后的推理仍失败，另一次调试中自验证误判伪造工具实现为通过；尚无安全的端到端成功问答。** 此次联通使用临时演示令牌和空病例清单，不能作为临床性能证据。本机验证未使用患者影像。

## 1. 本地服务与病例清单

按 [模型服务说明](../model-server/README.md)配置 `DICOM_ROOT`、`CASE_CATALOG_JSON`、`MODEL_SERVER_TOKEN` 并启动模型服务。清单中的 `demo-001` 仅是例子，必须指向授权根目录内真实存在的脱敏 DICOM 序列目录。MCP 进程使用同一模型服务令牌，另设 `MCP_ALLOWED_CASE_IDS` 为本次演示允许的脱敏病例 ID；未设置时工具拒绝所有病例。不要将令牌、审计密钥写入仓库或比赛截图。

## 2. 模型与工具

在 Nexent 配置可用的大语言模型和嵌入模型，记录提供方、模型版本、温度、上下文长度、调用限额及费用。密钥只走本机密钥管理或环境变量，不能复制原项目源码中可能存在的硬编码值。

2026-10-07 已把本机 Ollama `qwen3:8b` 作为 OpenAI 兼容模型接到 `http://host.docker.internal:11434/v1`，Nexent 显示“可用”。模型连通不等于具备 Nexent 所需的规划/工具调用能力：演示 Agent 首次输入 `demo-001` 时，调试轨迹未发出可执行工具调用，随后进入无效推理；人工停止。下一轮须先用固定的无医学数据用例验证该模型能否生成 Nexent 期望的工具调用格式，再评估模型替换、推理参数与 Agent 模式，不得将此次轨迹作为有效影像检测结果。

进一步的固定用例中，`qwen2.5:7b` 与 `qwen2.5-coder:7b` 没有发出真实 MCP 调用，分别产生模拟结果或错误脚本调用。Qwen3 8B 用 `/no_think` 与明确的 `<code>print(detect_lung_nodules(...))</code>` 指令触发过真实调用，但错误后又假定响应是字典、编造新的病例 ID。Agent 草稿现已开启“严格输出协议与静默修复”“自验证”，最大步数限制为 5；自验证并不保证工具来源真实，曾将伪造工具实现判为通过。正式答辩前必须通过签名工具事件、错误降级和真实病例三项独立验收；不能靠提示词或自验证分数替代。详见 [联调记录](integration-log-2026-10-07.md)。

当前 MCP 服务支持 `stdio` 与带 Bearer 鉴权的 Streamable HTTP，工具签名为：

- `detect_lung_nodules(case_id)` → `run_id`、待复核候选及 `candidate_id`。
- `classify_nodules(case_id, run_id, candidate_ids)` → `model_score`、`review_status: pending`。
- `analyze_case_candidates(case_id)` → 工具端按同批候选完成检测与分类；错误时固定说明原因并停止，成功结果仍为 `review_status: pending`。

本机 Docker Nexent 通过 `http://host.docker.internal:8200/mcp` 访问 Windows 宿主上的 HTTP MCP。服务使用 `MCP_SERVER_TOKEN` 鉴权，Nexent 当前版本在“自定义 HTTP Headers”中填写 `Authorization: Bearer …` 后能够发现两个工具；单独的 Bearer Token 栏位在此次实际联调中未成功传给发现请求。HTTP 服务允许 `host.docker.internal` Host，同时保留 SDK 的 DNS 重绑定保护。2026-10-07 平台“连通性校验”显示“连接成功”，服务曾启用并在联调后停用。临时令牌不得用于对外部署；正式演示前换用随机令牌，并限制监听和网络访问范围。

2026-10-09 新增组合工具后，独立 MCP SDK 的本机 HTTP 烟测可发现三个工具，空病例调用组合工具时只产生一条真实检测错误事件，返回 `CASE_NOT_REGISTERED` 与“未获得影像结果”。**Nexent 中原服务仍是旧的两工具配置，须刷新工具发现、调整 Agent 绑定并重新做自然语言对话验收**；不能把独立 SDK 结果当作 Nexent Agent 已通过。

## 3. 知识库门禁

`knowledge-base/` 现有文件是**待专家逐条审核的草稿**，暂不整体上传。尤其不能仅凭 RAG 文本生成自动 Lung-RADS/Fleischner 分级：必须由结构化规则先判断适用范围、缺失字段和数值条件，再由医生核准。`03-Lung-RADS分级.md` 已修正一处明显错误，但这不等于整个文件或其余资料通过医学审校。审核后为每条知识记录原始出处、版本、适用人群、禁用场景、复核人和日期，再按批准版本入库。

## 4. 智能体约束与演示验收

智能体应先确认病例 ID、筛查或偶发场景及必要临床字段；调用工具后展示原始候选与其待复核状态。没有医生确认时不得生成“已确认结节”“低风险/无风险”或确定的随访间隔。`model_score` 不得称为“恶性概率”。信息不足时列出缺失项和医生下一步复核事项。最终建议必须可回溯到规则版本、知识来源和工具运行批次。

新工具返回契约要求第一步检查 `ok`。`ok=false` 时仅能复述 `error_code` 和失败说明，明确“没有影像推理/分类结果”，不得读取不存在的 `findings`、推断阴性、改用另一个病例 ID 或继续分类。只有 `ok=true` 且有本次 `run_id` 才能使用候选编号。此约束仍需在 Nexent 的真实对话中复验，不能因单元测试通过而宣称 Agent 已稳定执行。

2026-10-08 的 Nexent 复验中，“使用要求”已保存上述 `ok` 规则，但 Qwen3 8B 仍把检测调用写成最终代码文本；平台自检通过，服务端无工具执行事件。新版错误返回尚未进入 Agent 推理。独立门禁 `deploy/verify_agent_failure.py` 可用签名审计与最终回答文本检查空病例降级；必须以真实调试轨迹配合使用。详见 [联调记录](integration-log-2026-10-07.md)。

运行日志与 Nexent v2.7.0 源码对照表明，本轮是两次 CodeAgent 输出协议错误后的“原文最终答案”回退；平台自验证并未证明代码被执行。正式演示的验收条件必须检查服务端签名 `CallToolRequest` 事件。不能只通过继续增加提示词或引用“自检通过”解除草稿状态。

演示至少保存脱敏证据：有效病例、未知病例 ID、路径型输入被拒、错误批次/候选 ID 被拒、无医生确认时不出最终分级、医生确认后的可追溯输出、工具失败时的降级说明。联通与启用已在本机 Nexent 页面验证；仍需保存可提交的脱敏截图、Agent 配置导出和真实工具调用轨迹。

使用空病例清单启动本机模型服务后，独立 MCP SDK 经鉴权 HTTP 通道再次验收：`detect_lung_nodules(case_id="demo-001")` 返回 `ok=false, error_code=CASE_NOT_REGISTERED`，`case_123` 返回 `CASE_OUT_OF_SCOPE`，且两者不含影像字段。签名审计分别验出 `error` 与 `denied`，没有进行 DICOM 推理。Nexent Agent 对新版契约的对话处理仍需单独复验。
