import os
from tempfile import TemporaryDirectory

from doctor_review import merge_case_context, save_review


def test_fresh_model_candidate_is_not_doctor_confirmed():
    result = merge_case_context(
        "case-001",
        findings=[{"nodule_id": "model-1", "prob": 0.8}],
    )

    assert len(result["model_findings"]) == 1
    assert result["model_findings"][0]["doctor_confirmed"] is False
    assert result["model_findings"][0]["status"] == "pending"
    assert result["final_nodules"] == []


def test_saving_unreviewed_model_candidate_does_not_confirm_it():
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        review = save_review(
            temp_dir,
            "case-002",
            findings=[{"nodule_id": "model-1", "status": "pending"}],
        )

    assert review["model_findings"][0]["doctor_confirmed"] is False
    assert merge_case_context("case-002", review=review)["final_nodules"] == []


def test_explicit_confirmation_enters_final_list_and_dismissal_does_not():
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        review = save_review(
            temp_dir,
            "case-003",
            findings=[
                {"nodule_id": "model-1", "doctor_confirmed": True, "status": "confirmed"},
                {"nodule_id": "model-2", "doctor_confirmed": False, "status": "dismissed"},
            ],
        )

    final = merge_case_context("case-003", review=review)["final_nodules"]
    assert [item["nodule_id"] for item in final] == ["model-1"]


def test_saved_empty_review_does_not_resurrect_old_model_candidates():
    result = merge_case_context(
        "case-004",
        findings=[{"nodule_id": "deleted-model-1", "status": "pending"}],
        review={"updated_at": "2026-10-07 10:00:00", "model_findings": []},
    )

    assert result["model_findings"] == []
    assert result["final_nodules"] == []
