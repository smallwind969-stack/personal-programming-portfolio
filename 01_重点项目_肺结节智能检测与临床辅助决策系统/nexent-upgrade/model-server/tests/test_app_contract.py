import json
import os
from tempfile import TemporaryDirectory

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app as model_api


class FakeEngine:
    def __init__(self):
        self.loaded_paths = []
        self.detect_kwargs = None
        self.identify_inputs = None

    def load_itk(self, path):
        self.loaded_paths.append(path)
        return "fake-image"

    def run_inference(self, image, **kwargs):
        self.detect_kwargs = kwargs
        return ([{"x_idx": 1, "y_idx": 2, "z_idx": 3, "prob": 0.8, "status": "pending", "dicom_dir": "D:/private/patient"}], {"seconds": 0.1})

    def identify_malignancy(self, image, findings):
        self.identify_inputs = findings
        return ([{**findings[0], "malignancy_prob": 0.77, "status": "malignant"}], {"seconds": 0.1})


def _setup_case(monkeypatch, temp_dir):
    root = os.path.join(temp_dir, "dicom")
    case_dir = os.path.join(root, "sample")
    os.makedirs(case_dir)
    catalog = os.path.join(temp_dir, "catalog.json")
    with open(catalog, "w", encoding="utf-8") as handle:
        json.dump({"case-001": "sample"}, handle)
    monkeypatch.setenv("DICOM_ROOT", root)
    monkeypatch.setenv("CASE_CATALOG_JSON", catalog)
    monkeypatch.setenv("MODEL_SERVER_TOKEN", "test-secret")
    model_api.CANDIDATE_CACHE.clear()
    fake = FakeEngine()
    monkeypatch.setattr(model_api, "get_engine", lambda: fake)
    return case_dir, fake


def test_detect_requires_server_token(monkeypatch):
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        _setup_case(monkeypatch, temp_dir)
        with pytest.raises(HTTPException) as error:
            model_api.detect(model_api.DetectRequest(case_id="case-001"), authorization="")
        assert error.value.status_code == 401


def test_detect_accepts_case_id_and_rejects_raw_path_or_threshold(monkeypatch):
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        case_dir, fake = _setup_case(monkeypatch, temp_dir)
        with pytest.raises(ValidationError):
            model_api.DetectRequest.model_validate({"case_id": "case-001", "dicom_dir": case_dir})
        with pytest.raises(ValidationError):
            model_api.DetectRequest.model_validate({"case_id": "case-001", "prob_threshold": 0.99})
        good = model_api.detect(model_api.DetectRequest(case_id="case-001"), authorization="Bearer test-secret")

        assert fake.loaded_paths == [os.path.realpath(case_dir)]
        assert fake.detect_kwargs["prob_threshold"] == 0.15
        assert good["findings"][0]["candidate_id"] == "c001"
        assert good["findings"][0]["review_status"] == "pending"
        assert "dicom_dir" not in good["findings"][0]


def test_identify_uses_cached_candidate_ids_and_exposes_only_model_score(monkeypatch):
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        _case_dir, fake = _setup_case(monkeypatch, temp_dir)
        detection = model_api.detect(model_api.DetectRequest(case_id="case-001"), authorization="Bearer test-secret")
        run_id = detection["run_id"]

        with pytest.raises(HTTPException) as stale:
            model_api.identify(
                model_api.IdentifyRequest(case_id="case-001", run_id="outdated", candidate_ids=["c001"]),
                authorization="Bearer test-secret",
            )

        with pytest.raises(HTTPException) as error:
            model_api.identify(
                model_api.IdentifyRequest(case_id="case-001", run_id=run_id, candidate_ids=["other"]),
                authorization="Bearer test-secret",
            )
        result = model_api.identify(
            model_api.IdentifyRequest(case_id="case-001", run_id=run_id, candidate_ids=["c001"]),
            authorization="Bearer test-secret",
        )

        assert stale.value.status_code == 409
        assert error.value.status_code == 400
        assert fake.identify_inputs[0]["x_idx"] == 1
        finding = result["findings"][0]
        assert finding["candidate_id"] == "c001"
        assert finding["model_score"] == 0.77
        assert finding["review_status"] == "pending"
        assert "malignancy_prob" not in finding
        assert "status" not in finding


def test_run_evidence_comes_from_server_cache_and_is_not_public_without_token(monkeypatch):
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        _setup_case(monkeypatch, temp_dir)
        detection = model_api.detect(model_api.DetectRequest(case_id="case-001"), authorization="Bearer test-secret")
        run_id = detection["run_id"]

        with pytest.raises(HTTPException) as unauthorized:
            model_api.get_run_evidence("case-001", run_id, authorization="")
        with pytest.raises(HTTPException) as wrong_run:
            model_api.get_run_evidence("case-001", "fabricated", authorization="Bearer test-secret")
        assert unauthorized.value.status_code == 401
        assert wrong_run.value.status_code == 404

        evidence = model_api.get_run_evidence("case-001", run_id, authorization="Bearer test-secret")
        assert evidence["case_id"] == "case-001"
        assert evidence["run_id"] == run_id
        assert evidence["findings"][0]["review_status"] == "pending"
        assert "model_score" not in evidence["findings"][0]
        assert "dicom_dir" not in str(evidence)

        model_api.identify(
            model_api.IdentifyRequest(case_id="case-001", run_id=run_id, candidate_ids=["c001"]),
            authorization="Bearer test-secret",
        )
        classified = model_api.get_run_evidence("case-001", run_id, authorization="Bearer test-secret")
        assert classified["findings"][0]["model_score"] == 0.77
        assert classified["findings"][0]["review_status"] == "pending"
        assert "status" not in classified["findings"][0]

        model_api.detect(model_api.DetectRequest(case_id="case-001"), authorization="Bearer test-secret")
        with pytest.raises(HTTPException) as stale:
            model_api.get_run_evidence("case-001", run_id, authorization="Bearer test-secret")
        assert stale.value.status_code == 404
