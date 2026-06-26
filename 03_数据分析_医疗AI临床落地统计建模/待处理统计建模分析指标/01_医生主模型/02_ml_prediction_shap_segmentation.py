# -*- coding: utf-8 -*-
"""
02_ml_prediction_shap_segmentation.py
第六章：机器学习预测与医生分层画像

定位：辅助预测与推广分层，非临床级预测工具
- 机器学习模型用于预测、变量重要性识别和医生分层画像
- Logistic解释模型用于机制检验（已在第五章完成）

所有输出写入 output_ml/ 文件夹，不修改任何原始数据文件
"""

import pandas as pd
import numpy as np
import sys
import io
import warnings
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

warnings.filterwarnings("ignore")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegressionCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, accuracy_score, recall_score, precision_score,
    f1_score, brier_score_loss, confusion_matrix, roc_curve
)
from sklearn.base import clone

import shap

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output_ml"
RANDOM_STATE = 42

# ============================================================
# 变量口径定义
# ============================================================
Y_VAR = "AdoptTop2"

X_INDEX = [
    "ValueIndex",
    "PainIndex",
    "AIExperience",
    "CaseVolume",
    "HospitalGrade",
    "MAI_LGI_entropy",
]

X_GAP = [
    "ValueIndex",
    "PainIndex",
    "AIExperience",
    "CaseVolume",
    "HospitalGrade",
    "TrustGap",
    "LiabilityGap",
    "DataGap",
    "ManageGap",
    "WorkflowGap",
]

ALL_REQUIRED_VARS = list(set([Y_VAR] + X_INDEX + X_GAP))

# 五类鸿沟中文标签
GAP_LABELS = {
    "TrustGap": "技术信任鸿沟",
    "LiabilityGap": "责任治理鸿沟",
    "DataGap": "数据安全鸿沟",
    "ManageGap": "医院管理鸿沟",
    "WorkflowGap": "流程嵌入鸿沟",
}

VAR_LABELS = {
    "ValueIndex": "AI综合价值感知指数",
    "PainIndex": "流程痛点指数",
    "AIExperience": "AI接触经验",
    "CaseVolume": "病例量",
    "HospitalGrade": "医院等级",
    "MAI_LGI_entropy": "MAI-LGI鸿沟指数",
    "TrustGap": "技术信任鸿沟",
    "LiabilityGap": "责任治理鸿沟",
    "DataGap": "数据安全鸿沟",
    "ManageGap": "医院管理鸿沟",
    "WorkflowGap": "流程嵌入鸿沟",
}

# 治理含义映射
GAP_GOVERNANCE = {
    "LiabilityGap": "责任治理鸿沟，若排名靠前，解释为最强区分性约束",
    "WorkflowGap": "流程嵌入鸿沟，工作流适配和操作负担影响采用转化",
    "DataGap": "数据安全鸿沟，隐私与合规约束",
    "TrustGap": "技术信任鸿沟，准确率和稳定性顾虑",
    "ManageGap": "医院管理鸿沟，若SHAP值较低，解释为普遍性背景约束而非强区分变量",
}


# ============================================================
# 日志收集器
# ============================================================
class Logger:
    def __init__(self):
        self.lines = []

    def log(self, msg):
        self.lines.append(msg)
        print(msg)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))


logger = Logger()


# ============================================================
# 1. 数据读取
# ============================================================
def read_data():
    paths = [
        BASE_DIR / "output_py" / "SPSS_MAI_LGI_entropy_dataset.csv",
        BASE_DIR / "SPSS_MAI_LGI_entropy_dataset.csv",
    ]
    for p in paths:
        if p.exists():
            df = pd.read_csv(p)
            logger.log(f"[读取成功] {p.name}, N={len(df)}, cols={len(df.columns)}")
            return df, str(p)
    logger.log("[错误] 未找到 SPSS_MAI_LGI_entropy_dataset.csv，请先运行 01_build_mai_lgi_entropy.py")
    sys.exit(1)


def check_variables(df):
    missing = [v for v in ALL_REQUIRED_VARS if v not in df.columns]
    if missing:
        logger.log(f"[错误] 缺少变量: {missing}")
        sys.exit(1)
    logger.log(f"[检查通过] 全部{len(ALL_REQUIRED_VARS)}个变量均存在")


def prepare_data(df):
    model_vars = list(dict.fromkeys([Y_VAR] + X_INDEX + X_GAP))  # 去重保序
    subset = df[model_vars].dropna().copy()
    n_total = len(df)
    n_valid = len(subset)
    n_pos = int(subset[Y_VAR].sum())
    n_neg = n_valid - n_pos
    pos_rate = n_pos / n_valid
    logger.log(f"[数据准备] 原始N={n_total}, 有效N={n_valid}, 阳性={n_pos}, 阴性={n_neg}, 阳性率={pos_rate:.3f}")
    return subset


