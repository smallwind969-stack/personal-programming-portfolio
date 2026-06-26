import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
CASE_CONTEXT = ROOT / "case_context"
UPLOADS = ROOT / "uploads"
PROCESSED = ROOT / "static" / "processed"
OUT = ROOT / "docs" / "research_loop"
FIG = OUT / "figures"


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "font.size": 8,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
})


@dataclass
class Nodule:
    patient_id: str
    nodule_id: str
    source: str
    slice_idx: Optional[int]
    x: Optional[float]
    y: Optional[float]
    prob: Optional[float]
    malignancy_prob: Optional[float]
    status: str
    doctor_confirmed: bool
    diameter_mm: Optional[float]
    bbox_3d: dict


def ensure_dirs():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def to_float(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    if value in ("", None):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def normalize_nodule(patient_id, item):
    return Nodule(
        patient_id=patient_id,
        nodule_id=str(item.get("nodule_id") or item.get("id") or ""),
        source=item.get("source") or "model",
        slice_idx=to_int(item.get("slice_idx", item.get("slice_index"))),
        x=to_float(item.get("x")),
        y=to_float(item.get("y")),
        prob=to_float(item.get("prob", item.get("detection_prob"))),
        malignancy_prob=to_float(item.get("malignancy_prob")),
        status=item.get("status") or "pending",
        doctor_confirmed=bool(item.get("doctor_confirmed", item.get("source") == "doctor")),
        diameter_mm=to_float(item.get("diameter_mm")),
        bbox_3d=item.get("bbox_3d") if isinstance(item.get("bbox_3d"), dict) else {},
    )


def load_reviews():
    reviews = []
    for path in sorted(CASE_CONTEXT.glob("*/doctor_review.json")):
        data = read_json(path)
        patient_id = path.parent.name
        model = [normalize_nodule(patient_id, item) for item in data.get("model_findings", [])]
        doctor = [normalize_nodule(patient_id, item) for item in data.get("doctor_nodules", [])]
        reviews.append({
            "patient_id": patient_id,
            "updated_at": data.get("updated_at", ""),
            "clinical_context": data.get("clinical_context", {}),
            "model_findings": model,
            "doctor_nodules": doctor,
        })
    return reviews


def count_files(path, suffix):
    if not path.exists():
        return 0
    return len(list(path.glob(f"*{suffix}")))


def case_manifest(reviews):
    ids = sorted(set(
        [p.name for p in UPLOADS.iterdir() if p.is_dir()] if UPLOADS.exists() else []
    ) | set(
        [p.name for p in PROCESSED.iterdir() if p.is_dir()] if PROCESSED.exists() else []
    ) | {r["patient_id"] for r in reviews})

    rows = []
    review_by_id = {r["patient_id"]: r for r in reviews}
    for pid in ids:
        review = review_by_id.get(pid, {})
        rows.append({
            "patient_id": pid,
            "dicom_count": count_files(UPLOADS / pid, ".dcm"),
            "preview_slice_count": count_files(PROCESSED / pid, ".png"),
            "model_finding_count": len(review.get("model_findings", [])),
            "doctor_added_count": len(review.get("doctor_nodules", [])),
            "clinical_fields_filled": sum(1 for v in (review.get("clinical_context") or {}).values() if str(v).strip()),
            "review_updated_at": review.get("updated_at", ""),
        })
    return rows


def distance(a, b):
    if a.slice_idx is None or b.slice_idx is None or a.x is None or b.x is None or a.y is None or b.y is None:
        return math.inf
    dz = abs(a.slice_idx - b.slice_idx)
    if dz > 3:
        return math.inf
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (dz * 4) ** 2)


def match_predictions(predictions, references, max_distance=40):
    used = set()
    matches = []
    for pi, pred in enumerate(predictions):
        candidates = []
        for ri, ref in enumerate(references):
            if ri in used:
                continue
            d = distance(pred, ref)
            if d <= max_distance:
                candidates.append((d, ri))
        if candidates:
            d, ri = min(candidates, key=lambda x: x[0])
            used.add(ri)
            matches.append((pi, ri, d))
    tp = len(matches)
    fp = len(predictions) - tp
    fn = len(references) - tp
    return tp, fp, fn, matches


def active(nodule):
    return nodule.status != "dismissed" and nodule.doctor_confirmed


