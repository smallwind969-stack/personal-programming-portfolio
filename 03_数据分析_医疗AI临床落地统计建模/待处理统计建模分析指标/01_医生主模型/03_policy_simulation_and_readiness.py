# -*- coding: utf-8 -*-
"""
03_policy_simulation_and_readiness.py
第八章：政策情景仿真与分层推广决策

两部分：
1. 基于第五章Logistic模型系数的政策情景仿真
2. 基于医院资源库的AI落地准备度评分与MAI-LGI × 准备度矩阵

定位：政策预测比较和分层推广决策，不做因果推断
所有输出写入 output_policy/ 文件夹
"""

import pandas as pd
import numpy as np
import sys
import io
import warnings
import re
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

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output_policy"
HOSPITAL_XLSX = Path(r"C:\Users\LSY\Desktop\0516 50 hospitals.xlsx")

# ============================================================
# 第五章正式Logistic模型系数
# ============================================================
LOGISTIC_COEFS = {
    "Intercept": -9.200,
    "ValueIndex": 1.394,
    "MAI_LGI_entropy": -1.787,
    "PainIndex": 0.574,
    "AIExperience": 0.485,
    "CaseVolume": 0.116,
    "HospitalGrade": -0.153,
}

# 熵权法权重（从01脚本结果确认）
ENTROPY_WEIGHTS = {
    "TrustGap": 0.079,
    "LiabilityGap": 0.463,
    "DataGap": 0.199,
    "ManageGap": 0.017,
    "WorkflowGap": 0.242,
}

GAP_LABELS = {
    "TrustGap": "技术信任鸿沟",
    "LiabilityGap": "责任治理鸿沟",
    "DataGap": "数据安全鸿沟",
    "ManageGap": "医院管理鸿沟",
    "WorkflowGap": "流程嵌入鸿沟",
}


# ============================================================
# 日志
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
# 1. 读取医生数据
# ============================================================
def read_doctor_data():
    paths = [
        BASE_DIR / "output_py" / "SPSS_MAI_LGI_entropy_dataset.csv",
        BASE_DIR / "SPSS_MAI_LGI_entropy_dataset.csv",
    ]
    required = [
        "AdoptTop2", "ValueIndex", "PainIndex", "AIExperience",
        "CaseVolume", "HospitalGrade", "MAI_LGI_entropy",
        "TrustGap", "LiabilityGap", "DataGap", "ManageGap", "WorkflowGap",
    ]
    for p in paths:
        if p.exists():
            df = pd.read_csv(p)
            missing = [v for v in required if v not in df.columns]
            if missing:
                logger.log(f"[错误] 缺少变量: {missing}")
                sys.exit(1)
            logger.log(f"[读取成功] {p.name}, N={len(df)}")
            return df, str(p)
    logger.log("[错误] 未找到 SPSS_MAI_LGI_entropy_dataset.csv")
    sys.exit(1)


# ============================================================
# 2. Logistic预测概率
# ============================================================
def logistic_predict(df, mai_lgi_col="MAI_LGI_entropy"):
    """
    P_i = 1 / (1 + exp(-eta_i))
    eta_i = Intercept + 1.394*ValueIndex - 1.787*MAI_LGI + ...
    """
    eta = (
        LOGISTIC_COEFS["Intercept"]
        + LOGISTIC_COEFS["ValueIndex"] * df["ValueIndex"]
        + LOGISTIC_COEFS["MAI_LGI_entropy"] * df[mai_lgi_col]
        + LOGISTIC_COEFS["PainIndex"] * df["PainIndex"]
        + LOGISTIC_COEFS["AIExperience"] * df["AIExperience"]
        + LOGISTIC_COEFS["CaseVolume"] * df["CaseVolume"]
        + LOGISTIC_COEFS["HospitalGrade"] * df["HospitalGrade"]
    )
    return 1.0 / (1.0 + np.exp(-eta))


def compute_mai_lgi(df, gap_overrides=None):
    """
    MAI_LGI = sum(w_j * Gap_j)
    gap_overrides: dict of {gap_var: new_value} to override
    """
    w = ENTROPY_WEIGHTS
    result = np.zeros(len(df))
    for gap_var, weight in w.items():
        if gap_overrides and gap_var in gap_overrides:
            result += weight * gap_overrides[gap_var]
        else:
            result += weight * df[gap_var].values
    return result