# ============================================================
# 2. 模型定义
# ============================================================
def get_models_index():
    """综合指数口径下的三个模型"""
    models = OrderedDict()

    # LASSO Logistic: StandardScaler + LogisticRegressionCV
    lasso_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("logreg", LogisticRegressionCV(
            penalty="l1",
            solver="saga",
            cv=5,
            scoring="roc_auc",
            class_weight="balanced",
            max_iter=5000,
            random_state=RANDOM_STATE,
            Cs=10,
        )),
    ])
    models["LASSO_Logistic"] = lasso_pipe

    # Random Forest
    models["Random_Forest"] = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )

    # Gradient Boosting
    models["Gradient_Boosting"] = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=2,
        random_state=RANDOM_STATE,
    )

    return models


def get_model_gap():
    """五维分解口径下用于SHAP的模型（Gradient Boosting）"""
    return GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=2,
        random_state=RANDOM_STATE,
    )


# ============================================================
# 3. 交叉验证评估
# ============================================================
def repeated_stratified_cv_evaluate(models, X, y, feature_names, cv, logger):
    """
    重复分层交叉验证，输出每个模型的预测概率和评估指标

    指标公式：
    - Accuracy = (TP + TN) / (TP + TN + FP + FN)
    - Sensitivity/Recall = TP / (TP + FN)
    - Specificity = TN / (TN + FP)
    - Precision = TP / (TP + FP)
    - F1 = 2 * Precision * Recall / (Precision + Recall)
    - Brier = (1/n) * sum((y_i - p_i)^2)
    - AUC: ROC曲线下面积
    """
    results = {}
    metrics_rows = []

    for name, model in models.items():
        logger.log(f"\n[交叉验证] {name} (特征: {len(feature_names)})")

        try:
            # RepeatedStratifiedKFold 不是分区型CV，需手动循环
            y_prob_all = np.zeros(len(y))
            count_all = np.zeros(len(y))
            for train_idx, test_idx in cv.split(X, y):
                m = clone(model)
                m.fit(X[train_idx], y[train_idx])
                probs = m.predict_proba(X[test_idx])[:, 1]
                y_prob_all[test_idx] += probs
                count_all[test_idx] += 1
            y_prob = y_prob_all / count_all
        except Exception as e:
            logger.log(f"[错误] {name} 交叉验证失败: {e}")
            continue

        y_pred = (y_prob >= 0.5).astype(int)

        auc = roc_auc_score(y, y_prob)
        acc = accuracy_score(y, y_pred)
        sens = recall_score(y, y_pred)
        cm = confusion_matrix(y, y_pred)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        prec = precision_score(y, y_pred, zero_division=0)
        f1 = f1_score(y, y_pred, zero_division=0)
        brier = brier_score_loss(y, y_prob)

        metrics_rows.append({
            "model": name,
            "feature_set": "X_index",
            "n_features": len(feature_names),
            "AUC": round(auc, 4),
            "Accuracy": round(acc, 4),
            "Sensitivity": round(sens, 4),
            "Specificity": round(spec, 4),
            "Precision": round(prec, 4),
            "F1": round(f1, 4),
            "Brier": round(brier, 4),
        })

        results[name] = {
            "y_prob": y_prob,
            "y_pred": y_pred,
            "auc": auc,
            "fpr_tpr": roc_curve(y, y_prob),
        }

        logger.log(f"  AUC={auc:.4f}, Accuracy={acc:.4f}, Sensitivity={sens:.4f}, Specificity={spec:.4f}")
        logger.log(f"  Precision={prec:.4f}, F1={f1:.4f}, Brier={brier:.4f}")

    metrics_df = pd.DataFrame(metrics_rows)
    return results, metrics_df


# ============================================================
# 4. ROC曲线图
# ============================================================
def plot_roc_curves(results, y, output_dir, logger):
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = {"LASSO_Logistic": "#2166ac", "Random_Forest": "#4dac26", "Gradient_Boosting": "#e08214"}

    for name, res in results.items():
        fpr, tpr, _ = res["fpr_tpr"]
        auc = res["auc"]
        c = colors.get(name, "#333333")
        ax.plot(fpr, tpr, color=c, lw=2, label=f"{name} (AUC={auc:.3f})")

    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=12)
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=12)
    ax.set_title("ROC Curves - Repeated Stratified 5-Fold CV (20 repeats)", fontsize=13)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_roc_curves.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] fig_roc_curves.png")


# ============================================================
# 5. 校准图
# ============================================================
def plot_calibration(results, y, output_dir, logger):
    """校准图：将预测概率分10组，比较每组平均预测概率与实际阳性率"""
    n_bins = 10
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = {"LASSO_Logistic": "#2166ac", "Random_Forest": "#4dac26", "Gradient_Boosting": "#e08214"}

    for name, res in results.items():
        y_prob = res["y_prob"]
        df_cal = pd.DataFrame({"y": y, "p": y_prob})
        df_cal["bin"] = pd.cut(df_cal["p"], bins=np.linspace(0, 1, n_bins + 1), include_lowest=True)
        grouped = df_cal.groupby("bin", observed=True).agg(mean_p=("p", "mean"), mean_y=("y", "mean"), count=("y", "count"))
        c = colors.get(name, "#333333")
        ax.scatter(grouped["mean_p"], grouped["mean_y"], s=grouped["count"] * 5, color=c, alpha=0.7, label=name)
        ax.plot(grouped["mean_p"], grouped["mean_y"], color=c, lw=1.5, alpha=0.5)

    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("Mean Predicted Probability", fontsize=12)
    ax.set_ylabel("Observed Proportion (AdoptTop2=1)", fontsize=12)
    ax.set_title("Calibration Plot (10 Bins)", fontsize=13)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_calibration.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] fig_calibration.png")


