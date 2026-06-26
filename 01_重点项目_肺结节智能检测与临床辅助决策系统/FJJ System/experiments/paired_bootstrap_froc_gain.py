import argparse
import csv
import json
import random
from pathlib import Path

try:
    from bootstrap_froc import percentile_interval
    from froc_eval import FP_RATES, evaluate_froc, read_annotations, read_predictions, read_seriesuids
except ImportError:
    from experiments.bootstrap_froc import percentile_interval
    from experiments.froc_eval import FP_RATES, evaluate_froc, read_annotations, read_predictions, read_seriesuids


def group_by_series(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row.seriesuid, []).append(row)
    return groups


def clone_annotation(annotation, seriesuid):
    return type(annotation)(seriesuid, annotation.x, annotation.y, annotation.z, annotation.diameter_mm)


def clone_prediction(prediction, seriesuid):
    return type(prediction)(seriesuid, prediction.x, prediction.y, prediction.z, prediction.probability)


def summarize(annotations, predictions, seriesuids):
    _points, sensitivities, cpm = evaluate_froc(annotations, predictions, seriesuids)
    values = {"cpm": cpm}
    for rate in FP_RATES:
        values[f"sensitivity_at_{rate}_fp_per_scan"] = sensitivities[rate]
    return values


def paired_resample(annotations, baseline_predictions, experimental_predictions, seriesuids, rng):
    ann_by_series = group_by_series(annotations)
    base_by_series = group_by_series(baseline_predictions)
    exp_by_series = group_by_series(experimental_predictions)
    sampled_annotations = []
    sampled_baseline = []
    sampled_experimental = []
    sampled_seriesuids = []
    for index in range(len(seriesuids)):
        source = rng.choice(seriesuids)
        sampled_id = f"{source}__boot{index}"
        sampled_seriesuids.append(sampled_id)
        sampled_annotations.extend(clone_annotation(item, sampled_id) for item in ann_by_series.get(source, []))
        sampled_baseline.extend(clone_prediction(item, sampled_id) for item in base_by_series.get(source, []))
        sampled_experimental.extend(clone_prediction(item, sampled_id) for item in exp_by_series.get(source, []))
    return sampled_annotations, sampled_baseline, sampled_experimental, sampled_seriesuids


def summarize_gain_samples(samples):
    ci95 = {}
    for key, values in samples.items():
        lower, upper = percentile_interval(values, alpha=0.05)
        ci95[key] = {"lower": lower, "upper": upper}
    p_gain_positive = {
        key: sum(1 for value in values if value > 0) / len(values) if values else None
        for key, values in samples.items()
    }
    return ci95, p_gain_positive


def one_paired_bootstrap_sample(annotations, baseline_predictions, experimental_predictions, seriesuids, seed, sample_index):
    rng = random.Random(f"{seed}:{sample_index}")
    sample_annotations, sample_baseline, sample_experimental, sample_seriesuids = paired_resample(
        annotations, baseline_predictions, experimental_predictions, seriesuids, rng
    )
    if not sample_annotations:
        return None
    baseline = summarize(sample_annotations, sample_baseline, sample_seriesuids)
    experimental = summarize(sample_annotations, sample_experimental, sample_seriesuids)
    return {key: experimental[key] - baseline[key] for key in baseline}


def resumable_paired_bootstrap_gain(
    annotations,
    baseline_predictions,
    experimental_predictions,
    seriesuids,
    n_boot=1000,
    seed=20260615,
    existing_samples=None,
):
    point_baseline = summarize(annotations, baseline_predictions, seriesuids)
    point_experimental = summarize(annotations, experimental_predictions, seriesuids)
    point_gain = {key: point_experimental[key] - point_baseline[key] for key in point_baseline}
    samples = {key: list((existing_samples or {}).get(key, [])) for key in point_gain}

    sample_index = 0
    while len(next(iter(samples.values()))) < n_boot:
        if sample_index < len(next(iter(samples.values()))):
            sample_index += 1
            continue
        gain = one_paired_bootstrap_sample(
            annotations, baseline_predictions, experimental_predictions, seriesuids, seed, sample_index
        )
        sample_index += 1
        if gain is None:
            continue
        for key in samples:
            samples[key].append(gain[key])

    ci95, p_gain_positive = summarize_gain_samples(samples)
    return {
        "n_boot_requested": n_boot,
        "n_boot_accepted": len(next(iter(samples.values()))),
        "seed": seed,
        "series_count": len(seriesuids),
        "annotation_count": len(annotations),
        "baseline_prediction_count": len(baseline_predictions),
        "experimental_prediction_count": len(experimental_predictions),
        "baseline_point": point_baseline,
        "experimental_point": point_experimental,
        "gain_point": point_gain,
        "gain_ci95": ci95,
        "p_gain_positive": p_gain_positive,
        "samples": samples,
    }


def paired_bootstrap_gain(annotations, baseline_predictions, experimental_predictions, seriesuids, n_boot=1000, seed=20260615):
    return resumable_paired_bootstrap_gain(
        annotations, baseline_predictions, experimental_predictions, seriesuids, n_boot=n_boot, seed=seed
    )


def write_gain_csv(path, summary):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "gain", "ci95_lower", "ci95_upper", "p_gain_positive"])
        writer.writeheader()
        for metric, gain in summary["gain_point"].items():
            ci = summary["gain_ci95"][metric]
            writer.writerow({
                "metric": metric,
                "gain": gain,
                "ci95_lower": ci["lower"],
                "ci95_upper": ci["upper"],
                "p_gain_positive": summary["p_gain_positive"][metric],
            })


def main():
    parser = argparse.ArgumentParser(description="Paired series-bootstrap gain CI between two LUNA16 FROC prediction sets.")
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--baseline-predictions", required=True)
    parser.add_argument("--experimental-predictions", required=True)
    parser.add_argument("--seriesuids", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--resume", action="store_true", help="Continue from paired_bootstrap_gain_summary.json in out-dir.")
    args = parser.parse_args()

    annotations = read_annotations(args.annotations)
    baseline_predictions = read_predictions(args.baseline_predictions)
    experimental_predictions = read_predictions(args.experimental_predictions)
    seriesuids = read_seriesuids(args.seriesuids, annotations, baseline_predictions + experimental_predictions)
    wanted = set(seriesuids)
    annotations = [item for item in annotations if item.seriesuid in wanted]
    baseline_predictions = [item for item in baseline_predictions if item.seriesuid in wanted]
    experimental_predictions = [item for item in experimental_predictions if item.seriesuid in wanted]

    out_dir = Path(args.out_dir)
    existing_samples = None
    checkpoint = out_dir / "paired_bootstrap_gain_summary.json"
    if args.resume and checkpoint.exists():
        previous = json.loads(checkpoint.read_text(encoding="utf-8"))
        if previous.get("seed") == args.seed:
            existing_samples = previous.get("samples")

    summary = resumable_paired_bootstrap_gain(
        annotations,
        baseline_predictions,
        experimental_predictions,
        seriesuids,
        n_boot=args.n_boot,
        seed=args.seed,
        existing_samples=existing_samples,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "paired_bootstrap_gain_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_gain_csv(out_dir / "paired_bootstrap_gain_ci95.csv", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