# ============================================================
# 3. 政策情景仿真
# ============================================================
def run_policy_simulation(df, output_dir, logger):
    logger.log("\n" + "=" * 50)
    logger.log("政策情景仿真")

    actual_pos_rate = df["AdoptTop2"].mean()
    logger.log(f"实际阳性率: {actual_pos_rate:.4f}")

    # 基准情景
    baseline_prob = logistic_predict(df)
    baseline_mean = baseline_prob.mean()
    logger.log(f"基准预测概率: {baseline_mean:.4f}")

    if abs(baseline_mean - actual_pos_rate) > 0.05:
        logger.log("[提示] 基准预测概率与实际阳性率存在差异，可能由系数来源、变量编码或四舍五入造成。")

    # 情景定义
    scenarios = OrderedDict()
    scenarios["baseline"] = {
        "cn": "基准情景",
        "overrides": None,
        "meaning": "保持当前样本状态",
    }
    scenarios["liability_governance"] = {
        "cn": "责任边界清晰化",
        "overrides": {"LiabilityGap": 0},
        "meaning": "将责任治理鸿沟设为已解决",
    }
    scenarios["data_security"] = {
        "cn": "数据安全治理",
        "overrides": {"DataGap": 0},
        "meaning": "将数据安全鸿沟设为已解决",
    }
    scenarios["workflow_integration"] = {
        "cn": "流程嵌入优化",
        "overrides": {"WorkflowGap": 0},
        "meaning": "将流程嵌入鸿沟设为已解决",
    }
    scenarios["technical_trust"] = {
        "cn": "技术信任提升",
        "overrides": {"TrustGap": 0},
        "meaning": "将技术信任鸿沟设为已解决",
    }
    scenarios["hospital_management"] = {
        "cn": "医院管理改善",
        "overrides": {"ManageGap": 0},
        "meaning": "将医院管理鸿沟设为已解决",
    }
    scenarios["comprehensive_package"] = {
        "cn": "综合治理政策包",
        "overrides": {"TrustGap": 0, "LiabilityGap": 0, "DataGap": 0, "WorkflowGap": 0},
        "meaning": "同步改善技术信任、责任、数据安全与流程嵌入鸿沟",
    }
    scenarios["sensitivity_all_zero"] = {
        "cn": "敏感性分析：五类鸿沟全部消除",
        "overrides": {"TrustGap": 0, "LiabilityGap": 0, "DataGap": 0, "ManageGap": 0, "WorkflowGap": 0},
        "meaning": "五类鸿沟全部设为0，敏感性上界",
    }

    results = []
    for scenario_name, info in scenarios.items():
        overrides = info["overrides"]
        if overrides is None:
            prob = baseline_prob
            mai_lgi = df["MAI_LGI_entropy"].values
        else:
            df_temp = df.copy()
            for gap_var, new_val in overrides.items():
                df_temp[gap_var] = new_val
            df_temp["MAI_LGI_policy"] = compute_mai_lgi(df_temp, gap_overrides=None)
            prob = logistic_predict(df_temp, mai_lgi_col="MAI_LGI_policy")
            mai_lgi = df_temp["MAI_LGI_policy"].values

        mean_prob = prob.mean()
        mean_mai_lgi = mai_lgi.mean()
        prob_gain = mean_prob - baseline_mean
        rel_gain = (prob_gain / baseline_mean * 100) if baseline_mean > 0 else 0

        results.append({
            "scenario": scenario_name,
            "mean_predicted_probability": round(mean_prob, 4),
            "probability_gain": round(prob_gain, 4),
            "relative_gain_pct": round(rel_gain, 2),
            "mean_MAI_LGI": round(mean_mai_lgi, 4),
            "policy_meaning": info["meaning"],
        })
        logger.log(f"  {scenario_name}: mean_P={mean_prob:.4f}, gain={prob_gain:+.4f} ({rel_gain:+.1f}%), MAI-LGI={mean_mai_lgi:.4f}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_dir / "policy_scenario_results.csv", index=False)
    logger.log("[输出] policy_scenario_results.csv")

    # 中文表
    cn_rows = []
    for _, row in results_df.iterrows():
        cn_rows.append({
            "政策情景": row["scenario"],
            "平均预测采纳概率": row["mean_predicted_probability"],
            "较基准提升": row["probability_gain"],
            "相对提升(%)": row["relative_gain_pct"],
            "平均MAI-LGI": row["mean_MAI_LGI"],
            "政策含义": row["policy_meaning"],
        })
    cn_df = pd.DataFrame(cn_rows)
    cn_df.to_csv(output_dir / "table_policy_scenario_results_cn.csv", index=False)
    logger.log("[输出] table_policy_scenario_results_cn.csv")

    # 条形图
    plot_policy_bar(results_df, output_dir, logger)

    return results_df, baseline_mean


def plot_policy_bar(results_df, output_dir, logger):
    fig, ax = plt.subplots(figsize=(10, 6))
    scenarios = results_df["scenario"].values
    probs = results_df["mean_predicted_probability"].values
    baseline_p = probs[0]

    colors = ["#2166ac"] + ["#4dac26"] * (len(scenarios) - 2) + ["#d6604d"]
    bars = ax.barh(range(len(scenarios)), probs, color=colors[:len(scenarios)], edgecolor="k", linewidth=0.5)
    ax.axvline(baseline_p, color="red", linestyle="--", lw=1.5, alpha=0.7, label=f"Baseline={baseline_p:.3f}")
    ax.set_yticks(range(len(scenarios)))
    ax.set_yticklabels(scenarios, fontsize=9)
    ax.set_xlabel("Mean Predicted Adoption Probability", fontsize=12)
    ax.set_title("Policy Scenario Simulation", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="x")
    for i, p in enumerate(probs):
        ax.text(p + 0.005, i, f"{p:.3f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / "policy_scenario_bar.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] policy_scenario_bar.png")


# ============================================================
# 4. 读取医院资源库
# ============================================================
def read_hospital_data(logger):
    if not HOSPITAL_XLSX.exists():
        logger.log(f"[错误] 未找到 {HOSPITAL_XLSX}")
        sys.exit(1)

    xls = pd.ExcelFile(HOSPITAL_XLSX)
    logger.log(f"[读取] {HOSPITAL_XLSX.name}, sheets={xls.sheet_names}")

    # 优先选择"全国医院筛选清单"
    target_sheet = None
    for pref in ["全国医院筛选清单", "目标医院短名单", "医院资源采集表"]:
        if pref in xls.sheet_names:
            target_sheet = pref
            break
    if target_sheet is None:
        target_sheet = xls.sheet_names[0]

    df = pd.read_excel(xls, sheet_name=target_sheet)
    logger.log(f"[选择sheet] {target_sheet}, N={len(df)}, cols={len(df.columns)}")
    return df, target_sheet


def identify_hospital_name_col(df, logger):
    """识别医院名称列"""
    candidates = []
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["医院", "名称", "hospital", "name"]):
            candidates.append(col)
    if candidates:
        chosen = candidates[0]
        logger.log(f"[识别] 医院名称列: {chosen}")
        return chosen
    logger.log("[警告] 未识别到医院名称列，使用第一列")
    return df.columns[0]


