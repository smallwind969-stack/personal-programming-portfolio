# 肺结节 Follow-up Agent 指南约束与安全审计报告

生成日期：2026-06-14

## 1. 升级目标

本轮升级将 follow-up Agent 从普通风险提示改造为“规则约束 + 指南提示 + 缺失信息审计 + 安全语句检查”的结构化辅助系统。目标不是让 Agent 代替医生，而是让它在医生复核工作流中稳定输出可追溯、可审计、不过界的建议。

## 2. 联网依据

- Fleischner Society 2017: incidental pulmonary nodules 的随访建议依赖结节大小、密度、数量和患者风险因素。
- Lung-RADS/NCCN: 肺癌筛查场景应采用筛查路径，不应与偶发结节路径混用。
- ACR Lung-RADS v2022: 筛查 CT 的结构化分级与管理建议需要结合筛查资格、结节变化和类别。

## 3. 新增工程资产

| 文件 | 作用 |
|---|---|
| `agent/guideline_rules.py` | Fleischner-like 规则提示、场景适用性、缺失输入、安全词表审计 |
| `experiments/audit_followup_agent.py` | 对真实 `case_context` 跑离线 Agent 安全审计 |
| `tests/test_guideline_rules.py` | 覆盖实性、磨玻璃、部分实性、筛查场景和安全审计 |
| `tests/test_followup_agent.py` | 验证 follow-up Agent 每个结节携带 `guideline_hint` |

## 4. 当前真实病例审计结果

审计命令：

```powershell
python experiments\audit_followup_agent.py
```

结果：

```text
audited=3
failed=[]
```

输出文件：

```text
docs\world_frontier\agent_safety\followup_agent_safety_audit.json
```

## 5. Agent 输出新增字段

每个结节 recommendation 现在包含：

- `guideline_hint.framework`: 当前采用的指南提示来源，默认 Fleischner 2017。
- `guideline_hint.primary_framework`: 若临床场景为筛查，则提示 Lung-RADS/NCCN。
- `guideline_hint.recommendation`: 按大小/密度/风险生成的谨慎建议。
- `guideline_hint.missing_inputs`: 生成精确建议前缺少的信息。
- `guideline_hint.suspicious_features`: 毛刺、分叶、胸膜牵拉等可疑征象。
- `guideline_hint.basis`: 明确说明这是辅助提示，不能替代医生决策。

## 6. 当前限制

该规则层是 “Fleischner-like” 辅助提示，不是完整医学指南计算器。原因：

- 当前病例缺少稳定的结节最大径、实性成分大小、增长率和完整筛查资格字段。
- 本地医生复核记录仍不完整。
- Lung-RADS/NCCN 的正式使用需要明确筛查场景、既往筛查轮次和类别定义。

## 7. 下一步

1. 在前端增加结节最大径、实性成分大小、结节类型、是否筛查场景等字段。
2. 将 Agent 输出拆为“影像事实、指南提示、缺失信息、安全边界”四栏。
3. 增加 Lung-RADS v2022 规则模块，用于筛查场景。
4. 将安全审计纳入每次生成 PDF 或汇报材料前的自动检查。
