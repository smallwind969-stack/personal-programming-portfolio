from fastapi.testclient import TestClient

from app.decision.contracts import DecisionRequirement
from app.decision.trace_store import DecisionTrace
from app.main import app
from app.routers.decision import get_pipeline, get_requirement_parser


class FakeParser:
    def parse(self, text):
        return DecisionRequirement(
            productType="功能性果冻",
            attributes=[],
            missingConstraints=["minimumOutput"],
            confidence=0.95,
        )


class FakePipeline:
    def execute(self, identity, payload):
        return DecisionTrace(
            runId="run-api-001",
            tenantId=identity.tenantId,
            userId=identity.userId,
            rawRequirement=payload["rawRequirement"],
            requirement=payload["requirement"],
            knowledgeVersion="knowledge-v1",
            knowledgeIds=["evidence-1"],
            modelVersions={"target_product_output": "model-v1"},
            search={"scoringVersion": "deterministic-grid-v1"},
            plans=[
                {"planId": "maximize_output:candidate-0001"},
                {"planId": "balanced:candidate-0002"},
                {"planId": "minimize_resource:candidate-0003"},
            ],
            generatedAt="2026-07-25T10:00:00+00:00",
        )

    def get(self, identity, run_id):
        return self.execute(
            identity,
            {"rawRequirement": "saved", "requirement": {"productType": "功能性果冻"}},
        )

    def confirm(self, identity, run_id, plan_id, note):
        trace = self.get(identity, run_id)
        trace.confirmationStatus = "confirmed"
        return trace

    def cases(self, identity):
        return [self.get(identity, "run-api-001")]


def _headers(client):
    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Test-Admin-2026!"},
    )
    return {"Authorization": f"Bearer {login.json()['accessToken']}"}


def test_parse_and_one_click_run_are_authenticated_and_traced():
    app.dependency_overrides[get_requirement_parser] = lambda: FakeParser()
    app.dependency_overrides[get_pipeline] = lambda: FakePipeline()
    client = TestClient(app)
    headers = _headers(client)
    try:
        parsed = client.post(
            "/decision/requirements/parse",
            headers=headers,
            json={"text": "低糖高弹性菌藻果冻"},
        )
        assert parsed.status_code == 200
        assert parsed.json()["missingConstraints"] == ["minimumOutput"]

        run = client.post(
            "/decision/runs",
            headers=headers,
            json={
                "rawRequirement": "低糖高弹性菌藻果冻",
                "requirement": {"productType": "功能性果冻"},
                "supplementalConstraints": {
                    "minimumOutput": 7,
                    "minimumQuality": 7,
                },
            },
        )
        assert run.status_code == 201
        assert len(run.json()["plans"]) == 3
        assert run.json()["tenantId"] == "tenant-junzao-qiyuan"
    finally:
        app.dependency_overrides.clear()