def identify_score_columns(df, logger):
    """识别评分列"""
    exclude_kw = ["年份", "电话", "网址", "链接", "经纬", "邮编", "序号", "id", "时间",
                  "名称", "链接", "来源名称", "来源链接", "理由", "依据", "说明",
                  "类别", "等级", "标识", "推荐", "目标", "用途", "城市", "省份",
                  "证据"]
    include_kw = ["分", "score", "hairi", "医疗资源", "专科", "crc", "数字化", "ai",
                  "区域", "来源分"]

    score_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in exclude_kw):
            continue
        if any(kw in col_lower for kw in include_kw):
            try:
                vals = pd.to_numeric(df[col], errors="coerce")
                if vals.notna().sum() > len(df) * 0.5:
                    score_cols.append(col)
            except Exception:
                continue

    logger.log(f"[识别] 评分列: {score_cols}")
    return score_cols


def compute_hospital_readiness(df, name_col, score_cols, output_dir, logger):
    """计算医院AI落地准备度"""
    logger.log("\n" + "=" * 50)
    logger.log("医院AI落地准备度评分")

    # 检查是否已有HAIRI列
    hairi_col = None
    for col in df.columns:
        if "hairi" in col.lower() or col in ["HAIRI初筛分", "HAIRI", "总分", "综合得分", "医院准备度"]:
            hairi_col = col
            break

    hospital_df = pd.DataFrame()
    hospital_df["hospital_name"] = df[name_col]

    if hairi_col:
        logger.log(f"[使用] 已有准备度列: {hairi_col}")
        raw_score = pd.to_numeric(df[hairi_col], errors="coerce")
        # 标准化到0-1
        s_min, s_max = raw_score.min(), raw_score.max()
        if s_max > s_min:
            hospital_df["readiness_score"] = (raw_score - s_min) / (s_max - s_min)
        else:
            hospital_df["readiness_score"] = 0.5
        used_cols = [hairi_col]
    else:
        logger.log("[计算] 对评分列进行0-1标准化后等权求均值")
        norm_scores = []
        used_cols = []
        for col in score_cols:
            vals = pd.to_numeric(df[col], errors="coerce")
            v_min, v_max = vals.min(), vals.max()
            if v_max > v_min:
                norm = (vals - v_min) / (v_max - v_min)
            else:
                norm = pd.Series(0.5, index=df.index)
            norm_scores.append(norm)
            used_cols.append(col)
        if norm_scores:
            hospital_df["readiness_score"] = pd.concat(norm_scores, axis=1).mean(axis=1)
        else:
            hospital_df["readiness_score"] = 0.5
            logger.log("[警告] 未找到评分列，准备度统一设为0.5")

    # 分位数分层
    p30 = hospital_df["readiness_score"].quantile(0.30)
    p70 = hospital_df["readiness_score"].quantile(0.70)

    def assign_level(score):
        if score >= p70:
            return "High"
        elif score >= p30:
            return "Medium"
        else:
            return "Low"

    hospital_df["readiness_level"] = hospital_df["readiness_score"].apply(assign_level)
    hospital_df = hospital_df.sort_values("readiness_score", ascending=False).reset_index(drop=True)
    hospital_df["rank"] = range(1, len(hospital_df) + 1)
    hospital_df["used_score_columns"] = ", ".join(used_cols)

    hospital_df.to_csv(output_dir / "hospital_readiness_hairi.csv", index=False)
    logger.log("[输出] hospital_readiness_hairi.csv")

    # 分层汇总
    level_counts = hospital_df["readiness_level"].value_counts()
    summary_rows = []
    for level in ["High", "Medium", "Low"]:
        n = level_counts.get(level, 0)
        summary_rows.append({
            "readiness_level": level,
            "n": n,
            "pct": round(n / len(hospital_df), 4),
            "mean_score": round(hospital_df.loc[hospital_df["readiness_level"] == level, "readiness_score"].mean(), 4) if n > 0 else 0,
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_dir / "hospital_readiness_summary.csv", index=False)
    logger.log("[输出] hospital_readiness_summary.csv")

    # 中文表
    cn_rows = []
    level_cn = {"High": "高准备度", "Medium": "中准备度", "Low": "低准备度"}
    for _, row in summary_df.iterrows():
        cn_rows.append({
            "准备度分层": level_cn.get(row["readiness_level"], row["readiness_level"]),
            "医院数量": row["n"],
            "占比": row["pct"],
            "平均准备度分数": row["mean_score"],
        })
    cn_df = pd.DataFrame(cn_rows)
    cn_df.to_csv(output_dir / "table_hospital_readiness_summary_cn.csv", index=False)
    logger.log("[输出] table_hospital_readiness_summary_cn.csv")

    # 条形图
    plot_readiness_bar(hospital_df, output_dir, logger)

    logger.log(f"[分层结果] High={level_counts.get('High',0)}, Medium={level_counts.get('Medium',0)}, Low={level_counts.get('Low',0)}")
    logger.log(f"  p30={p30:.4f}, p70={p70:.4f}")

    return hospital_df


def plot_readiness_bar(hospital_df, output_dir, logger):
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = hospital_df["readiness_level"].map({"High": "#4dac26", "Medium": "#f4a460", "Low": "#d6604d"})
    ax.bar(range(len(hospital_df)), hospital_df["readiness_score"], color=colors, edgecolor="k", linewidth=0.3)
    ax.set_xlabel("Hospital Rank", fontsize=11)
    ax.set_ylabel("Readiness Score (0-1)", fontsize=11)
    ax.set_title("Hospital AI Readiness Index (HAIRI)", fontsize=13)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#4dac26", label="High"),
        Patch(facecolor="#f4a460", label="Medium"),
        Patch(facecolor="#d6604d", label="Low"),
    ]
    ax.legend(handles=legend_elements, fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(output_dir / "hospital_readiness_bar.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] hospital_readiness_bar.png")


# ============================================================
# 5. MAI-LGI × 医院准备度矩阵
# ============================================================
def build_mai_lgi_readiness_matrix(doctor_df, hospital_df, output_dir, logger):
    """构建MAI-LGI × 医院准备度四象限推广矩阵"""
    logger.log("\n" + "=" * 50)
    logger.log("MAI-LGI × 医院准备度矩阵")

    # 医生端MAI-LGI阈值
    mai_lgi_median = doctor_df["MAI_LGI_entropy"].median()
    n_low_mai = (doctor_df["MAI_LGI_entropy"] <= mai_lgi_median).sum()
    n_high_mai = (doctor_df["MAI_LGI_entropy"] > mai_lgi_median).sum()
    logger.log(f"MAI-LGI中位数: {mai_lgi_median:.4f}")
    logger.log(f"  Low MAI-LGI: {n_low_mai}, High MAI-LGI: {n_high_mai}")

    # 医院端
    n_high_h = (hospital_df["readiness_level"] == "High").sum()
    n_med_h = (hospital_df["readiness_level"] == "Medium").sum()
    n_low_h = (hospital_df["readiness_level"] == "Low").sum()

    # 四象限
    matrix_rows = [
        {
            "组合类型": "Low MAI-LGI × High readiness",
            "医生端判断": f"MAI-LGI <= {mai_lgi_median:.3f} (落地阻力低)",
            "医院端判断": "高准备度 (HAIRI >= p70)",
            "政策含义": "医生阻力低、医院条件好",
            "推广策略": "优先示范试点，形成真实世界应用样板",
        },
        {
            "组合类型": "High MAI-LGI × High readiness",
            "医生端判断": f"MAI-LGI > {mai_lgi_median:.3f} (落地阻力高)",
            "医院端判断": "高准备度 (HAIRI >= p70)",
            "政策含义": "医院条件好但医生阻力大",
            "推广策略": "先治理责任边界、流程嵌入和培训机制，再推进常态化应用",
        },
        {
            "组合类型": "Low MAI-LGI × Low readiness",
            "医生端判断": f"MAI-LGI <= {mai_lgi_median:.3f} (落地阻力低)",
            "医院端判断": "低准备度 (HAIRI < p30)",
            "政策含义": "医生阻力低但医院条件不足",
            "推广策略": "补齐信息化接口、设备、培训和管理基础，开展轻量化试点",
        },
        {
            "组合类型": "High MAI-LGI × Low readiness",
            "医生端判断": f"MAI-LGI > {mai_lgi_median:.3f} (落地阻力高)",
            "医院端判断": "低准备度 (HAIRI < p30)",
            "政策含义": "医生阻力大且医院条件不足",
            "推广策略": "暂缓全面推广，以科普、培训和制度建设为主",
        },
    ]

    matrix_df = pd.DataFrame(matrix_rows)
    matrix_df.to_csv(output_dir / "mai_lgi_readiness_matrix.csv", index=False)
    logger.log("[输出] mai_lgi_readiness_matrix.csv")

    # 中文表
    cn_rows = []
    for _, row in matrix_df.iterrows():
        cn_rows.append({
            "组合类型": row["组合类型"],
            "医生端判断": row["医生端判断"],
            "医院端判断": row["医院端判断"],
            "政策含义": row["政策含义"],
            "推广策略": row["推广策略"],
        })
    cn_df = pd.DataFrame(cn_rows)
    cn_df.to_csv(output_dir / "table_mai_lgi_readiness_matrix_cn.csv", index=False)
    logger.log("[输出] table_mai_lgi_readiness_matrix_cn.csv")

    logger.log("[重要说明] 医院准备度不进入医生采纳意愿回归模型，仅作为外部证据和政策决策模块使用。")

    # 四象限可视化
    plot_matrix_heatmap(n_low_mai, n_high_mai, n_high_h, n_low_h, n_med_h,
                        mai_lgi_median, doctor_df, hospital_df, output_dir, logger)

    return matrix_df, mai_lgi_median


def plot_matrix_heatmap(n_low_mai, n_high_mai, n_high_h, n_low_h, n_med_h,
                        mai_lgi_median, doctor_df, hospital_df, output_dir, logger):
    """四象限推广矩阵可视化"""
    fig, ax = plt.subplots(figsize=(9, 7))

    strategies = {
        (0, 0): "Priority Pilot\n(low barrier, high readiness)",
        (0, 1): "Infrastructure + Pilot\n(low barrier, low readiness)",
        (1, 0): "Governance First\n(high barrier, high readiness)",
        (1, 1): "Hold & Educate\n(high barrier, low readiness)",
    }
    counts = {
        (0, 0): f"Doctors: {n_low_mai}\nHospitals: {n_high_h}",
        (0, 1): f"Doctors: {n_low_mai}\nHospitals: {n_low_h}",
        (1, 0): f"Doctors: {n_high_mai}\nHospitals: {n_high_h}",
        (1, 1): f"Doctors: {n_high_mai}\nHospitals: {n_low_h}",
    }
    colors = {
        (0, 0): "#4dac26",
        (0, 1): "#f4a460",
        (1, 0): "#2166ac",
        (1, 1): "#d6604d",
    }

    for (i, j) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=colors[(i, j)], alpha=0.3, edgecolor="k", linewidth=2))
        ax.text(j + 0.5, i + 0.65, strategies[(i, j)], ha="center", va="center", fontsize=10, fontweight="bold")
        ax.text(j + 0.5, i + 0.3, counts[(i, j)], ha="center", va="center", fontsize=9, color="gray")

    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5])
    ax.set_xticklabels(["Low Readiness", "High Readiness"], fontsize=11)
    ax.set_yticks([0.5, 1.5])
    ax.set_yticklabels(["Low MAI-LGI", "High MAI-LGI"], fontsize=11)
    ax.set_xlabel("Hospital AI Readiness", fontsize=12)
    ax.set_ylabel("Doctor MAI-LGI (Implementation Barrier)", fontsize=12)
    ax.set_title("MAI-LGI x Hospital Readiness Matrix", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_mai_lgi_readiness_matrix.png", dpi=200)
    plt.close(fig)
    logger.log("[输出] fig_mai_lgi_readiness_matrix.png")


# ============================================================
# 6. 结果摘要
# ============================================================
def write_results_summary(policy_df, baseline_mean, hospital_df, matrix_df,
                           actual_pos_rate, mai_lgi_median, output_dir, logger):
    lines = [
        "=" * 60,
        "第八章 政策情景仿真与医院准备度矩阵 — 结果摘要",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        "一、基准预测采纳概率",
        f"  实际阳性率: {actual_pos_rate:.4f}",
        f"  基准预测概率: {baseline_mean:.4f}",
        "",
        "二、各政策情景预测采纳概率和提升幅度",
    ]
    for _, row in policy_df.iterrows():
        lines.append(f"  {row['scenario']}: P={row['mean_predicted_probability']:.4f}, "
                      f"gain={row['probability_gain']:+.4f} ({row['relative_gain_pct']:+.1f}%), "
                      f"MAI-LGI={row['mean_MAI_LGI']:.4f}")

    lines.extend([
        "",
        "三、综合治理政策包预测采纳概率",
    ])
    comp_row = policy_df[policy_df["scenario"] == "comprehensive_package"].iloc[0]
    lines.append(f"  综合治理政策包: P={comp_row['mean_predicted_probability']:.4f}, "
                  f"gain={comp_row['probability_gain']:+.4f} ({comp_row['relative_gain_pct']:+.1f}%)")

    lines.extend([
        "",
        "四、医院准备度分层结果",
    ])
    for level in ["High", "Medium", "Low"]:
        n = (hospital_df["readiness_level"] == level).sum()
        pct = n / len(hospital_df)
        mean_s = hospital_df.loc[hospital_df["readiness_level"] == level, "readiness_score"].mean()
        lines.append(f"  {level}: N={n}, pct={pct:.2%}, mean_score={mean_s:.4f}")

    lines.extend([
        "",
        "五、MAI-LGI × 医院准备度矩阵",
        f"  MAI-LGI中位数阈值: {mai_lgi_median:.4f}",
    ])
    for _, row in matrix_df.iterrows():
        lines.append(f"  {row['组合类型']}: {row['推广策略']}")

    lines.extend([
        "",
        "六、谨慎说明",
        "1. 政策情景仿真是基于Logistic模型的反事实预测比较，不等同于严格因果识别。",
        "2. 医院准备度属于外部证据，不进入医生问卷主回归。",
        "3. 医院准备度不进入医生采纳意愿回归模型，仅作为外部证据和政策决策模块使用。",
    ])

    with open(output_dir / "policy_chapter_results_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.log("[输出] policy_chapter_results_summary.txt")


# ============================================================
# 主函数
# ============================================================
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    logger.log("=" * 60)
    logger.log("第八章：政策情景仿真与分层推广决策")
    logger.log(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log("=" * 60)

    # 1. 读取医生数据
    doctor_df, doctor_source = read_doctor_data()
    actual_pos_rate = doctor_df["AdoptTop2"].mean()
    logger.log(f"样本量: {len(doctor_df)}, 阳性率: {actual_pos_rate:.4f}")

    # 2. 政策情景仿真
    policy_df, baseline_mean = run_policy_simulation(doctor_df, OUTPUT_DIR, logger)

    # 3. 读取医院数据
    logger.log("\n" + "=" * 50)
    logger.log("医院资源库读取与准备度评分")
    hosp_df_raw, hosp_sheet = read_hospital_data(logger)

    # 4. 识别列
    name_col = identify_hospital_name_col(hosp_df_raw, logger)
    score_cols = identify_score_columns(hosp_df_raw, logger)

    # 5. 计算准备度
    hospital_df = compute_hospital_readiness(hosp_df_raw, name_col, score_cols, OUTPUT_DIR, logger)

    # 6. MAI-LGI × 准备度矩阵
    matrix_df, mai_lgi_median = build_mai_lgi_readiness_matrix(
        doctor_df, hospital_df, OUTPUT_DIR, logger
    )

    # 7. 结果摘要
    write_results_summary(
        policy_df, baseline_mean, hospital_df, matrix_df,
        actual_pos_rate, mai_lgi_median, OUTPUT_DIR, logger
    )

    # 8. 运行日志
    logger.log("\n" + "=" * 60)
    logger.log("全部完成！输出文件列表：")
    for f in sorted(OUTPUT_DIR.glob("*")):
        logger.log(f"  {f.name}")
    logger.log("\n[Logistic系数]")
    for k, v in LOGISTIC_COEFS.items():
        logger.log(f"  {k}: {v}")
    logger.log("\n[熵权]")
    for k, v in ENTROPY_WEIGHTS.items():
        logger.log(f"  {k}: {v}")
    logger.log(f"\n[数据来源] 医生: {doctor_source}")
    logger.log(f"[数据来源] 医院: {HOSPITAL_XLSX.name}, sheet={hosp_sheet}")
    logger.save(OUTPUT_DIR / "run_log_policy.txt")

    print("\n第八章政策情景仿真与医院准备度矩阵已完成，输出文件位于 output_policy/。")


if __name__ == "__main__":
    main()
