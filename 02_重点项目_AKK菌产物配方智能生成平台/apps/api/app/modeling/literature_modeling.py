from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


FEATURE_COLUMNS = [
    "carbonSource",
    "productFormat",
    "carbonConcentration",
    "cultureHours",
    "temperatureC",
    "ph",
    "anaerobicScore",
    "pressureMpa",
    "stirringRpm",
    "pretreated",
]

NUMERIC_FEATURES = [
    "carbonConcentration",
    "cultureHours",
    "temperatureC",
    "ph",
    "anaerobicScore",
    "pressureMpa",
    "stirringRpm",
    "pretreated",
]


def build_literature_dataset(random_state: int = 42, augmented_rows: int = 160) -> pd.DataFrame:
    """Build a deterministic literature-anchored simulated dataset.

    The anchors encode values found in the local papers and patents. Extra rows
    are simulated around those anchors so the first modeling pipeline can run
    before real production batches exist.
    """

    rng = np.random.default_rng(random_state)
    anchors = _literature_anchor_rows()
    rows: list[dict[str, Any]] = [dict(row, evidenceLevel="literature-anchor") for row in anchors]

    carbon_sources = ["BFP", "UBFP", "lambdaCarrageenan", "iotaCarrageenan", "PHP", "agar"]
    formats = ["culture-medium", "postbiotic-powder", "fish-ball", "encapsulated-bead"]

    for _ in range(max(augmented_rows - len(rows), 0)):
        source = rng.choice(carbon_sources, p=[0.28, 0.18, 0.22, 0.10, 0.14, 0.08])
        product_format = rng.choice(formats, p=[0.34, 0.24, 0.25, 0.17])
        row = {
            "carbonSource": source,
            "productFormat": product_format,
            "carbonConcentration": _sample_concentration(rng, source, product_format),
            "cultureHours": float(rng.choice([24, 36, 48, 60, 72])),
            "temperatureC": float(np.clip(rng.normal(37.0, 1.8), 32.0, 42.0)),
            "ph": float(np.clip(rng.normal(6.85, 0.22), 5.7, 7.3)),
            "anaerobicScore": float(np.clip(rng.normal(0.86, 0.10), 0.45, 0.99)),
            "pressureMpa": float(np.clip(rng.choice([0.1, 100, 200, 300, 400]) + rng.normal(0, 8), 0.1, 420)),
            "stirringRpm": float(np.clip(rng.normal(165, 45), 80, 260)),
            "pretreated": int(source == "UBFP" or rng.random() < 0.28),
            "evidenceLevel": "simulated-augmentation",
        }
        rows.append(_with_targets(row, rng))

    dataset = pd.DataFrame(rows)
    target_columns = ["molecularWeightKda", "akkGrowthScore", "scfaScore", "barrierScore"]
    for column in target_columns:
        dataset[column] = dataset[column].clip(0, 100 if column.endswith("Score") else None)
    return dataset


