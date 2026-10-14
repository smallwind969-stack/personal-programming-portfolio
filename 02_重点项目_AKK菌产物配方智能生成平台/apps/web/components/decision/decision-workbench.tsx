"use client";

import { useEffect, useReducer } from "react";
import {
  decisionRequirementSchema,
  decisionTraceSchema,
  type DecisionPlan,
  type DecisionRequirement,
  type DecisionTrace,
} from "@/lib/decision-schema";

type Phase = "draft" | "parsing" | "needs_constraints" | "retrieving" | "modeling" | "searching" | "ready" | "confirmed" | "failed";
type State = {
  phase: Phase;
  request: string;
  requirement: DecisionRequirement | null;
  constraintValues: Record<string, string>;
  minimumQualifiedOutput: string;
  trace: DecisionTrace | null;
  selectedPlanId: string | null;
  cases: DecisionTrace[];
  error: string | null;
};
type Action =
  | { type: "request"; value: string }
  | { type: "phase"; phase: Phase }
  | { type: "parsed"; requirement: DecisionRequirement }
  | { type: "constraint"; key: string; value: string }
  | { type: "minimum"; value: string }
  | { type: "ready"; trace: DecisionTrace }
  | { type: "select"; planId: string }
  | { type: "confirmed"; trace: DecisionTrace }
  | { type: "cases"; cases: DecisionTrace[] }
  | { type: "failed"; message: string }
  | { type: "reset" };

const initialState: State = {
  phase: "draft",
  request: "开发一款低糖、高弹性、具有抗氧化能力的菌藻功能性果冻",
  requirement: null,
  constraintValues: {},
  minimumQualifiedOutput: "0.20",
  trace: null,
  selectedPlanId: null,
  cases: [],
  error: null,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "request": return { ...state, request: action.value };
    case "phase": return { ...state, phase: action.phase, error: null };
    case "parsed":
      return {
        ...state,
        phase: "needs_constraints",
        requirement: action.requirement,
        constraintValues: Object.fromEntries(action.requirement.missingConstraints.map((key) => [key, ""])),
      };
    case "constraint":
      return { ...state, constraintValues: { ...state.constraintValues, [action.key]: action.value } };
    case "minimum": return { ...state, minimumQualifiedOutput: action.value };
    case "ready":
      return {
        ...state,
        phase: "ready",
        trace: action.trace,
        selectedPlanId: action.trace.plans[1]?.planId ?? action.trace.plans[0]?.planId ?? null,
      };
    case "select": return { ...state, selectedPlanId: action.planId };
    case "confirmed": return { ...state, phase: "confirmed", trace: action.trace };
    case "cases": return { ...state, cases: action.cases };
    case "failed": return { ...state, phase: "failed", error: action.message };
    case "reset": return { ...initialState, cases: state.cases };
  }
}

const phaseOrder: Array<[Phase, string]> = [
  ["parsing", "需求解析"],
  ["retrieving", "证据检索"],
  ["modeling", "模型推理"],
  ["searching", "参数寻优"],
  ["ready", "方案就绪"],
];
const objectiveLabels: Record<DecisionPlan["objective"], string> = {
  maximize_output: "产出最大",
  balanced: "综合最优",
  minimize_resource: "资源消耗最小",
};

async function postJson(path: string, payload: unknown) {
  const response = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(detail?.message ?? detail?.code ?? "请求执行失败");
  }
  return body;
}

function parameterLabel(key: string) {
  return ({ transfer_number: "适应传代", time_hours: "培养时间" }[key] ?? key);
}

function phaseProgress(phase: Phase) {
  if (phase === "confirmed" || phase === "ready") return phaseOrder.length - 1;
  return phaseOrder.findIndex(([key]) => key === phase);
}

