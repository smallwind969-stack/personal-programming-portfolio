import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.followup_agent import build_followup_recommendation
from agent.guideline_rules import audit_agent_text
import agent.followup_agent as followup_agent


CASE_CONTEXT = ROOT / "case_context"
OUT = ROOT / "docs" / "world_frontier" / "agent_safety"


def load_review(patient_id):
    path = CASE_CONTEXT / patient_id / "doctor_review.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def final_nodules(review):
    return list(review.get("model_findings", [])) + list(review.get("doctor_nodules", []))


def flatten_text(result):
    chunks = [
        result.get("case_summary", ""),
        result.get("followup_suggestion", ""),
        result.get("presentation_highlight", ""),
        result.get("safety_note", ""),
    ]
    for rec in result.get("recommendations", []):
        chunks.append(rec.get("suggestion", ""))
        guideline = rec.get("guideline_hint") or {}
        chunks.append(guideline.get("recommendation", ""))
        chunks.append(guideline.get("basis", ""))
    return "\n".join(str(chunk) for chunk in chunks if chunk)


def audit_patient(patient_id):
    review = load_review(patient_id)
    context = {
        "clinical_context": review.get("clinical_context", {}),
        "final_nodules": final_nodules(review),
    }
    original_llm = followup_agent.generate_with_local_qwen
    followup_agent.generate_with_local_qwen = lambda _prompt: ("", {"available": False, "reason": "audit_offline"})
    try:
        result = build_followup_recommendation(patient_id, case_context=context)
    finally:
        followup_agent.generate_with_local_qwen = original_llm
    audit = audit_agent_text(flatten_text(result))
    return {
        "patient_id": patient_id,
        "audit": audit,
        "risk_level": result.get("risk_level"),
        "statistics": result.get("statistics"),
        "missing_information": result.get("missing_information"),
        "recommendation_count": len(result.get("recommendations", [])),
        "guideline_frameworks": sorted({
            (rec.get("guideline_hint") or {}).get("primary_framework", "")
            for rec in result.get("recommendations", [])
            if rec.get("guideline_hint")
        }),
    }


def main():
    parser = argparse.ArgumentParser(description="Audit follow-up Agent safety and guideline metadata.")
    parser.add_argument("--patient", action="append", help="Patient id to audit. Repeat for multiple.")
    parser.add_argument("--out", default=str(OUT / "followup_agent_safety_audit.json"))
    args = parser.parse_args()

    patients = args.patient or sorted(p.name for p in CASE_CONTEXT.iterdir() if p.is_dir())
    rows = [audit_patient(patient) for patient in patients]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [row["patient_id"] for row in rows if not row["audit"]["passed"]]
    print(f"audited={len(rows)}")
    print(f"failed={failed}")
    print(out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
