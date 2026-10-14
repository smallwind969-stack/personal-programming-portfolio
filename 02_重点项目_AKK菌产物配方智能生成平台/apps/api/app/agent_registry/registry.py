from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from app.agent_registry.models import AgentCatalogSnapshot, AgentManifest, WorkflowManifest


class AgentCatalogValidationError(ValueError):
    pass


class AgentCatalog:
    def __init__(self) -> None:
        self._agents: dict[str, AgentManifest] = {}
        self._workflows: dict[str, WorkflowManifest] = {}

    def register_agent(self, manifest: AgentManifest) -> None:
        if manifest.agentKey in self._agents:
            raise AgentCatalogValidationError(f"agent {manifest.agentKey} already registered")
        self._agents[manifest.agentKey] = manifest

    def register_workflow(self, workflow: WorkflowManifest) -> None:
        if workflow.workflowKey in self._workflows:
            raise AgentCatalogValidationError(f"workflow {workflow.workflowKey} already registered")
        node_ids = [node.nodeId for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise AgentCatalogValidationError("workflow contains duplicate node ids")
        if workflow.entryNodeId not in node_ids:
            raise AgentCatalogValidationError("entry node is missing")
        missing = sorted({node.agentKey for node in workflow.nodes} - self._agents.keys())
        if missing:
            raise AgentCatalogValidationError(f"workflow references missing agents: {', '.join(missing)}")
        referenced = set(workflow.edges) | {target for targets in workflow.edges.values() for target in targets}
        unknown_nodes = referenced - set(node_ids)
        if unknown_nodes:
            raise AgentCatalogValidationError(f"workflow references missing nodes: {', '.join(sorted(unknown_nodes))}")
        self._assert_acyclic(workflow)
        self._workflows[workflow.workflowKey] = workflow

    @staticmethod
    def _assert_acyclic(workflow: WorkflowManifest) -> None:
        visiting: set[str] = set(); visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise AgentCatalogValidationError("workflow contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target in workflow.edges.get(node_id, []):
                visit(target)
            visiting.remove(node_id); visited.add(node_id)

        for node in workflow.nodes:
            visit(node.nodeId)

    def agent(self, key: str) -> AgentManifest:
        try: return self._agents[key]
        except KeyError as exc: raise AgentCatalogValidationError(f"agent {key} is not registered") from exc

    def workflow(self, key: str) -> WorkflowManifest:
        try: return self._workflows[key]
        except KeyError as exc: raise AgentCatalogValidationError(f"workflow {key} is not registered") from exc

    def snapshot(self) -> AgentCatalogSnapshot:
        try: framework_version = version("langgraph")
        except PackageNotFoundError: framework_version = "unavailable"
        agents = sorted(self._agents.values(), key=lambda item: item.agentKey)
        workflows = sorted(self._workflows.values(), key=lambda item: item.workflowKey)
        return AgentCatalogSnapshot(frameworkVersion=framework_version, agentCount=len(agents), workflowCount=len(workflows), agents=agents, workflows=workflows)