export function DecisionWorkbench() {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    fetch("/api/decision/cases")
      .then((response) => (response.ok ? response.json() : []))
      .then((data) => dispatch({ type: "cases", cases: decisionTraceSchema.array().parse(data) }))
      .catch(() => undefined);
  }, []);

  async function parseRequirement() {
    dispatch({ type: "phase", phase: "parsing" });
    try {
      const data = await postJson("/decision/requirements/parse", { text: state.request });
      dispatch({ type: "parsed", requirement: decisionRequirementSchema.parse(data) });
    } catch (error) {
      dispatch({ type: "failed", message: error instanceof Error ? error.message : "需求解析失败" });
    }
  }

  async function runDecision() {
    if (!state.requirement) return;
    if (Object.values(state.constraintValues).some((value) => !value.trim())) {
      dispatch({ type: "failed", message: "请补充全部必要约束后再运行。" });
      return;
    }
    dispatch({ type: "phase", phase: "retrieving" });
    try {
      const data = await postJson("/decision/runs", {
        rawRequirement: state.request,
        requirement: state.requirement,
        supplementalConstraints: {
          ...state.constraintValues,
          minimumOutput: Number(state.minimumQualifiedOutput),
          minimumQuality: Number(state.minimumQualifiedOutput),
        },
      });
      dispatch({ type: "ready", trace: decisionTraceSchema.parse(data) });
    } catch (error) {
      dispatch({ type: "failed", message: error instanceof Error ? error.message : "决策执行失败" });
    }
  }

  async function confirmPlan() {
    if (!state.trace || !state.selectedPlanId) return;
    try {
      const data = await postJson(`/decision/runs/${state.trace.runId}/confirm`, {
        planId: state.selectedPlanId,
        note: "管理员确认进入下一轮验证",
      });
      dispatch({ type: "confirmed", trace: decisionTraceSchema.parse(data) });
    } catch (error) {
      dispatch({ type: "failed", message: error instanceof Error ? error.message : "方案确认失败" });
    }
  }

  async function replay(runId: string) {
    dispatch({ type: "phase", phase: "searching" });
    try {
      const data = await postJson(`/decision/cases/${runId}/replay`, {});
      dispatch({ type: "ready", trace: decisionTraceSchema.parse(data) });
    } catch (error) {
      dispatch({ type: "failed", message: error instanceof Error ? error.message : "案例复算失败" });
    }
  }

  const selectedPlan = state.trace?.plans.find((plan) => plan.planId === state.selectedPlanId);
  const progress = phaseProgress(state.phase);

  return (
    <div className="decision-workbench">
      <section className="decision-command">
        <div>
          <p className="decision-kicker">生产决策 / 当前企业</p>
          <h1>从产品需求到产线方案</h1>
          <p className="decision-lead">菌藻启元研发中心 · 管理员工作区</p>
        </div>
        <div className="decision-run-mark"><span>运行模式</span><strong>在线计算</strong></div>
      </section>

      <section className="decision-console">
        <div className="decision-input-zone">
          <label htmlFor="product-request">产品需求</label>
          <textarea id="product-request" rows={4} value={state.request}
            onChange={(event) => dispatch({ type: "request", value: event.target.value })} />
          <button disabled={state.phase !== "draft" && state.phase !== "failed"} onClick={parseRequirement}>
            建立决策任务
          </button>
        </div>
        <div className="decision-pulse" aria-label="自动执行进度">
          {phaseOrder.map(([phase, label], index) => {
            const done = progress > index || state.phase === "confirmed";
            const active = state.phase === phase ||
              (["retrieving", "modeling", "searching"].includes(phase) &&
               ["retrieving", "modeling", "searching"].includes(state.phase));
            return <div className={done ? "done" : active ? "active" : ""} key={phase}>
              <span>{done ? "✓" : String(index + 1).padStart(2, "0")}</span><p>{label}</p>
            </div>;
          })}
        </div>
      </section>

      {state.phase === "needs_constraints" && state.requirement ? (
        <section className="decision-constraints">
          <div>
            <p className="decision-kicker">计算前确认</p>
            <h2>补充必要边界</h2>
            <p>已识别：{state.requirement.productType} · 解析置信度 {Math.round((state.requirement.confidence ?? 0) * 100)}%</p>
          </div>
          {state.requirement.missingConstraints.map((key) => (
            <label key={key}>{key}
              <input value={state.constraintValues[key] ?? ""}
                onChange={(event) => dispatch({ type: "constraint", key, value: event.target.value })}
                placeholder="请输入明确数值、单位或检测方法" />
            </label>
          ))}
          <label>最低合格产出（OD600）
            <input type="number" min="0" step="0.05" value={state.minimumQualifiedOutput}
              onChange={(event) => dispatch({ type: "minimum", value: event.target.value })} />
          </label>
          <button onClick={runDecision}>运行完整决策链路</button>
        </section>
      ) : null}

      {state.error ? (
        <section className="decision-error">
          <strong>流程已停止</strong><span>{state.error}</span>
          <button onClick={() => dispatch({ type: "reset" })}>重新开始</button>
        </section>
      ) : null}

      {state.trace ? <>
        <section className="decision-result-head">
          <div><p className="decision-kicker">决策结果 / {state.trace.runId.slice(-8)}</p><h2>三类目标完成同域比较</h2></div>
          <div><span>{String(state.trace.search.scoringVersion ?? "deterministic-grid-v1")}</span>
            <strong>{state.trace.confirmationStatus === "confirmed" ? "已确认" : "待确认"}</strong></div>
        </section>
        <section className="decision-plans">
          {state.trace.plans.map((plan) => {
            const prediction = Object.values(plan.predictions)[0];
            return <button className={state.selectedPlanId === plan.planId ? "decision-plan selected" : "decision-plan"}
              key={plan.planId} onClick={() => dispatch({ type: "select", planId: plan.planId })}>
              <span className="plan-index">{objectiveLabels[plan.objective]}</span>
              <strong>{prediction.value.toFixed(2)} <small>{prediction.lineage.targetUnit ?? ""}</small></strong>
              <p>目标评分 {plan.objectiveScore.toFixed(3)}</p>
              <dl>{Object.entries(plan.parameters).map(([key, value]) =>
                <div key={key}><dt>{parameterLabel(key)}</dt><dd>{value}</dd></div>)}</dl>
              <span className="constraint-pass">硬约束已通过</span>
            </button>;
          })}
        </section>
        {selectedPlan ? <section className="decision-evidence">
          <div>
            <p className="decision-kicker">证据与模型谱系</p>
            <h3>{Object.values(selectedPlan.predictions)[0].lineage.modelVersion}</h3>
            <p>文献基线模型 · 数据 {state.trace.dataVersions.join("、")}</p>
            <code>{Object.values(selectedPlan.predictions)[0].lineage.datasetFingerprint}</code>
          </div>
          <div>
            <p className="decision-kicker">知识与边界</p><h3>{state.trace.knowledgeVersion}</h3>
            <p>{state.trace.knowledgeIds.length} 条启用证据 · {state.trace.applicability.join("；")}</p>
            <p>{state.trace.risks[0] ?? "未发现额外禁用条件"}</p>
          </div>
          <button disabled={state.trace.confirmationStatus === "confirmed"} onClick={confirmPlan}>
            {state.trace.confirmationStatus === "confirmed" ? "方案已由管理员确认" : "确认当前方案"}
          </button>
        </section> : null}
      </> : null}

      <section className="decision-cases">
        <div><p className="decision-kicker">已执行记录</p><h2>案例复算</h2></div>
        {state.cases.length ? state.cases.slice(0, 3).map((item) => (
          <button key={item.runId} onClick={() => replay(item.runId)}>
            <span>{item.requirement.productType}</span>
            <strong>{new Date(item.generatedAt).toLocaleString("zh-CN")}</strong>
            <small>按当前模型与知识版本重新计算 →</small>
          </button>
        )) : <p>完成首个决策后，运行记录将在这里形成可复算案例。</p>}
      </section>
    </div>
  );
}