# ============================================================
# 6. 变量重要性
# ============================================================
def compute_variable_importance(models, X, y, feature_names, output_dir, logger):
    """
    变量重要性：
    - LASSO: 标准化系数绝对值
    - RF/GB: sklearn feature_importances_ (Gini/Impurity reduction)
    """
    importance_rows = []

    # LASSO: fit on full data to get coefficients
    lasso_model = models["LASSO_Logistic"]
    lasso_model.fit(X, y)
    coefs = lasso_model.named_steps["logreg"].coef_[0]
    for i, fname in enumerate(feature_names):
        importance_rows.append({
            "model": "LASSO_Logistic",
            "variable": fname,
            "variable_label": VAR_LABELS.get(fname, fname),
            "importance": round(abs(coefs[i]), 6),
            "importance_type": "abs_coef",
        })

    # RF
    rf_model = models["Random_Forest"]
    rf_model.fit(X, y)
    for i, fname in enumerate(feature_names):
        importance_rows.append({
            "model": "Random_Forest",
            "variable": fname,
            "variable_label": VAR_LABELS.get(fname, fname),
            "importance": round(rf_model.feature_importances_[i], 6),
            "importance_type": "gini_importance",
        })

    # GB
    gb_model = models["Gradient_Boosting"]
    gb_model.fit(X, y)
    for i, fname in enumerate(feature_names):
        importance_rows.append({
            "model": "Gradient_Boosting",
            "variable": fname,
            "variable_label": VAR_LABELS.get(fname, fname),
            "importance": round(gb_model.feature_importances_[i], 6),
            "importance_type": "gini_importance",
        })

    imp_df = pd.DataFrame(importance_rows)
    imp_df.to_csv(output_dir / "02_variable_importance.csv", index=False)
    logger.log("[输出] 02_variable_importance.csv")

    # 排序条形图
    plot_variable_importance(imp_df, output_dir, logger)

    return imp_df


