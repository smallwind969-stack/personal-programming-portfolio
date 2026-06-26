# Research loop evidence report

Generated at: 2026-06-14T02:27:57

## Boundary
These are NOT clinical validation metrics. They use physician review records in this workspace as a small reference set to build an experiment loop and identify evidence gaps.

## Current inventory
- case_count: 3
- reviewed_case_count: 2
- dicom_count_total: 607
- model_finding_count_total: 7
- doctor_added_count_total: 4

## Proxy evaluation at threshold 0.0
- threshold: 0.0
- patient_count: 3
- reference_nodules: 11
- model_predictions: 7
- tp_proxy: 7
- fp_proxy: 0
- fn_proxy: 4
- precision_proxy: 1.0
- recall_proxy: 0.6364

## Figure outputs
- figures/fig_case_inventory.svg/pdf/png/tiff
- figures/fig_threshold_sweep.svg/pdf/png/tiff
- figures/fig_evidence_gap.svg/pdf/png/tiff

## Next experiments
- Freeze a case list and export all predictions to immutable JSON.
- Ask a reviewer to correct every case in the workstation, then rerun review-proxy evaluation.
- Expose VNet probability threshold and ResNet filter threshold as experiment parameters.
- Run FROC-like analysis after a real nodule-level reference set is available.
- Add ablations: no CBAM, no dual-branch context, no Agent safety rule layer.