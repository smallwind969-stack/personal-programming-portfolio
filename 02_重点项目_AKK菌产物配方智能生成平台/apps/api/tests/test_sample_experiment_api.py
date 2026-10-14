from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_sample_workspace_api_creates_ready_to_review_sample() -> None:
    response = client.post("/experiments/sample-workspaces", json={"templateKey": "algae-culture"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["sourceType"] == "sample"
    assert payload["overview"]["sampleTemplateVersion"] == "algae-culture-v1"
    assert payload["asset"]["rowCount"] >= 36
    assert payload["asset"]["contentHash"] == payload["templateContentHash"]
    assert payload["intakeRunId"].startswith("intake-")


def test_sample_workspace_api_rejects_unknown_template() -> None:
    response = client.post("/experiments/sample-workspaces", json={"templateKey": "unknown"})
    assert response.status_code == 422
