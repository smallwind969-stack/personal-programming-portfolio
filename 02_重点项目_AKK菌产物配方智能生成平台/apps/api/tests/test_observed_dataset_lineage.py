from pathlib import Path

import pandas as pd


DATASET = Path("data/decision/datasets/akk-food-grade-growth-figure2-v1.csv")


def test_every_training_row_has_observed_target_and_source_location():
    dataset = pd.read_csv(DATASET)
    required = {
        "datasetId",
        "sourceUrl",
        "sourceFile",
        "sourceLocation",
        "sourceRow",
        "targetName",
        "targetValue",
        "targetUnit",
        "evidenceKind",
    }
    assert required <= set(dataset.columns)
    assert dataset["targetValue"].notna().all()
    assert dataset["sourceRow"].is_unique
    assert set(dataset["evidenceKind"]) <= {
        "author_table",
        "author_supplement",
        "figure_digitized",
    }


def test_seed_script_does_not_import_simulated_literature_builder():
    source = Path("scripts/seed_literature_model.py").read_text(encoding="utf-8")
    assert "build_literature_dataset" not in source
    assert "augmented_rows" not in source
    assert "random" not in source.lower()