def evaluate_reviews(reviews, threshold=0.0):
    rows = []
    total = {"tp": 0, "fp": 0, "fn": 0, "pred": 0, "ref": 0}
    for review in reviews:
        refs = [n for n in review["model_findings"] + review["doctor_nodules"] if active(n)]
        preds = [n for n in review["model_findings"] if n.status != "dismissed" and (n.prob is None or n.prob >= threshold)]
        tp, fp, fn, _ = match_predictions(preds, refs)
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        rows.append({
            "patient_id": review["patient_id"],
            "threshold": threshold,
            "reference_nodules": len(refs),
            "model_predictions": len(preds),
            "tp_proxy": tp,
            "fp_proxy": fp,
            "fn_proxy": fn,
            "precision_proxy": round(precision, 4),
            "recall_proxy": round(recall, 4),
        })
        total["tp"] += tp
        total["fp"] += fp
        total["fn"] += fn
        total["pred"] += len(preds)
        total["ref"] += len(refs)
    total_precision = total["tp"] / (total["tp"] + total["fp"]) if total["tp"] + total["fp"] else 0
    total_recall = total["tp"] / (total["tp"] + total["fn"]) if total["tp"] + total["fn"] else 0
    summary = {
        "threshold": threshold,
        "patient_count": len(reviews),
        "reference_nodules": total["ref"],
        "model_predictions": total["pred"],
        "tp_proxy": total["tp"],
        "fp_proxy": total["fp"],
        "fn_proxy": total["fn"],
        "precision_proxy": round(total_precision, 4),
        "recall_proxy": round(total_recall, 4),
    }
    return rows, summary


def threshold_sweep(reviews):
    thresholds = [0.0, 0.4, 0.6, 0.75, 0.85, 0.9, 0.95, 0.98, 0.99]
    return [evaluate_reviews(reviews, t)[1] for t in thresholds]


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_pub(fig, stem):
    for ext in ("svg", "pdf", "png", "tiff"):
        kwargs = {"bbox_inches": "tight"}
        if ext in ("png", "tiff"):
            kwargs["dpi"] = 600
        fig.savefig(FIG / f"{stem}.{ext}", **kwargs)
    plt.close(fig)


def plot_case_inventory(manifest_rows):
    patients = [r["patient_id"] for r in manifest_rows]
    dicom = [r["dicom_count"] for r in manifest_rows]
    model = [r["model_finding_count"] for r in manifest_rows]
    doctor = [r["doctor_added_count"] for r in manifest_rows]
    x = range(len(patients))
    fig, ax1 = plt.subplots(figsize=(7.2, 3.35))
    ax1.bar([i - 0.2 for i in x], dicom, width=0.4, color="#9ecae1", label="DICOM slices")
    ax2 = ax1.twinx()
    ax2.bar([i + 0.12 for i in x], model, width=0.24, color="#74c476", label="Model findings")
    ax2.bar([i + 0.36 for i in x], doctor, width=0.24, color="#fdae6b", label="Doctor-added")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(patients, rotation=20, ha="right")
    ax1.set_ylabel("DICOM slices")
    ax2.set_ylabel("Nodule records")
    ax1.set_title("Current review-set inventory")
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        handles1 + handles2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=3,
    )
    save_pub(fig, "fig_case_inventory")


def plot_threshold_sweep(rows):
    t = [r["threshold"] for r in rows]
    precision = [r["precision_proxy"] for r in rows]
    recall = [r["recall_proxy"] for r in rows]
    fp = [r["fp_proxy"] for r in rows]
    fig, ax1 = plt.subplots(figsize=(6.4, 3.2))
    ax1.plot(t, precision, marker="o", color="#3182bd", label="Precision proxy")
    ax1.plot(t, recall, marker="o", color="#31a354", label="Recall proxy")
    ax1.set_ylim(0, 1.05)
    ax1.set_xlabel("Detection probability threshold")
    ax1.set_ylabel("Proxy score")
    if max(fp) > 0:
        ax2 = ax1.twinx()
        ax2.bar(t, fp, width=0.025, alpha=0.25, color="#de2d26", label="FP proxy")
        ax2.set_ylabel("False-positive proxy count")
        handles2, labels2 = ax2.get_legend_handles_labels()
    else:
        ax1.text(
            0.98,
            0.08,
            "FP proxy = 0 across saved-review sweep",
            transform=ax1.transAxes,
            ha="right",
            color="#8a2d2d",
            fontsize=8,
        )
        handles2, labels2 = [], []
    ax1.set_title("Threshold sweep on saved review records")
    handles1, labels1 = ax1.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left")
    save_pub(fig, "fig_threshold_sweep")


