import json
from unittest.mock import patch

import pytest

from model_run_evidence import EvidenceError, fetch_verified_run


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return json.dumps(self.payload).encode("utf-8")


def test_fetches_current_server_run_and_keeps_only_read_only_evidence():
    def fake_open(request, timeout):
        assert request.full_url == "http://127.0.0.1:8100/runs/case-001/abcdef"
        assert request.get_header("Authorization") == "Bearer secret"
        assert timeout == 5
        return FakeResponse({
            "case_id": "case-001", "run_id": "abcdef",
            "findings": [{
                "candidate_id": "c001", "detection_score": 0.8,
                "model_score": 0.77, "review_status": "pending",
                "slice_idx": 12, "x": 34, "y": 56,
                "dicom_dir": "D:/private/patient", "status": "malignant",
            }],
        })

    with patch("model_run_evidence.urlopen", fake_open):
        result = fetch_verified_run("case-001", "abcdef", "http://127.0.0.1:8100", "secret")
    assert result["findings"] == [{
        "candidate_id": "c001", "detection_score": 0.8,
        "model_score": 0.77, "review_status": "pending",
    }]
    assert "private" not in str(result)


@pytest.mark.parametrize("payload", [
    {"case_id": "other", "run_id": "abcdef", "findings": []},
    {"case_id": "case-001", "run_id": "wrong", "findings": []},
    {"case_id": "case-001", "run_id": "abcdef", "findings": [{"candidate_id": "c001", "review_status": "confirmed"}]},
    {"case_id": "case-001", "run_id": "abcdef", "findings": [{"candidate_id": "c001"}, {"candidate_id": "c001"}]},
])
def test_rejects_mismatched_or_invalid_evidence(payload):
    with patch("model_run_evidence.urlopen", lambda *_args, **_kwargs: FakeResponse(payload)):
        with pytest.raises(EvidenceError):
            fetch_verified_run("case-001", "abcdef", "http://127.0.0.1:8100", "secret")


def test_rejects_invalid_identifier_before_http():
    with patch("model_run_evidence.urlopen") as opener:
        with pytest.raises(EvidenceError):
            fetch_verified_run("../private", "abcdef", "http://127.0.0.1:8100", "secret")
        opener.assert_not_called()
