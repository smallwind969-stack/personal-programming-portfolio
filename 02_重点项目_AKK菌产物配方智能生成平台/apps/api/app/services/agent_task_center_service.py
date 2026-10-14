from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.agent_tasks import AgentTaskCenter, AgentTaskProjection
from app.services.agent_orchestrator import agent_orchestrator
from app.services.experiment_service import experiment_service
from app.services.optimization_orchestrator import optimization_orchestrator
from app.services.product_innovation_agent import product_innovation_agent
from app.services.product_requirement_registry import product_requirement_registry
from app.services.simulation_run_orchestrator import simulation_run_orchestrator
from app.agent_registry.builtin import agent_catalog


class AgentTaskCenterNotFoundError(LookupError):
    pass


_BUSINESS_LABELS = {
    "productInnovation": "产品需求研判",
    "dataAnalysis": "数据分析流程",
    "simulation": "仿真模拟流程",
    "optimization": "工艺优化流程",
}


def _business_label(agent_key: str) -> str:
    return _BUSINESS_LABELS.get(agent_key, agent_key)


class AgentTaskCenterService:
    def get(self, experiment_id: str) -> AgentTaskCenter:
        overview = experiment_service.get_workspace_overview(experiment_id)
        if overview is None:
            raise AgentTaskCenterNotFoundError(experiment_id)

        innovation = product_innovation_agent.latest_run(experiment_id)
        requirement = product_requirement_registry.latest(experiment_id)
        analysis = agent_orchestrator.peek_latest_run(experiment_id)
        simulation = simulation_run_orchestrator.peek_latest(experiment_id)
        optimization = optimization_orchestrator.peek_latest(experiment_id)
        workflow = agent_catalog.workflow("experiment-rd-loop")
        workflow_nodes = {node.nodeId: node for node in workflow.nodes}
        dependencies = {node.nodeId: [] for node in workflow.nodes}
        for source, targets in workflow.edges.items():
            for target in targets:
                dependencies[target].append(source)

        product_status = "completed" if requirement else "needsReview" if innovation else "waiting"
        product_progress = 100 if requirement else 70 if innovation else 0
        product_sources = []
        if innovation:
            product_sources.append(f"innovation-run://{innovation.runId}")
        if requirement:
            product_sources.append(f"product-requirement://{requirement.requirementVersionId}")

        data_status = analysis.status if analysis else "waiting"
        data_progress = analysis.progressPercent if analysis else 0
        data_sources = [f"runtime://{analysis.runtimeRunId}", f"agent-run://{analysis.runId}"] if analysis else []

        simulation_status = simulation.status if simulation else "waiting"
        simulation_progress = simulation.progressPercent if simulation else 0
        simulation_blocked = []
        if not analysis or analysis.status != "completed":
            simulation_blocked.append("需要先完成数据分析并通过人工确认")

        optimization_status = optimization.status if optimization else "waiting"
        optimization_progress = optimization.progressPercent if optimization else 0
        optimization_blocked = []
        if requirement is None:
            optimization_blocked.append("尚未固化产品需求版本")
        if not simulation or simulation.status != "completed":
            optimization_blocked.append("需要先完成仿真并形成正式结果")

        tasks = [
            AgentTaskProjection(
                taskId="product-innovation", agentKey="productInnovation", agentName=_business_label("productInnovation"),
                status=product_status, progressPercent=product_progress, route=f"/experiments/{experiment_id}/innovation",
                dependsOn=dependencies["product-innovation"], blockedReasons=[], runId=innovation.runId if innovation else None,
                version=requirement.version if requirement else None,
                summary="将自然语言产品构想转成可验证需求，并经人工确认固化版本。",
                sourceRefs=product_sources, canRetry=innovation is not None,
            ),
            AgentTaskProjection(
                taskId="data-analysis", agentKey="dataAnalysis", agentName=_business_label("dataAnalysis"),
                status=data_status, progressPercent=data_progress, route=f"/experiments/{experiment_id}/analysis",
                dependsOn=dependencies["data-analysis"], blockedReasons=[], runId=analysis.runId if analysis else None,
                version=analysis.version if analysis else None,
                summary="收集定位、字段识别、清洗对齐、特征工程、建模和评估的状态图。",
                sourceRefs=data_sources, canGuide=bool(analysis and analysis.status in {"running", "needsReview"}),
                canRetry=bool(analysis and analysis.status in {"failed", "stopped"}),
            ),
            AgentTaskProjection(
                taskId="simulation", agentKey="simulation", agentName=_business_label("simulation"),
                status=simulation_status, progressPercent=simulation_progress, route=f"/experiments/{experiment_id}/simulation",
                dependsOn=dependencies["simulation"], blockedReasons=simulation_blocked,
                runId=simulation.runId if simulation else None, version=simulation.version if simulation else None,
                summary="基于已验收数学模型运行虚拟产线，并保留阶段状态与预测证据。",
                sourceRefs=[f"simulation-run://{simulation.runId}"] if simulation else [],
                canRetry=bool(simulation and simulation.status in {"failed", "stopped"}),
            ),
            AgentTaskProjection(
                taskId="optimization", agentKey="optimization", agentName=_business_label("optimization"),
                status=optimization_status, progressPercent=optimization_progress, route=f"/experiments/{experiment_id}/optimization",
                dependsOn=dependencies["optimization"], blockedReasons=optimization_blocked,
                runId=optimization.runId if optimization else None, version=optimization.version if optimization else None,
                summary="生成候选工艺、允许人工调参并以新版本执行模型重训与验收。",
                sourceRefs=[f"optimization-run://{optimization.runId}"] if optimization else [],
                canRetry=bool(optimization and optimization.status in {"failed", "stopped"}),
            ),
        ]
        active = [item.taskId for item in tasks if item.status in {"running", "interrupted", "needsReview"}]
        progress = round(sum(item.progressPercent for item in tasks) / len(tasks))
        if any(item.status == "failed" for item in tasks):
            overall = "failed"
        elif any(item.status == "interrupted" for item in tasks):
            overall = "interrupted"
        elif any(item.status == "needsReview" for item in tasks):
            overall = "needsReview"
        elif any(item.status == "running" for item in tasks):
            overall = "running"
        elif all(item.status == "completed" for item in tasks):
            overall = "completed"
        else:
            overall = "waiting"
        return AgentTaskCenter(
            experimentId=experiment_id, overallStatus=overall, progressPercent=progress,
            activeTaskIds=active, tasks=tasks, generatedAt=datetime.now(timezone.utc).isoformat(),
        )


agent_task_center_service = AgentTaskCenterService()
