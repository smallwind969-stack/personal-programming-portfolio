from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentManifest(BaseModel):
    agentKey: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    displayName: str
    description: str
    kind: Literal["supervisor", "specialist", "humanGate", "toolAdapter"] = "specialist"
    framework: Literal["langgraph", "deterministic", "human"] = "langgraph"
    capabilities: list[str] = Field(min_length=1)
    requiredWorkerCapabilities: list[Literal["cpu", "gpu", "localLlm"]] = Field(default_factory=lambda: ["cpu"])
    inputSchema: str
    outputSchema: str
    enabled: bool = True
    safetyBoundary: list[str] = Field(default_factory=list)


class WorkflowNodeManifest(BaseModel):
    nodeId: str
    agentKey: str
    stageLabel: str
    requiresHuman: bool = False
    inputSummary: list[str] = Field(default_factory=list)
    methodSummary: list[str] = Field(default_factory=list)
    metricSummary: list[str] = Field(default_factory=list)
    outputSummary: list[str] = Field(default_factory=list)


class WorkflowManifest(BaseModel):
    workflowKey: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    displayName: str
    description: str = ""
    nodes: list[WorkflowNodeManifest] = Field(min_length=1)
    edges: dict[str, list[str]]
    entryNodeId: str


class AgentCatalogSnapshot(BaseModel):
    framework: Literal["langgraph"] = "langgraph"
    frameworkVersion: str
    agentCount: int
    workflowCount: int
    agents: list[AgentManifest]
    workflows: list[WorkflowManifest]
    disclaimer: Literal["研发实验建议"] = "研发实验建议"