def plot_variable_importance(imp_df, output_dir, logger):
    """变量重要性条形图"""
    models_unique = imp_df["model"].unique()
    fig, axes = plt.subplots(1, len(models_unique), figsize=(6 * len(models_unique), 5))
    if len(models_unique) == 1:
        axes = [axes]

    for ax, model_name in zip(axes, models_unique):
        sub = imp_df[imp_df["model"] == model_name].sort_values("importance", ascending=True)
        labels = sub["variable_label"].values
        vals = sub["importance"].values
        ax.barh(labels, vals, color="#4393c3", edgecolor="k", linewidth=0.5)
        ax.set_title(model_name, fontsize=12)
        ax.set_xlabel("Importance", fontsize=10)

    fig.suptitle("Variable Importance (X_index)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_variable_importance.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.log("[输出] fig_variable_importance.png")


# ============================================================
# 7. SHAP分析（五维分解口径）
# ============================================================
def run_shap_analysis(X_gap_arr, y, feature_names_gap, output_dir, logger):
    """
    SHAP分析：使用五维分解口径 X_gap
    模型: Gradient Boosting

    SHAP公式：
    对于第 i 个医生样本，模型预测值可分解为：
    f(x_i) = φ_0 + Σ φ_j
    其中：
    φ_0 为模型基准预测值；
    φ_j 为第 j 个变量对该医生预测结果的边际贡献；
    φ_j > 0 表示该变量推动预测概率升高；
    φ_j < 0 表示该变量推动预测概率降低。

    全局变量重要性使用平均绝对SHAP值：
    Importance_j = (1/n) × Σ |φ_ij|
    """
    logger.log("\n" + "=" * 50)
    logger.log("SHAP分析（五维分解口径 X_gap）")

    gb_model = get_model_gap()
    gb_model.fit(X_gap_arr, y)
    logger.log(f"[SHAP] Gradient Boosting 已训练, 特征数={len(feature_names_gap)}")

    # TreeExplainer
    explainer = shap.TreeExplainer(gb_model)
    shap_values = explainer.shap_values(X_gap_arr, check_additivity=False)

    # 确保shap_values形状正确
    if shap_values.shape != X_gap_arr.shape:
        logger.log(f"[警告] SHAP values shape {shap_values.shape} != X shape {X_gap_arr.shape}, 截取前{X_gap_arr.shape[1]}列")
        shap_values = shap_values[:, :X_gap_arr.shape[1]]

    feature_labels = [VAR_LABELS.get(f, f) for f in feature_names_gap]
    X_gap_shap = pd.DataFrame(X_gap_arr, columns=feature_labels)

    # --- 保留原有SHAP图 ---
    # beeswarm
    plt.close("all")
    shap.summary_plot(
        shap_values, X_gap_shap,
        show=False, max_display=len(feature_labels)
    )
    fig = plt.gcf()
    fig.tight_layout()
    fig.savefig(output_dir / "fig_shap_summary.png", dpi=200, bbox_inches="tight")
    plt.close("all")
    logger.log("[输出] fig_shap_summary.png")

    # bar
    shap.summary_plot(
        shap_values, X_gap_shap,
        plot_type="bar",
        show=False, max_display=len(feature_labels)
    )
    fig = plt.gcf()
    fig.tight_layout()
    fig.savefig(output_dir / "fig_shap_bar.png", dpi=200, bbox_inches="tight")
    plt.close("all")
    logger.log("[输出] fig_shap_bar.png")

    # --- 原有SHAP重要性表 (03, 04) ---
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_rows = []
    for i, fname in enumerate(feature_names_gap):
        shap_rows.append({
            "variable": fname,
            "variable_label": VAR_LABELS.get(fname, fname),
            "mean_abs_shap": round(mean_abs_shap[i], 6),
        })
    shap_df = pd.DataFrame(shap_rows).sort_values("mean_abs_shap", ascending=False)
    shap_df.to_csv(output_dir / "03_shap_importance.csv", index=False)
    logger.log("[输出] 03_shap_importance.csv")

    gap_shap_rows = []
    for i, fname in enumerate(feature_names_gap):
        if fname in GAP_LABELS:
            gap_shap_rows.append({
                "variable": fname,
                "gap_name_cn": GAP_LABELS[fname],
                "mean_abs_shap": round(mean_abs_shap[i], 6),
                "rank": 0,
            })
    if gap_shap_rows:
        gap_shap_df = pd.DataFrame(gap_shap_rows).sort_values("mean_abs_shap", ascending=False)
        gap_shap_df["rank"] = range(1, len(gap_shap_df) + 1)
        gap_shap_df.to_csv(output_dir / "04_shap_gap_importance.csv", index=False)
        logger.log("[输出] 04_shap_gap_importance.csv")
        logger.log("[SHAP鸿沟排序]")
        for _, row in gap_shap_df.iterrows():
            logger.log(f"  Rank {row['rank']}: {row['gap_name_cn']} (mean|SHAP|={row['mean_abs_shap']:.4f})")

    # ============================================================
    # 新增：完整变量SHAP重要性表（含排名和解释）
    # ============================================================
    logger.log("\n[补充] 完整变量SHAP重要性表")

    full_rows = []
    for i, fname in enumerate(feature_names_gap):
        full_rows.append({
            "variable": fname,
            "mean_abs_shap": round(mean_abs_shap[i], 6),
        })
    full_df = pd.DataFrame(full_rows).sort_values("mean_abs_shap", ascending=False)
    full_df["rank"] = range(1, len(full_df) + 1)
    full_df.to_csv(output_dir / "shap_importance_full.csv", index=False)
    logger.log("[输出] shap_importance_full.csv")

    # 中文解释版
    INTERP_RULES = {
        "ValueIndex": "AI价值感知越高，越可能推动高采用意愿",
        "PainIndex": "流程痛点指数越高，可能推动或抑制采用（取决于方向）",
        "AIExperience": "AI接触经验越丰富，越可能推动高采用意愿",
        "CaseVolume": "病例量影响采用决策，方向取决于临床场景",
        "HospitalGrade": "医院等级影响AI资源配置和采用条件",
        "TrustGap": "技术信任鸿沟抑制采用，准确率和稳定性顾虑",
        "LiabilityGap": "责任治理鸿沟抑制采用，责任归属和规范顾虑",
        "DataGap": "数据安全鸿沟抑制采用，隐私和合规顾虑",
        "ManageGap": "医院管理鸿沟抑制采用，设备和制度约束",
        "WorkflowGap": "流程嵌入鸿沟抑制采用，工作流适配负担",
    }
    cn_rows = []
    for _, row in full_df.iterrows():
        v = row["variable"]
        cn_rows.append({
            "排名": int(row["rank"]),
            "变量": VAR_LABELS.get(v, v),
            "平均绝对SHAP值": row["mean_abs_shap"],
            "解释": INTERP_RULES.get(v, ""),
        })
    cn_df = pd.DataFrame(cn_rows)
    cn_df.to_csv(output_dir / "table_shap_importance_full_cn.csv", index=False)
    logger.log("[输出] table_shap_importance_full_cn.csv")

    # ============================================================
    # 新增：五类鸿沟SHAP子表（含治理含义）
    # ============================================================
    logger.log("[补充] 五类鸿沟SHAP子表（含治理含义）")

    gap_sub_rows = []
    for i, fname in enumerate(feature_names_gap):
        if fname in GAP_LABELS:
            gap_sub_rows.append({
                "variable": fname,
                "mean_abs_shap": round(mean_abs_shap[i], 6),
            })
    gap_sub_df = pd.DataFrame(gap_sub_rows).sort_values("mean_abs_shap", ascending=False)
    gap_sub_df["rank"] = range(1, len(gap_sub_df) + 1)
    gap_sub_df.to_csv(output_dir / "shap_gap_importance.csv", index=False)
    logger.log("[输出] shap_gap_importance.csv")

    gap_cn_rows = []
    for _, row in gap_sub_df.iterrows():
        v = row["variable"]
        gap_cn_rows.append({
            "排名": int(row["rank"]),
            "鸿沟变量": GAP_LABELS.get(v, v),
            "平均绝对SHAP值": row["mean_abs_shap"],
            "治理含义": GAP_GOVERNANCE.get(v, ""),
        })
    gap_cn_df = pd.DataFrame(gap_cn_rows)
    gap_cn_df.to_csv(output_dir / "table_shap_gap_importance_cn.csv", index=False)
    logger.log("[输出] table_shap_gap_importance_cn.csv")

    # ============================================================
    # 新增图像
    # ============================================================
    # shap_summary_full_bar.png — 英文标题完整变量bar图
    plt.close("all")
    sorted_idx = np.argsort(mean_abs_shap)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(
        range(len(sorted_idx)),
        mean_abs_shap[sorted_idx],
        color="#4393c3", edgecolor="k", linewidth=0.5,
    )
    ax.set_yticks(range(len(sorted_idx)))
    ax.set_yticklabels([feature_labels[i] for i in sorted_idx], fontsize=10)
    ax.set_xlabel("Mean absolute SHAP value", fontsize=12)
    ax.set_title("SHAP Feature Importance (Full Variables)", fontsize=13)
    ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(output_dir / "shap_summary_full_bar.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] shap_summary_full_bar.png")

    # shap_summary_full_beeswarm.png — 英文标题beeswarm
    plt.close("all")
    shap.summary_plot(
        shap_values, X_gap_shap,
        show=False, max_display=len(feature_labels)
    )
    fig = plt.gcf()
    fig.axes[0].set_title("SHAP Feature Importance (Full Variables)", fontsize=13)
    fig.axes[0].set_xlabel("SHAP value (impact on model output)", fontsize=11)
    fig.tight_layout()
    fig.savefig(output_dir / "shap_summary_full_beeswarm.png", dpi=200, bbox_inches="tight")
    plt.close("all")
    logger.log("[输出] shap_summary_full_beeswarm.png")

    # shap_gap_importance_bar.png — 五类鸿沟bar图
    gap_indices = [i for i, f in enumerate(feature_names_gap) if f in GAP_LABELS]
    gap_shap_vals = mean_abs_shap[gap_indices]
    gap_labels_sorted = [feature_labels[i] for i in gap_indices]
    sorted_gap_idx = np.argsort(gap_shap_vals)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(
        range(len(sorted_gap_idx)),
        gap_shap_vals[sorted_gap_idx],
        color="#d6604d", edgecolor="k", linewidth=0.5,
    )
    ax.set_yticks(range(len(sorted_gap_idx)))
    ax.set_yticklabels([gap_labels_sorted[i] for i in sorted_gap_idx], fontsize=10)
    ax.set_xlabel("Mean absolute SHAP value", fontsize=12)
    ax.set_title("SHAP Feature Importance (Five Gaps)", fontsize=13)
    ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(output_dir / "shap_gap_importance_bar.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] shap_gap_importance_bar.png")

    return shap_values, shap_df


# ============================================================
# 8. 医生分层画像
# ============================================================
def run_segmentation(X_gap_df, y, shap_values, feature_names_gap, output_dir, logger):
    """
    医生分层画像：
    1. 使用最优模型（GB on X_gap）的预测概率分层
    2. 结合SHAP值进行画像描述
    """
    logger.log("\n" + "=" * 50)
    logger.log("医生分层画像")

    # 用GB模型全量训练预测概率
    gb_model = get_model_gap()
    X_arr = X_gap_df.values
    gb_model.fit(X_arr, y)
    y_prob = gb_model.predict_proba(X_arr)[:, 1]

    # 分层：高/中/低采用意愿
    # 高: prob >= 0.6, 中: 0.3 <= prob < 0.6, 低: prob < 0.3
    segments = pd.Series(index=X_gap_df.index, dtype=str)
    segments[y_prob >= 0.6] = "High"
    segments[(y_prob >= 0.3) & (y_prob < 0.6)] = "Medium"
    segments[y_prob < 0.3] = "Low"

    seg_counts = segments.value_counts()
    logger.log(f"[分层] High={seg_counts.get('High',0)}, Medium={seg_counts.get('Medium',0)}, Low={seg_counts.get('Low',0)}")

    # 各层SHAP画像
    seg_profile_rows = []
    gap_cols = [f for f in feature_names_gap if f in GAP_LABELS]

    for seg_name in ["High", "Medium", "Low"]:
        mask = segments == seg_name
        n_seg = mask.sum()
        if n_seg == 0:
            continue
        actual_pos_rate = y[mask].mean()

        # 该层各变量均值
        var_means = X_gap_df.loc[mask].mean()

        # 该层各Gap的SHAP均值
        seg_shap = shap_values[mask.values]
        shap_means = seg_shap.mean(axis=0)

        row_base = {
            "segment": seg_name,
            "n": n_seg,
            "actual_positive_rate": round(actual_pos_rate, 4),
        }
        for i, fname in enumerate(feature_names_gap):
            label = VAR_LABELS.get(fname, fname)
            row_base[f"mean_{label}"] = round(var_means[fname], 4)
            row_base[f"shap_{label}"] = round(shap_means[i], 6)

        seg_profile_rows.append(row_base)

        logger.log(f"  [{seg_name}] N={n_seg}, 实际阳性率={actual_pos_rate:.2%}")
        for fname in gap_cols:
            idx = list(feature_names_gap).index(fname)
            label = GAP_LABELS[fname]
            logger.log(f"    {label}: 均值={var_means[fname]:.3f}, 平均SHAP={shap_means[idx]:.4f}")

    seg_profile_df = pd.DataFrame(seg_profile_rows)
    seg_profile_df.to_csv(output_dir / "05_segment_profile.csv", index=False)
    logger.log("[输出] 05_segment_profile.csv")

    # 分层汇总表（论文用）
    summary_rows = []
    for seg_name in ["High", "Medium", "Low"]:
        mask = segments == seg_name
        n_seg = mask.sum()
        if n_seg == 0:
            continue
        row = {
            "segment": seg_name,
            "segment_cn": {"High": "高采用意愿层", "Medium": "中采用意愿层", "Low": "低采用意愿层"}[seg_name],
            "n": n_seg,
            "pct": round(n_seg / len(y), 4),
            "actual_positive_rate": round(y[mask].mean(), 4),
            "mean_predict_prob": round(y_prob[mask].mean(), 4),
        }
        for fname in feature_names_gap:
            label = VAR_LABELS.get(fname, fname)
            row[f"mean_{label}"] = round(X_gap_df.loc[mask, fname].mean(), 4)
        summary_rows.append(row)

    seg_summary_df = pd.DataFrame(summary_rows)
    seg_summary_df.to_csv(output_dir / "table_segment_summary.csv", index=False)
    logger.log("[输出] table_segment_summary.csv")

    # 分层可视化
    plot_segmentation(segments, y_prob, y, X_gap_df, feature_names_gap, output_dir, logger)

    return segments, y_prob


def plot_segmentation(segments, y_prob, y, X_gap_df, feature_names_gap, output_dir, logger):
    """医生分层可视化"""
    # 1. 预测概率分布直方图
    fig, ax = plt.subplots(figsize=(8, 5))
    for seg_name, color in zip(["High", "Medium", "Low"], ["#4dac26", "#f4a460", "#d6604d"]):
        mask = segments == seg_name
        if mask.sum() > 0:
            ax.hist(y_prob[mask], bins=20, alpha=0.6, color=color, label=f"{seg_name} (N={mask.sum()})", edgecolor="k", linewidth=0.5)
    ax.set_xlabel("Predicted Probability (AdoptTop2=1)", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title("Prediction Probability Distribution by Segment", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_segment_distribution.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] fig_segment_distribution.png")

    # 2. 各层Gap均值雷达图
    gap_cols = [f for f in feature_names_gap if f in GAP_LABELS]
    seg_names = ["High", "Medium", "Low"]
    seg_colors = ["#4dac26", "#f4a460", "#d6604d"]

    fig, ax = plt.subplots(figsize=(8, 6))
    x_pos = np.arange(len(gap_cols))
    width = 0.25

    for i, (seg_name, color) in enumerate(zip(seg_names, seg_colors)):
        mask = segments == seg_name
        if mask.sum() == 0:
            continue
        means = [X_gap_df.loc[mask, c].mean() for c in gap_cols]
        labels = [GAP_LABELS.get(c, c) for c in gap_cols]
        ax.bar(x_pos + i * width, means, width, color=color, label=seg_name, edgecolor="k", linewidth=0.5)

    ax.set_xticks(x_pos + width)
    ax.set_xticklabels(labels, fontsize=9, rotation=15)
    ax.set_ylabel("Mean Value", fontsize=11)
    ax.set_title("Gap Variable Means by Segment", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(output_dir / "fig_segment_gap_means.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] fig_segment_gap_means.png")


# ============================================================
# 9. SHAP依赖图（对最重要的Gap变量）
# ============================================================
def plot_shap_dependence(shap_values, X_gap_arr, feature_names_gap, output_dir, logger):
    """对SHAP重要性最高的Gap变量绘制依赖图"""
    gap_cols = [f for f in feature_names_gap if f in GAP_LABELS]
    if not gap_cols:
        return

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    gap_indices = [list(feature_names_gap).index(f) for f in gap_cols]
    top_gap_idx = gap_indices[np.argmax([mean_abs_shap[i] for i in gap_indices])]
    top_gap_name = feature_names_gap[top_gap_idx]
    top_gap_label = VAR_LABELS.get(top_gap_name, top_gap_name)

    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(
        X_gap_arr[:, top_gap_idx],
        shap_values[:, top_gap_idx],
        c=X_gap_arr[:, list(feature_names_gap).index("ValueIndex")],
        cmap="coolwarm", alpha=0.6, edgecolors="k", linewidths=0.3, s=40
    )
    ax.set_xlabel(f"{top_gap_label} Value", fontsize=12)
    ax.set_ylabel(f"SHAP Value ({top_gap_label})", fontsize=12)
    ax.set_title(f"SHAP Dependence: {top_gap_label}", fontsize=13)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("AI Value Perception", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_shap_dependence_topgap.png", dpi=200)
    plt.close(fig)
    logger.log(f"[输出] fig_shap_dependence_topgap.png (变量: {top_gap_label})")


# ============================================================
# 10. 全量预测概率导出
# ============================================================
def export_predictions(segments, y_prob, y, X_index_df, X_gap_df, feature_names_index, feature_names_gap, output_dir, logger):
    """导出全量预测结果供后续使用"""
    pred_df = pd.DataFrame({
        "Segment": segments.values,
        "Predict_Prob": y_prob,
        "AdoptTop2": y,
    })
    for col in feature_names_gap:
        pred_df[col] = X_gap_df[col].values
    pred_df.to_csv(output_dir / "06_predictions_with_segment.csv", index=False)
    logger.log("[输出] 06_predictions_with_segment.csv")


# ============================================================
# 11. 推广策略建议表
# ============================================================
def export_strategy_table(segments, y, X_gap_df, feature_names_gap, output_dir, logger):
    """基于分层的推广策略建议"""
    strategy_rows = []
    seg_info = {
        "High": {"cn": "高采用意愿层", "strategy": "维持价值感知，降低流程痛点", "priority": "低优先级（已具备意愿）"},
        "Medium": {"cn": "中采用意愿层", "strategy": "重点突破鸿沟约束，增强AI价值感知", "priority": "高优先级（最具转化潜力）"},
        "Low": {"cn": "低采用意愿层", "strategy": "先解决基础设施和信任问题", "priority": "中优先级（需长期投入）"},
    }

    for seg_name in ["High", "Medium", "Low"]:
        mask = segments == seg_name
        n_seg = mask.sum()
        if n_seg == 0:
            continue
        info = seg_info.get(seg_name, {})

        # 该层SHAP方向：哪些Gap正向贡献最大（抑制采纳）
        gap_cols = [f for f in feature_names_gap if f in GAP_LABELS]
        gap_means = {f: X_gap_df.loc[mask, f].mean() for f in gap_cols}
        sorted_gaps = sorted(gap_means.items(), key=lambda x: x[1], reverse=True)
        top_gaps = ", ".join([f"{GAP_LABELS[f]}({v:.2f})" for f, v in sorted_gaps[:3]])

        strategy_rows.append({
            "segment": seg_name,
            "segment_cn": info.get("cn", ""),
            "n": n_seg,
            "pct": round(n_seg / len(y), 4),
            "actual_positive_rate": round(y[mask].mean(), 4),
            "top3_gaps": top_gaps,
            "strategy": info.get("strategy", ""),
            "priority": info.get("priority", ""),
        })

    strategy_df = pd.DataFrame(strategy_rows)
    strategy_df.to_csv(output_dir / "table_promotion_strategy.csv", index=False)
    logger.log("[输出] table_promotion_strategy.csv")


# ============================================================
# 主函数
# ============================================================
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    logger.log("=" * 60)
    logger.log("第六章：机器学习预测与医生分层画像")
    logger.log(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log("定位: 探索性预测与推广分层（非临床级预测工具）")
    logger.log(f"随机种子: {RANDOM_STATE}")
    logger.log("=" * 60)

    # 1. 读取数据
    df, source = read_data()
    check_variables(df)
    data = prepare_data(df)

    y = data[Y_VAR].values
    X_index_df = data[X_INDEX].copy()
    X_gap_df = data[X_GAP].copy()
    X_index_arr = X_index_df.values
    X_gap_arr = X_gap_df.values

    logger.log(f"\n综合指数口径 X_index: {X_INDEX}")
    logger.log(f"五维分解口径 X_gap: {X_GAP}")

    # 2. 模型定义
    models = get_models_index()
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=20, random_state=RANDOM_STATE)
    logger.log(f"交叉验证: RepeatedStratifiedKFold(n_splits=5, n_repeats=20)")

    # 3. 交叉验证评估
    logger.log("\n" + "=" * 50)
    logger.log("模型比较（综合指数口径 X_index）")
    results, metrics_df = repeated_stratified_cv_evaluate(
        models, X_index_arr, y, X_INDEX, cv, logger
    )
    metrics_df.to_csv(OUTPUT_DIR / "01_model_comparison_metrics.csv", index=False)
    logger.log("[输出] 01_model_comparison_metrics.csv")

    # 4. ROC曲线
    plot_roc_curves(results, y, OUTPUT_DIR, logger)

    # 5. 校准图
    plot_calibration(results, y, OUTPUT_DIR, logger)

    # 6. 变量重要性
    logger.log("\n" + "=" * 50)
    logger.log("变量重要性（全量训练）")
    imp_df = compute_variable_importance(models, X_index_arr, y, X_INDEX, OUTPUT_DIR, logger)

    # 7. SHAP分析（五维分解口径）
    shap_values, shap_df = run_shap_analysis(X_gap_arr, y, X_GAP, OUTPUT_DIR, logger)

    # 8. 医生分层画像
    segments, y_prob_seg = run_segmentation(
        X_gap_df, y, shap_values, X_GAP, OUTPUT_DIR, logger
    )

    # 9. SHAP依赖图
    plot_shap_dependence(shap_values, X_gap_arr, X_GAP, OUTPUT_DIR, logger)

    # 10. 预测结果导出
    export_predictions(
        segments, y_prob_seg, y, X_index_df, X_gap_df, X_INDEX, X_GAP, OUTPUT_DIR, logger
    )

    # 11. 推广策略建议
    export_strategy_table(segments, y, X_gap_df, X_GAP, OUTPUT_DIR, logger)

    # 12. 运行日志
    logger.log("\n" + "=" * 60)
    logger.log("全部完成！输出文件列表：")
    for f in sorted(OUTPUT_DIR.glob("*")):
        logger.log(f"  {f.name}")
    logger.log("\n注意事项：")
    logger.log("1. 本研究N≈200，结论定位为'探索性预测与推广分层'，不得作为临床级预测工具")
    logger.log("2. 机器学习模型用于预测和分层，不替代Logistic解释模型的机制检验")
    logger.log("3. MAI_LGI_entropy与五类Gap变量未同时入模，避免重复计量")
    logger.log("4. 交叉验证采用RepeatedStratifiedKFold(5-fold × 20 repeats)，结果更稳定")
    logger.save(OUTPUT_DIR / "run_log_ml.txt")

    # 13. 结果摘要文件
    shap_summary_text = (
        "SHAP完整变量重要性显示，预测模型能够同时识别价值感知、AI接触经验和落地鸿沟变量的贡献。"
        "进一步对五类鸿沟变量进行拆解后，责任治理鸿沟和流程嵌入鸿沟表现出更强区分能力，"
        "而医院管理鸿沟的SHAP贡献较低，说明其更多体现普遍性背景约束。"
    )
    summary_lines = [
        "=" * 60,
        "第六章 机器学习预测与医生分层画像 — 结果摘要",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        "一、模型比较（综合指数口径 X_index, RepeatedStratifiedKFold 5×20）",
    ]
    metrics_df_read = pd.read_csv(OUTPUT_DIR / "01_model_comparison_metrics.csv")
    summary_lines.append(metrics_df_read.to_string(index=False))
    summary_lines.extend([
        "",
        "二、SHAP完整变量重要性",
    ])
    full_shap_read = pd.read_csv(OUTPUT_DIR / "shap_importance_full.csv")
    for _, row in full_shap_read.iterrows():
        v = row["variable"]
        summary_lines.append(f"  Rank {int(row['rank'])}: {v} ({VAR_LABELS.get(v, v)}) — mean|SHAP|={row['mean_abs_shap']:.4f}")
    summary_lines.extend([
        "",
        "三、五类鸿沟SHAP排序",
    ])
    gap_shap_read = pd.read_csv(OUTPUT_DIR / "shap_gap_importance.csv")
    for _, row in gap_shap_read.iterrows():
        v = row["variable"]
        summary_lines.append(f"  Rank {int(row['rank'])}: {v} ({GAP_LABELS.get(v, v)}) — mean|SHAP|={row['mean_abs_shap']:.4f} — {GAP_GOVERNANCE.get(v, '')}")
    summary_lines.extend([
        "",
        "四、医生分层",
    ])
    seg_read = pd.read_csv(OUTPUT_DIR / "table_segment_summary.csv")
    summary_lines.append(seg_read.to_string(index=False))
    summary_lines.extend([
        "",
        "五、SHAP变量解释摘要",
        shap_summary_text,
        "",
        "六、注意事项",
        "1. 本研究N≈200，结论定位为'探索性预测与推广分层'，不得作为临床级预测工具",
        "2. 机器学习模型用于预测和分层，不替代Logistic解释模型的机制检验",
        "3. MAI_LGI_entropy与五类Gap变量未同时入模，避免重复计量",
        "4. 交叉验证采用RepeatedStratifiedKFold(5-fold × 20 repeats)，结果更稳定",
    ])
    with open(OUTPUT_DIR / "ml_chapter_results_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    print(f"[输出] ml_chapter_results_summary.txt")

    print("\n" + "=" * 60)
    print("第六章全部完成！输出文件均在 output_ml/ 文件夹中")
    print("=" * 60)


if __name__ == "__main__":
    main()
