from unittest.mock import patch

import app2


def test_verify_run_requires_local_case_and_returns_server_evidence(tmp_path):
    (tmp_path / "uploads" / "case-001").mkdir(parents=True)
    expected = {"case_id": "case-001", "run_id": "abcdef", "findings": []}
    with patch.object(app2, "base_dir", str(tmp_path)), patch.object(app2, "fetch_verified_run", return_value=expected) as fetch:
        client = app2.app.test_client()
        response = client.post("/agent/verify-run", json={"case_id": "case-001", "run_id": "abcdef"})
        assert response.status_code == 200
        assert response.json["evidence"] == expected
        fetch.assert_called_once()

        other_origin = client.post(
            "/agent/verify-run",
            json={"case_id": "case-001", "run_id": "abcdef"},
            headers={"Origin": "https://other.example"},
        )
        assert other_origin.status_code == 403
        unknown = client.post("/agent/verify-run", json={"case_id": "unknown", "run_id": "abcdef"})
        assert unknown.status_code == 404
        fetch.assert_called_once()


def test_followup_ignores_browser_supplied_review_and_findings():
    stored_review = {"patient_id": "case-001", "updated_at": "now", "model_findings": [], "doctor_nodules": []}
    with patch.object(app2, "load_review", return_value=stored_review) as load, patch.object(
        app2, "build_followup_recommendation", return_value={"risk_label": "待复核"}
    ) as build:
        response = app2.app.test_client().post("/agent/followup", json={
            "patient_id": "case-001",
            "findings": [{"doctor_confirmed": True, "status": "confirmed"}],
            "doctor_review": {"model_findings": [{"doctor_confirmed": True, "status": "confirmed"}]},
        })
    assert response.status_code == 200
    assert response.json["case_context"]["final_nodules"] == []
    assert build.call_args.args[1] == []
    load.assert_called_once()