def evaluate_models(dataset: pd.DataFrame, random_state: int = 42) -> dict[str, Any]:
    """Train and evaluate GPR-enhanced structure and function models."""

    X = _encode_features(dataset[FEATURE_COLUMNS])
    y_structure = dataset["molecularWeightKda"].astype(float)
    y_function = dataset["akkGrowthScore"].astype(float)

    X_train, X_test, ys_train, ys_test, yf_train, yf_test = train_test_split(
        X, y_structure, y_function, test_size=0.25, random_state=random_state
    )

    kernel = ConstantKernel(1.0, (0.1, 100.0)) * Matern(length_scale=1.0, nu=1.5) + WhiteKernel(
        noise_level=0.8, noise_level_bounds=(1e-08, 10.0)
    )
    gpr = make_pipeline(
        StandardScaler(),
        GaussianProcessRegressor(kernel=kernel, normalize_y=True, random_state=random_state),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        gpr.fit(X_train, ys_train)
    gpr_train_mean, gpr_train_std = gpr.named_steps["gaussianprocessregressor"].predict(
        gpr.named_steps["standardscaler"].transform(X_train), return_std=True
    )
    gpr_test_mean, gpr_test_std = gpr.named_steps["gaussianprocessregressor"].predict(
        gpr.named_steps["standardscaler"].transform(X_test), return_std=True
    )

    structure_train = _append_gpr_features(X_train, gpr_train_mean, gpr_train_std)
    structure_test = _append_gpr_features(X_test, gpr_test_mean, gpr_test_std)
    structure_svr = make_pipeline(StandardScaler(), SVR(kernel="rbf", C=24.0, epsilon=3.0, gamma="scale"))
    structure_svr.fit(structure_train, ys_train)
    structure_pred = structure_svr.predict(structure_test)

    function_train = _append_gpr_features(X_train, gpr_train_mean, gpr_train_std)
    function_test = _append_gpr_features(X_test, gpr_test_mean, gpr_test_std)
    function_model = RandomForestRegressor(
        n_estimators=220,
        max_depth=8,
        min_samples_leaf=2,
        random_state=random_state,
    )
    function_model.fit(function_train, yf_train)
    function_pred = function_model.predict(function_test)

    predictions = pd.DataFrame(
        {
            "actualMolecularWeightKda": ys_test.to_numpy(),
            "predictedMolecularWeightKda": structure_pred,
            "actualAkkGrowthScore": yf_test.to_numpy(),
            "predictedAkkGrowthScore": function_pred,
        }
    )

    feature_sensitivity = _feature_sensitivity(dataset, X, y_function)
    return {
        "sampleCount": int(len(dataset)),
        "encodedFeatureColumns": list(X.columns),
        "metrics": {
            "structureModel": _metrics(ys_test, structure_pred),
            "functionModel": _metrics(yf_test, function_pred),
        },
        "predictions": predictions,
        "featureSensitivity": feature_sensitivity,
        "models": {
            "gpr": gpr,
            "structureSvr": structure_svr,
            "functionRandomForest": function_model,
        },
    }


def recommend_process_settings(
    target_product: str,
    current_line_state: dict[str, float],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Recommend conservative R&D process settings for the requested product."""

    anaerobic = float(current_line_state.get("anaerobicScore", 0.8))
    temp = float(current_line_state.get("temperatureC", 37.0))
    ph = float(current_line_state.get("ph", 6.8))

    if "bead" in target_product.lower() or "encapsulated" in target_product.lower():
        carbon_source = "UBFP"
        concentration = "1.00-1.50% in wall-material premix"
        format_hint = "encapsulated-bead"
    elif "fish" in target_product.lower():
        carbon_source = "BFP"
        concentration = "0.50-1.00% in surimi matrix"
        format_hint = "fish-ball"
    elif anaerobic >= 0.78 and abs(temp - 37.0) <= 2.0:
        carbon_source = "lambdaCarrageenan"
        concentration = "1.50-2.00 g/L"
        format_hint = "culture-medium"
    else:
        carbon_source = "BFP"
        concentration = "1.00-2.00 g/L"
        format_hint = "postbiotic-powder"

    function_r2 = evaluation["metrics"]["functionModel"]["r2"]
    confidence = "medium" if function_r2 >= 0.65 and anaerobic >= 0.75 else "low"
    return {
        "label": "研发实验建议",
        "targetProduct": target_product,
        "confidence": confidence,
        "basis": "文献锚点 + 模拟增强数据 + GPR增强SVR结构模型 + 随机森林功能模型",
        "recommendedSettings": {
            "carbonSource": carbon_source,
            "productFormat": format_hint,
            "carbonConcentration": concentration,
            "temperatureC": [36.5, 37.5] if abs(temp - 37.0) <= 2.5 else [36.0, 38.0],
            "ph": [6.6, 7.0] if 6.4 <= ph <= 7.1 else [6.7, 6.9],
            "anaerobicScoreMinimum": 0.85,
            "cultureHours": [48, 72],
            "stirringRpm": [120, 180],
        },
        "risks": [
            "模拟数据不能替代真实批次训练；需要用OD600、qPCR/CFU和SCFAs复核。",
            "Akk相关输出必须作为研发实验建议，不得描述为最终可生产配方。",
            "若ORP/厌氧水平不足，Akk增殖和Amuc-1260相关响应会显著偏移。",
        ],
        "validationIndicators": [
            "OD600 growth curve",
            "Akk qPCR or CFU",
            "acetate/propionate/butyrate by GC-MS",
            "molecular weight distribution",
            "MUC2, ZO-1, Occludin or barrier assay",
        ],
    }


def run_modeling_pipeline(
    output_dir: str | Path = "outputs/modeling",
    random_state: int = 42,
    augmented_rows: int = 180,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    figure_dir = output_path / "figures"
    output_path.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_literature_dataset(random_state=random_state, augmented_rows=augmented_rows)
    evaluation = evaluate_models(dataset, random_state=random_state)
    recommendation = recommend_process_settings(
        "Akk postbiotic freeze-dried powder",
        {"temperatureC": 36.8, "ph": 6.8, "anaerobicScore": 0.86, "stirringRpm": 150, "pressureMpa": 0.1},
        evaluation,
    )

    dataset_path = output_path / "akk_literature_simulated_dataset.csv"
    metrics_path = output_path / "akk_model_metrics.json"
    predictions_path = output_path / "akk_model_predictions.csv"
    report_path = output_path / "AKK_AI建模评估报告.docx"

    dataset.to_csv(dataset_path, index=False, encoding="utf-8-sig")
    evaluation["predictions"].to_csv(predictions_path, index=False, encoding="utf-8-sig")
    serializable_metrics = {
        "sampleCount": evaluation["sampleCount"],
        "metrics": evaluation["metrics"],
        "featureSensitivity": evaluation["featureSensitivity"],
        "recommendation": recommendation,
    }
    metrics_path.write_text(json.dumps(serializable_metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    figure_paths = _save_figures(dataset, evaluation, recommendation, figure_dir)
    _write_docx_report(report_path, dataset, evaluation, recommendation, figure_paths)

    return {
        "datasetPath": str(dataset_path),
        "predictionsPath": str(predictions_path),
        "metricsPath": str(metrics_path),
        "reportPath": str(report_path),
        "figurePaths": [str(path) for path in figure_paths],
    }


def _literature_anchor_rows() -> list[dict[str, Any]]:
    raw_rows = [
        ("BFP", "culture-medium", 0.00, 48, 37.0, 6.8, 0.90, 0.1, 150, 0),
        ("BFP", "culture-medium", 0.25, 48, 37.0, 6.8, 0.90, 0.1, 150, 0),
        ("BFP", "culture-medium", 0.50, 48, 37.0, 6.8, 0.90, 0.1, 150, 0),
        ("BFP", "culture-medium", 1.00, 48, 37.0, 6.8, 0.90, 0.1, 150, 0),
        ("BFP", "culture-medium", 2.00, 60, 37.0, 6.8, 0.92, 0.1, 150, 0),
        ("BFP", "culture-medium", 4.00, 60, 37.0, 6.8, 0.90, 0.1, 150, 0),
        ("lambdaCarrageenan", "culture-medium", 0.125, 72, 37.0, 6.8, 0.93, 0.1, 150, 0),
        ("lambdaCarrageenan", "culture-medium", 2.00, 72, 37.0, 6.8, 0.95, 0.1, 150, 0),
        ("UBFP", "postbiotic-powder", 1.00, 48, 37.0, 6.8, 0.88, 300.0, 150, 1),
        ("UBFP", "postbiotic-powder", 4.00, 48, 37.0, 6.8, 0.88, 300.0, 150, 1),
        ("BFP", "fish-ball", 0.50, 24, 37.0, 6.8, 0.75, 0.1, 180, 0),
        ("BFP", "fish-ball", 1.00, 24, 37.0, 6.8, 0.75, 0.1, 180, 0),
        ("PHP", "fish-ball", 1.00, 24, 37.0, 6.8, 0.75, 0.1, 180, 0),
        ("iotaCarrageenan", "postbiotic-powder", 1.20, 36, 37.0, 6.9, 0.82, 220.0, 170, 1),
    ]
    rng = np.random.default_rng(100)
    return [_with_targets(_row_from_tuple(row), rng, anchor=True) for row in raw_rows]


def _row_from_tuple(values: tuple[Any, ...]) -> dict[str, Any]:
    return dict(zip(FEATURE_COLUMNS, values))


def _with_targets(row: dict[str, Any], rng: np.random.Generator, anchor: bool = False) -> dict[str, Any]:
    source_factor = {
        "BFP": 1.0,
        "UBFP": 1.13,
        "lambdaCarrageenan": 1.18,
        "iotaCarrageenan": 0.82,
        "PHP": 0.92,
        "agar": 0.55,
    }[row["carbonSource"]]
    concentration = float(row["carbonConcentration"])
    optimum = 2.0 if row["productFormat"] != "fish-ball" else 0.85
    dose_effect = math.exp(-((concentration - optimum) ** 2) / (2 * (0.85**2)))
    condition_effect = (
        0.55 * float(row["anaerobicScore"])
        + 0.25 * math.exp(-((float(row["temperatureC"]) - 37.0) ** 2) / 12)
        + 0.20 * math.exp(-((float(row["ph"]) - 6.8) ** 2) / 0.18)
    )
    pretreat_bonus = 8.0 if int(row["pretreated"]) else 0.0
    noise = 0.0 if anchor else float(rng.normal(0, 3.0))

    molecular_weight = (
        78
        - 0.065 * float(row["pressureMpa"])
        - 0.09 * float(row["stirringRpm"] - 150)
        - 9.5 * int(row["pretreated"])
        + {"lambdaCarrageenan": 14, "iotaCarrageenan": 10, "agar": 18, "PHP": -2}.get(row["carbonSource"], 0)
        + (0 if anchor else rng.normal(0, 4.0))
    )
    akk_growth = np.clip(18 + 67 * source_factor * dose_effect * condition_effect + pretreat_bonus + noise, 0, 100)
    scfa = np.clip(12 + 0.66 * akk_growth + 5 * int(row["pretreated"]) - 0.04 * molecular_weight, 0, 100)
    barrier = np.clip(10 + 0.42 * akk_growth + 0.28 * scfa + 4 * int(row["carbonSource"] in {"BFP", "UBFP"}), 0, 100)
    row.update(
        {
            "molecularWeightKda": float(np.clip(molecular_weight, 8, 130)),
            "akkGrowthScore": float(akk_growth),
            "scfaScore": float(scfa),
            "barrierScore": float(barrier),
        }
    )
    return row


def _sample_concentration(rng: np.random.Generator, source: str, product_format: str) -> float:
    if product_format == "fish-ball":
        return float(np.clip(rng.normal(0.8, 0.25), 0.2, 1.3))
    if source == "lambdaCarrageenan":
        return float(np.clip(rng.normal(1.35, 0.55), 0.125, 2.0))
    return float(np.clip(rng.normal(1.8, 1.0), 0.0, 4.0))


def _encode_features(frame: pd.DataFrame) -> pd.DataFrame:
    encoded = pd.get_dummies(frame, columns=["carbonSource", "productFormat"], drop_first=False)
    return encoded.astype(float)


def _append_gpr_features(X: pd.DataFrame, mean: np.ndarray, std: np.ndarray) -> pd.DataFrame:
    enhanced = X.copy()
    enhanced["gprPredictedMolecularWeightKda"] = mean
    enhanced["gprUncertainty"] = std
    return enhanced


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def _feature_sensitivity(dataset: pd.DataFrame, encoded: pd.DataFrame, target: pd.Series) -> list[dict[str, Any]]:
    values = []
    for column in encoded.columns:
        corr = np.corrcoef(encoded[column].to_numpy(), target.to_numpy())[0, 1]
        if np.isnan(corr):
            corr = 0.0
        values.append({"feature": column, "importance": float(abs(corr))})
    return sorted(values, key=lambda item: item["importance"], reverse=True)[:10]


def _save_figures(
    dataset: pd.DataFrame,
    evaluation: dict[str, Any],
    recommendation: dict[str, Any],
    figure_dir: Path,
) -> list[Path]:
    predictions = evaluation["predictions"]
    paths = [
        figure_dir / "01_structure_prediction.png",
        figure_dir / "02_akk_growth_prediction.png",
        figure_dir / "03_dose_response.png",
        figure_dir / "04_feature_sensitivity.png",
        figure_dir / "05_process_recommendation.png",
    ]

    _scatter_plot(
        predictions["actualMolecularWeightKda"],
        predictions["predictedMolecularWeightKda"],
        "Structure model: predicted vs actual",
        "Actual molecular weight (kDa)",
        "Predicted molecular weight (kDa)",
        paths[0],
    )
    _scatter_plot(
        predictions["actualAkkGrowthScore"],
        predictions["predictedAkkGrowthScore"],
        "Function model: predicted vs actual",
        "Actual AKK growth score",
        "Predicted AKK growth score",
        paths[1],
    )
    _dose_response_plot(dataset, paths[2])
    _feature_plot(evaluation["featureSensitivity"], paths[3])
    _recommendation_plot(recommendation, paths[4])
    return paths


def _scatter_plot(actual: pd.Series, predicted: pd.Series, title: str, xlabel: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(7, 5))
    plt.scatter(actual, predicted, color="#247BA0", alpha=0.78, edgecolor="white", linewidth=0.6)
    low = min(float(actual.min()), float(predicted.min()))
    high = max(float(actual.max()), float(predicted.max()))
    plt.plot([low, high], [low, high], color="#D1495B", linewidth=1.8)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _dose_response_plot(dataset: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    for source, color in [("BFP", "#247BA0"), ("lambdaCarrageenan", "#70C1B3"), ("UBFP", "#F25F5C")]:
        subset = dataset[dataset["carbonSource"] == source].sort_values("carbonConcentration")
        plt.scatter(subset["carbonConcentration"], subset["akkGrowthScore"], label=source, alpha=0.45, color=color)
        if len(subset) > 3:
            rolling = subset[["carbonConcentration", "akkGrowthScore"]].rolling(6, min_periods=1).mean()
            plt.plot(rolling["carbonConcentration"], rolling["akkGrowthScore"], color=color, linewidth=2)
    plt.axvline(2.0, color="#444444", linestyle="--", linewidth=1.2, label="2.00 g/L literature focus")
    plt.title("Literature-driven dose response simulation")
    plt.xlabel("Carbon concentration (g/L or % for food matrix)")
    plt.ylabel("AKK growth score")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _feature_plot(feature_sensitivity: list[dict[str, Any]], path: Path) -> None:
    labels = [item["feature"] for item in feature_sensitivity][::-1]
    values = [item["importance"] for item in feature_sensitivity][::-1]
    plt.figure(figsize=(8, 5))
    plt.barh(labels, values, color="#70C1B3")
    plt.title("Feature sensitivity for AKK growth score")
    plt.xlabel("Absolute correlation importance")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _recommendation_plot(recommendation: dict[str, Any], path: Path) -> None:
    settings = recommendation["recommendedSettings"]
    labels = ["temperature", "pH", "anaerobic", "cultureHours", "stirring"]
    values = [
        np.mean(settings["temperatureC"]) / 40,
        np.mean(settings["ph"]) / 7.2,
        settings["anaerobicScoreMinimum"],
        np.mean(settings["cultureHours"]) / 72,
        np.mean(settings["stirringRpm"]) / 220,
    ]
    plt.figure(figsize=(7, 5))
    plt.bar(labels, values, color=["#247BA0", "#70C1B3", "#B2DBBF", "#F3FFBD", "#FF9F1C"])
    plt.ylim(0, 1.1)
    plt.title("Normalized recommended process levels")
    plt.ylabel("Normalized level")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _write_docx_report(
    report_path: Path,
    dataset: pd.DataFrame,
    evaluation: dict[str, Any],
    recommendation: dict[str, Any],
    figure_paths: list[Path],
) -> None:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    title = doc.add_paragraph()
    run = title.add_run("AKK菌产物配方与产线调控AI建模评估报告")
    run.bold = True
    run.font.size = Pt(20)
    doc.add_paragraph("报告性质：研发实验建议。当前结果基于文献锚点与模拟增强数据，不代表最终生产配方。")

    doc.add_heading("1. 建模目标", level=1)
    doc.add_paragraph(
        "本报告将创新点附件中的论文和专利参数转化为第一版可运行建模闭环："
        "多糖工艺-结构预测、Akk功能响应预测、产线参数推荐与风险提示。"
    )

    doc.add_heading("2. 数据来源与样本", level=1)
    doc.add_paragraph(
        f"本次生成样本数为 {len(dataset)} 条，其中包含文献锚点和围绕文献条件生成的模拟增强样本。"
        "锚点覆盖BFP、UBFP、lambdaCarrageenan、PHP、iotaCarrageenan等碳源，以及培养基、鱼丸、冻干粉和包埋体系。"
    )

    doc.add_heading("3. 模型评估", level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["模型", "RMSE", "MAE", "R2"]
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    for model_name, metrics in evaluation["metrics"].items():
        row = table.add_row().cells
        row[0].text = model_name
        row[1].text = f"{metrics['rmse']:.3f}"
        row[2].text = f"{metrics['mae']:.3f}"
        row[3].text = f"{metrics['r2']:.3f}"

    doc.add_heading("4. 评估图表", level=1)
    for figure_path in figure_paths:
        doc.add_paragraph(figure_path.stem)
        doc.add_picture(str(figure_path), width=Inches(6.2))

    doc.add_heading("5. 产线调控建议", level=1)
    doc.add_paragraph(f"目标产品：{recommendation['targetProduct']}")
    doc.add_paragraph(f"置信度：{recommendation['confidence']}")
    doc.add_paragraph(f"推荐碳源：{recommendation['recommendedSettings']['carbonSource']}")
    doc.add_paragraph(f"推荐浓度：{recommendation['recommendedSettings']['carbonConcentration']}")
    doc.add_paragraph("推荐工艺范围：")
    for key, value in recommendation["recommendedSettings"].items():
        doc.add_paragraph(f"{key}: {value}", style=None)

    doc.add_heading("6. 风险与验证指标", level=1)
    doc.add_paragraph("风险提示：")
    for risk in recommendation["risks"]:
        doc.add_paragraph(risk, style=None)
    doc.add_paragraph("必须验证的实验指标：")
    for indicator in recommendation["validationIndicators"]:
        doc.add_paragraph(indicator, style=None)

    doc.add_heading("7. 下一步", level=1)
    doc.add_paragraph(
        "建议将真实小试批次数据按同一字段结构追加到CSV中，重新运行脚本。"
        "当真实批次数达到30-50条时，可开始替换模拟增强样本；达到100条以上后，再考虑多目标贝叶斯优化。"
    )
    doc.save(report_path)
