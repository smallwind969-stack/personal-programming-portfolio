# Research loop experiment entry points

This folder turns the local FJJ system into a reproducible research loop. The current loop is intentionally conservative: it separates engineering evidence from clinical claims and marks the saved physician review records as a review-proxy reference set, not as formal ground truth.

## 1. Build the current evidence package

```powershell
python experiments\research_loop.py
```

Outputs:

- `docs\research_loop\case_manifest.csv`
- `docs\research_loop\review_proxy_evaluation_by_case.csv`
- `docs\research_loop\threshold_sweep.csv`
- `docs\research_loop\research_loop_report.json`
- `docs\research_loop\research_loop_report.md`
- `docs\research_loop\figures\fig_case_inventory.*`
- `docs\research_loop\figures\fig_threshold_sweep.*`
- `docs\research_loop\figures\fig_evidence_gap.*`

## 2. Run real model threshold experiments

Start or restart the Flask app first, then run a small sweep. A single case can take several minutes on CPU.

```powershell
python experiments\run_detection_sweep.py --patient 曾玉香 --prob-thresholds 0.10,0.15,0.20 --resnet-thresholds 0.35,0.40,0.45 --return-all-candidates
```

Output:

- `docs\research_loop\detection_sweep_runs.csv`

## 3. Scientific interpretation rule

Use the current review-proxy metrics to guide engineering decisions only. Do not report them as clinical sensitivity, specificity, FROC, or external validation. A defensible manuscript needs a frozen case list, complete physician correction for every case, and then a rerun of the evaluation scripts.

## 4. Next upgrade targets

- Freeze a case list and export immutable prediction JSON for every parameter setting.
- Complete physician review for every indexed case.
- Add FROC-style analysis after a true nodule-level reference set exists.
- Add ablations for CBAM, dual-branch context, and Agent follow-up logic.
- Convert this evidence package into the结题报告 and manuscript result section only after the experiment table is complete.

## 5. Export LUNA-style predictions and proxy annotations

The world-frontier track uses LUNA16-style CSV files so the project can move from local demos to public benchmark evaluation.

```powershell
python experiments\export_luna_predictions.py --out docs\world_frontier\local_luna_predictions.csv
python experiments\export_review_proxy_annotations.py --out docs\world_frontier\local_review_proxy_annotations.csv
python experiments\froc_eval.py `
  --annotations docs\world_frontier\local_review_proxy_annotations.csv `
  --predictions docs\world_frontier\local_luna_predictions.csv `
  --out-dir docs\world_frontier\local_proxy_froc
python experiments\plot_froc_summary.py `
  --summary docs\world_frontier\local_proxy_froc\froc_summary.csv `
  --out docs\world_frontier\local_proxy_froc\froc_summary_plot.png
```

Current local proxy result:

- `annotation_count`: 11
- `prediction_count`: 7
- `proxy_CPM`: 0.636364

This is not a LUNA16 official score. It is a local review-proxy FROC result for validating the evaluation pipeline.
