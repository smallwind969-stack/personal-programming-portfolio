from fastapi.testclient import TestClient
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from app.main import app
from app.services.agent_orchestrator import agent_orchestrator

client = TestClient(app)


def advance_agent(experiment_id: str, run: dict):
    return client.post(
        f"/experiments/{experiment_id}/agent-runs/{run['runId']}/advance",
        json={"expectedRevision": run["runtimeRevision"], "commandId": f"test-{uuid4().hex}"},
    )


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_status() -> None:
    response = client.get("/system/status")
    assert response.status_code == 200
    status = response.json()
    assert status["status"] == "ok"
    assert status["productCount"] >= 1
    assert status["knowledgeItemCount"] >= 1
    assert status["knowledgeChunkCount"] >= 1
    assert status["researchUseOnly"] is True


def test_list_products() -> None:
    response = client.get("/akk-products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert products[0]["sourceType"] == "mock"


def test_product_detail() -> None:
    response = client.get("/akk-products/akk-postbiotic-powder")
    assert response.status_code == 200
    assert response.json()["productId"] == "akk-postbiotic-powder"


def test_generate_formula() -> None:
    response = client.post(
        "/formula/generate",
        json={
            "applicationTargetId": "nutrition_powder",
            "targetProperties": ["gut health concept fit"],
            "constraints": ["sensory check required"],
            "preferredProductIds": ["akk-postbiotic-powder", "akk-fiber-complex"],
            "excludedProductIds": [],
            "maxIngredientCount": 2,
            "notes": "mock test",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["research_use_only"] is True
    assert result["researchUseOnly"] is True
    assert result["candidates"][0]["composition"]
    assert result["candidates"][0]["predictions"]
    assert result["candidates"][0]["riskItems"]
    assert result["candidates"][0]["experimentSuggestions"]
    assert result["candidates"][0]["companionIngredients"]
    assert result["candidates"][0]["knowledgeReferences"]
    assert result["candidates"][0]["agentTrace"]


def test_get_formula_result() -> None:
    response = client.get("/formula-results/mock-result-001")
    assert response.status_code == 200
    assert response.json()["research_use_only"] is True


def test_list_formula_results() -> None:
    response = client.get("/formula-results")
    assert response.status_code == 200
    assert response.json()[0]["research_use_only"] is True


def test_list_knowledge_items() -> None:
    response = client.get("/knowledge", params={"query": "low sugar yogurt"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert items[0]["knowledgeId"]
    assert items[0]["usableInsights"]
    assert "retrievalScore" in items[0]
    assert "matchReasons" in items[0]
    assert "validationMetrics" in items[0]


def test_list_knowledge_chunks() -> None:
    response = client.get("/knowledge/chunks", params={"query": "low sugar yogurt", "limit": 5})
    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) >= 1
    assert chunks[0]["chunkId"]
    assert chunks[0]["text"]
    assert chunks[0]["retrievalScore"] > 0


def test_generate_formula_uses_literature_references() -> None:
    response = client.post(
        "/formula/generate",
        json={
            "applicationTargetId": "yogurt",
            "targetProperties": ["low sugar", "gut health concept"],
            "constraints": ["clean label", "medium cost"],
            "preferredProductIds": ["akk-postbiotic-powder", "akk-metabolite-blend"],
            "excludedProductIds": [],
            "maxIngredientCount": 2,
            "notes": "female low sugar yogurt, clean taste, medium cost",
        },
    )
    assert response.status_code == 200
    references = response.json()["candidates"][0]["knowledgeReferences"]
    assert references
    assert references[0]["evidenceLevel"] in {"A", "B", "C", "D"}
    assert references[0]["relevanceReason"]
    assert "retrievalScore" in references[0]
    assert "keyPassages" in references[0]


def test_llm_status() -> None:
    response = client.get("/llm/status")
    assert response.status_code == 200
    status = response.json()
    assert "enabled" in status
    assert status["provider"]
    assert status["model"]


def test_list_experiments() -> None:
    response = client.get("/experiments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_experiment_archive_lists_workspace_summaries() -> None:
    response = client.get("/experiments/archive")

    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] >= 4
    assert body["averageConfidenceScore"] > 0
    assert body["experiments"][0].keys() >= {
        "experimentId",
        "name",
        "batchCode",
        "currentStage",
        "status",
        "resultSummary",
        "confidenceScore",
    }


def test_experiment_workspace_overview_has_stage_gates() -> None:
    response = client.get("/experiments/exp-akk-018/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-018"
    assert [stage["stage"] for stage in body["stages"]] == [
        "dataAnalysis",
        "simulation",
        "optimization",
    ]
    assert body["stages"][0]["status"] == "completed"
    assert body["stages"][1]["canEnter"] is True
    assert body["stages"][1]["canRun"] is True
    assert body["stages"][2]["canEnter"] is False


def test_incomplete_experiment_can_view_but_not_run_simulation() -> None:
    response = client.get("/experiments/exp-culture-009/overview")

    assert response.status_code == 200
    body = response.json()
    simulation_stage = next(stage for stage in body["stages"] if stage["stage"] == "simulation")
    assert simulation_stage["canEnter"] is True
    assert simulation_stage["canRun"] is False
    assert body["reliabilityMetrics"][0] == {
        "label": "数据完整度",
        "value": "--",
        "detail": "尚未上传可用设备数据",
    }


def test_experiment_workspace_overview_returns_404_for_unknown_id() -> None:
    response = client.get("/experiments/missing-experiment/overview")

    assert response.status_code == 404
    assert response.json()["detail"] == "Experiment not found"


def test_agent_run_uses_seven_node_auditable_state_graph() -> None:
    created = client.post("/experiments/exp-akk-018/agent-runs")

    assert created.status_code == 200
    run = created.json()
    assert run["runtimeBackend"] == "deterministic"
    assert run["runtimeRunId"].startswith("runtime-")
    assert run["status"] == "running"
    assert run["version"] == 1
    assert run["progressPercent"] == 8
    assert [node["agentKey"] for node in run["nodes"]] == [
        "dataCollectionLocalization",
        "schemaRecognition",
        "cleaningAlignment",
        "featureEngineering",
        "modeling",
        "modelEvaluation",
        "humanReview",
    ]
    assert run["nodes"][0]["status"] == "running"
    assert run["nodes"][0]["methodSummary"]
    assert run["events"][0]["eventType"] == "runStarted"

    advanced = advance_agent("exp-akk-018", run)
    assert advanced.status_code == 200
    next_run = advanced.json()
    assert next_run["nodes"][0]["status"] == "completed"
    assert next_run["nodes"][0]["outputSummary"]
    assert next_run["nodes"][1]["status"] == "running"
    assert next_run["runtimeRevision"] > run["runtimeRevision"]
    assert next_run["events"][0]["eventId"].startswith("runtime-event-")
    assert next_run["events"][-1]["eventType"] == "nodeStarted"


def test_agent_run_rejects_concurrent_advance_from_stale_revision() -> None:
    run = client.post("/experiments/exp-akk-018/agent-runs").json()
    def request(command_id: str):
        return client.post(
            f"/experiments/exp-akk-018/agent-runs/{run['runId']}/advance",
            json={"expectedRevision": run["runtimeRevision"], "commandId": command_id},
        )
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(request, ["concurrent-a", "concurrent-b"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    latest = client.get(f"/experiments/exp-akk-018/agent-runs/latest").json()
    assert latest["currentNodeId"] == "schema-recognition"


def test_latest_agent_run_reprojects_external_runtime_interrupt() -> None:
    run = client.post("/experiments/exp-akk-018/agent-runs").json()
    agent_orchestrator._runtime.interrupt(run["runtimeRunId"], "等待外部字段确认")
    latest = client.get("/experiments/exp-akk-018/agent-runs/latest").json()
    assert latest["status"] == "interrupted"
    assert latest["runtimeRevision"] > run["runtimeRevision"]


def test_only_one_pending_guidance_is_allowed_and_checkpoint_apply_is_atomic() -> None:
    run = client.post("/experiments/exp-algae-017/agent-runs").json()
    first = client.post(f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/preview", json={"prompt": "优先采用企业内部字段命名规则"}).json()
    second = client.post(f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/preview", json={"prompt": "同时检查设备时间字段"}).json()
    scheduled = client.post(f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/apply", json={"guidanceId": first["guidanceId"], "confirmed": True})
    assert scheduled.status_code == 200
    assert client.post(f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/apply", json={"guidanceId": second["guidanceId"], "confirmed": True}).status_code == 409
    body = scheduled.json()
    advanced = advance_agent("exp-algae-017", body)
    assert advanced.status_code == 200
    result = advanced.json()
    assert result["pendingGuidance"] is None
    assert result["appliedGuidance"][-1]["guidanceId"] == first["guidanceId"]
    runtime = agent_orchestrator._runtime.get(result["runtimeRunId"])
    assert runtime.state["pendingGuidance"] is None
    assert runtime.state["activeGuidance"]["guidanceId"] == first["guidanceId"]


def test_agent_guidance_requires_preview_before_safe_checkpoint_application() -> None:
    run = client.post("/experiments/exp-algae-017/agent-runs").json()
    payload = {"prompt": "字段识别时优先采用企业内部 pH 与温度命名规则"}

    preview_response = client.post(
        f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/preview",
        json=payload,
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["requiresRestart"] is False
    assert preview["safeCheckpoint"] == "schemaRecognition"
    assert preview["affectedNodes"] == ["schemaRecognition", "cleaningAlignment"]

    apply_response = client.post(
        f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/apply",
        json={"guidanceId": preview["guidanceId"], "confirmed": True},
    )
    assert apply_response.status_code == 200
    updated = apply_response.json()
    assert updated["pendingGuidance"]["status"] == "scheduled"
    assert updated["events"][-1]["eventType"] == "guidanceScheduled"
    assert client.post(
        f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/apply",
        json={"guidanceId": preview["guidanceId"], "confirmed": True},
    ).status_code == 409


def test_stopped_agent_run_cannot_advance_and_restart_creates_new_version() -> None:
    run = client.post("/experiments/exp-food-012/agent-runs").json()
    stopped_response = client.post(
        f"/experiments/exp-food-012/agent-runs/{run['runId']}/stop"
    )
    assert stopped_response.status_code == 200
    stopped = stopped_response.json()
    assert stopped["status"] == "stopped"

    advance_response = advance_agent("exp-food-012", stopped)
    assert advance_response.status_code == 409

    restarted_response = client.post(
        f"/experiments/exp-food-012/agent-runs/{run['runId']}/restart",
        json={},
    )
    assert restarted_response.status_code == 200
    restarted = restarted_response.json()
    assert restarted["runId"] != run["runId"]
    assert restarted["parentRunId"] == run["runId"]
    assert restarted["version"] == 2
    assert restarted["status"] == "running"


def test_agent_run_rejects_unknown_experiment_and_cross_run_guidance() -> None:
    assert client.post("/experiments/unknown-experiment/agent-runs").status_code == 404
    source = client.post("/experiments/exp-akk-018/agent-runs").json()
    target = client.post("/experiments/exp-culture-009/agent-runs").json()
    preview = client.post(
        f"/experiments/exp-akk-018/agent-runs/{source['runId']}/guidance/preview",
        json={"prompt": "字段识别使用企业温度命名规则"},
    ).json()

    response = client.post(
        f"/experiments/exp-culture-009/agent-runs/{target['runId']}/guidance/apply",
        json={"guidanceId": preview["guidanceId"], "confirmed": True},
    )
    assert response.status_code == 409


def test_restart_required_guidance_is_applied_to_child_version() -> None:
    run = client.post("/experiments/exp-culture-009/agent-runs").json()
    preview = client.post(
        f"/experiments/exp-culture-009/agent-runs/{run['runId']}/guidance/preview",
        json={"prompt": "训练时增加 XGBoost 特征组合比较"},
    ).json()
    assert preview["requiresRestart"] is True
    stopped = client.post(
        f"/experiments/exp-culture-009/agent-runs/{run['runId']}/stop"
    ).json()
    restarted = client.post(
        f"/experiments/exp-culture-009/agent-runs/{stopped['runId']}/restart",
        json={"guidanceId": preview["guidanceId"]},
    )
    assert restarted.status_code == 200
    child = restarted.json()
    assert child["appliedGuidance"][0]["guidanceId"] == preview["guidanceId"]
    assert child["events"][-1]["eventType"] == "guidanceAppliedOnRestart"


def test_human_review_requires_structured_decision() -> None:
    run = client.post("/experiments/exp-akk-018/agent-runs").json()
    for _ in range(6):
        run = advance_agent("exp-akk-018", run).json()
    assert run["status"] == "needsReview"
    assert advance_agent("exp-akk-018", run).status_code == 409

    reviewed = client.post(
        f"/experiments/exp-akk-018/agent-runs/{run['runId']}/review",
        json={
            "decision": "approved",
            "reason": "字段映射与异常点已由研发负责人复核",
            "operator": "研发负责人",
            "impactScope": ["model-v1", "simulation-admission"],
        },
    )
    assert reviewed.status_code == 200
    body = reviewed.json()
    assert body["status"] == "completed"
    assert body["humanDecisions"][0]["reason"]
    assert next(node for node in body["nodes"] if node["nodeId"] == "human-review")["completedAt"]
    assert body["events"][-1]["eventType"] == "humanDecisionRecorded"


def test_guidance_rejects_stopped_run_and_passed_checkpoint() -> None:
    run = client.post("/experiments/exp-algae-017/agent-runs").json()
    for _ in range(2):
        run = advance_agent("exp-algae-017", run).json()
    preview = client.post(
        f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/preview",
        json={"prompt": "字段识别采用新的温度命名规则"},
    ).json()
    assert client.post(
        f"/experiments/exp-algae-017/agent-runs/{run['runId']}/guidance/apply",
        json={"guidanceId": preview["guidanceId"], "confirmed": True},
    ).status_code == 409
    stopped = client.post(
        f"/experiments/exp-algae-017/agent-runs/{run['runId']}/stop"
    ).json()
    assert client.post(
        f"/experiments/exp-algae-017/agent-runs/{stopped['runId']}/guidance/preview",
        json={"prompt": "字段识别采用另一套命名规则"},
    ).status_code == 409


def test_process_lines() -> None:
    response = client.get("/process/production-lines")
    assert response.status_code == 200
    lines = response.json()
    assert len(lines) >= 1
    assert lines[0]["lineName"]
    assert "temperatureRange" in lines[0]


def test_generate_process_task() -> None:
    response = client.post(
        "/process/tasks/generate",
        json={
            "targetProductName": "功能果冻",
            "targetProductForm": "果冻",
            "akkProductType": "AKK 后生元",
            "applicationDirection": "肠道健康方向",
            "optimizationStrategy": "综合平衡",
            "allowCoCulture": True,
            "targetScale": "中试",
            "constraints": ["避免窄 pH 窗口"],
            "productionLineId": "pilot-anaerobic-b",
        },
    )
    assert response.status_code == 200
    task = response.json()
    assert task["disclaimer"] == "内部研发实验建议"
    assert "功能果冻" in task["targetSummary"]
    assert len(task["candidatePlans"]) == 3
    assert task["candidatePlans"][0]["displayName"] in {"保守验证方案", "强化产出方案", "工艺平衡方案"}
    assert task["surface"]["xAxisLabel"] == "温度"
    assert task["surface"]["yAxisLabel"] == "pH"
    assert task["surface"]["zAxisLabel"] == "综合评分"


def test_create_process_feedback() -> None:
    response = client.post(
        "/process/feedback",
        json={
            "taskId": "task-demo",
            "actualYield": "中等",
            "actualActivity": "待复测",
            "contaminationObserved": False,
            "equipmentAbnormalities": ["无"],
            "conclusion": "部分成功",
            "notes": "需要复核 pH 波动。",
        },
    )
    assert response.status_code == 200
    assert response.json()["conclusion"] == "部分成功"