def plot_evidence_gap(manifest_rows, evaluation_summary):
    labels = ["Cases indexed", "Reviewed cases", "Reference nodules", "Model predictions", "Doctor-added"]
    reviewed = sum(1 for r in manifest_rows if r["model_finding_count"] or r["doctor_added_count"])
    values = [
        len(manifest_rows),
        reviewed,
        evaluation_summary["reference_nodules"],
        evaluation_summary["model_predictions"],
        sum(r["doctor_added_count"] for r in manifest_rows),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    colors = ["#9ecae1", "#9ecae1", "#74c476", "#74c476", "#fdae6b"]
    ax.barh(labels[::-1], values[::-1], color=colors[::-1])
    for y, v in enumerate(values[::-1]):
        ax.text(v + 0.05, y, str(v), va="center")
    ax.set_title("Evidence currently available for manuscript claims")
    ax.set_xlabel("Count")
    save_pub(fig, "fig_evidence_gap")


def build_report(manifest_rows, eval_rows, summary, sweep_rows):
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "review-proxy evaluation from current local cases and doctor_review.json files",
        "warning": (
            "These are NOT clinical validation metrics. They use physician review records in this workspace "
            "as a small reference set to build an experiment loop and identify evidence gaps."
        ),
        "inventory": {
            "case_count": len(manifest_rows),
            "reviewed_case_count": sum(1 for r in manifest_rows if r["model_finding_count"] or r["doctor_added_count"]),
            "dicom_count_total": sum(r["dicom_count"] for r in manifest_rows),
            "model_finding_count_total": sum(r["model_finding_count"] for r in manifest_rows),
            "doctor_added_count_total": sum(r["doctor_added_count"] for r in manifest_rows),
        },
        "evaluation_at_threshold_0": summary,
        "threshold_sweep": sweep_rows,
        "next_experiments": [
            "Freeze a case list and export all predictions to immutable JSON.",
            "Ask a reviewer to correct every case in the workstation, then rerun review-proxy evaluation.",
            "Expose VNet probability threshold and ResNet filter threshold as experiment parameters.",
            "Run FROC-like analysis after a real nodule-level reference set is available.",
            "Add ablations: no CBAM, no dual-branch context, no Agent safety rule layer.",
        ],
    }
    (OUT / "research_loop_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# Research loop evidence report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        "## Boundary",
        report["warning"],
        "",
        "## Current inventory",
    ]
    for k, v in report["inventory"].items():
        md.append(f"- {k}: {v}")
    md += [
        "",
        "## Proxy evaluation at threshold 0.0",
    ]
    for k, v in summary.items():
        md.append(f"- {k}: {v}")
    md += [
        "",
        "## Figure outputs",
        "- figures/fig_case_inventory.svg/pdf/png/tiff",
        "- figures/fig_threshold_sweep.svg/pdf/png/tiff",
        "- figures/fig_evidence_gap.svg/pdf/png/tiff",
        "",
        "## Next experiments",
    ]
    md.extend(f"- {item}" for item in report["next_experiments"])
    (OUT / "research_loop_report.md").write_text("\n".join(md), encoding="utf-8")


def main():
    ensure_dirs()
    reviews = load_reviews()
    manifest_rows = case_manifest(reviews)
    eval_rows, summary = evaluate_reviews(reviews, threshold=0.0)
    sweep_rows = threshold_sweep(reviews)

    write_csv(OUT / "case_manifest.csv", manifest_rows)
    write_csv(OUT / "review_proxy_evaluation_by_case.csv", eval_rows)
    write_csv(OUT / "threshold_sweep.csv", sweep_rows)

    plot_case_inventory(manifest_rows)
    plot_threshold_sweep(sweep_rows)
    plot_evidence_gap(manifest_rows, summary)
    build_report(manifest_rows, eval_rows, summary, sweep_rows)

    print(OUT)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
