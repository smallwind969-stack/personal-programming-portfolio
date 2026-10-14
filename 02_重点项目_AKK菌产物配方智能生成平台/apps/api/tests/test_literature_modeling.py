from pathlib import Path

from app.modeling.literature_modeling import (
    build_literature_dataset,
    evaluate_models,
    recommend_process_settings,
    run_modeling_pipeline,
)


def test_build_literature_dataset_contains_required_research_boundaries():
    dataset = build_literature_dataset(random_state=7, augmented_rows=72)

    assert len(dataset) >= 72
    assert {
        "carbonSource",
        "carbonConcentration",
        "cultureHours",
        "temperatureC",
        "anaerobicScore",
        "molecularWeightKda",
        "akkGrowthScore",
        "scfaScore",
        "barrierScore",
    }.issubset(dataset.columns)
    assert dataset["evidenceLevel"].isin(["literature-anchor", "simulated-augmentation"]).all()
    assert (dataset["carbonConcentration"] >= 0).all()
    assert dataset["akkGrowthScore"].between(0, 100).all()


def test_evaluate_models_reports_metrics_and_ranked_feature_sensitivity():
    dataset = build_literature_dataset(random_state=11, augmented_rows=96)
    evaluation = evaluate_models(dataset, random_state=11)

    assert evaluation["sampleCount"] == len(dataset)
    assert evaluation["metrics"]["structureModel"]["rmse"] >= 0
    assert evaluation["metrics"]["functionModel"]["r2"] > 0.5
    assert evaluation["predictions"].shape[0] > 0
    assert evaluation["featureSensitivity"][0]["importance"] >= evaluation["featureSensitivity"][-1]["importance"]


def test_recommend_process_settings_marks_output_as_research_suggestion():
    dataset = build_literature_dataset(random_state=19, augmented_rows=90)
    evaluation = evaluate_models(dataset, random_state=19)
    recommendation = recommend_process_settings(
        target_product="Akk postbiotic freeze-dried powder",
        current_line_state={
            "temperatureC": 36.5,
            "ph": 6.8,
            "anaerobicScore": 0.82,
            "stirringRpm": 145,
            "pressureMpa": 0.1,
        },
        evaluation=evaluation,
    )

    assert recommendation["label"] == "研发实验建议"
    assert "confidence" in recommendation
    assert recommendation["recommendedSettings"]["carbonSource"] in {"BFP", "lambdaCarrageenan", "UBFP"}
    assert recommendation["validationIndicators"]


def test_run_modeling_pipeline_creates_figures_and_word_report(tmp_path):
    result = run_modeling_pipeline(output_dir=tmp_path, random_state=23, augmented_rows=84)

    assert Path(result["reportPath"]).exists()
    assert Path(result["datasetPath"]).exists()
    assert Path(result["metricsPath"]).exists()
    assert len(result["figurePaths"]) >= 4
    assert all(Path(path).exists() for path in result["figurePaths"])
