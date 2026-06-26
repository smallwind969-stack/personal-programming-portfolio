# -*- coding: utf-8 -*-
"""
01_build_mai_lgi_entropy.py
构建MAI-LGI医疗AI落地鸿沟指数（熵权法）
所有输出写入 output_py/ 文件夹，不修改任何原始数据文件
"""

import pandas as pd
import numpy as np
import re
import sys
import io
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output_py"

# ============================================================
# 列名映射字典 — 可手动修改
# ============================================================
column_map = {
    "id": "ID",
    "hospital_grade": "Q03_HospitalLevel",
    "case_volume": "Q04_CaseVolume",
    "ai_experience": "Q05_AIExposure",
    "pain_items": ["Q06", "Q07", "Q08", "Q09", "Q10"],
    "value_items": ["Q13_1", "Q13_2", "Q13_3", "Q13_4", "Q13_5"],
    "adoption": "Q14_AdoptIntent",
    "q18_items": ["Q18_1", "Q18_2", "Q18_3", "Q18_4", "Q18_5", "Q18_6"],
    "q19_items": ["Q19_1", "Q19_2", "Q19_3", "Q19_4", "Q19_5", "Q19_6"],
}

# ============================================================
# 五类鸿沟 → Q18/Q19 题项映射（已通过反向工程验证，200/200匹配）
# ============================================================
gap_mapping = {
    "TrustGap": {
        "cn_name": "技术信任鸿沟",
        "meaning": "准确率、稳定性、可解释性相关顾虑",
        "items": ["Q18_2", "Q19_1"],
        "keywords": "准确率、稳定性、可靠性、误判、漏判、可解释、解释性、黑箱",
        "mapped_question": "Q18_2, Q19_1",
    },
    "LiabilityGap": {
        "cn_name": "责任治理鸿沟",
        "meaning": "责任边界、临床规范、风险追溯、人类监督相关顾虑",
        "items": ["Q19_3"],
        "keywords": "责任、归属、责任边界、风险追溯、追责、临床规范、操作规范、指南、人类监督、医生监督",
        "mapped_question": "Q19_3",
    },
    "DataGap": {
        "cn_name": "数据安全鸿沟",
        "meaning": "隐私、合规、数据使用相关顾虑",
        "items": ["Q18_6", "Q19_6"],
        "keywords": "数据安全、隐私、合规、授权、数据使用、数据泄露、患者隐私、信息安全",
        "mapped_question": "Q18_6, Q19_6",
    },
    "ManageGap": {
        "cn_name": "医院管理鸿沟",
        "meaning": "设备、培训、经费、制度、政策、信息化支持相关约束",
        "items": ["Q18_1", "Q18_3", "Q18_4", "Q18_5", "Q19_4", "Q19_5"],
        "keywords": "设备、信息化、培训、学习支持、经费、政策支持、医院支持、制度、管理、采购、维护",
        "mapped_question": "Q18_1, Q18_3, Q18_4, Q18_5, Q19_4, Q19_5",
    },
    "WorkflowGap": {
        "cn_name": "流程嵌入鸿沟",
        "meaning": "工作流衔接、额外负担、操作复杂相关约束",
        "items": ["Q19_2", "Q19_4", "Q19_5"],
        "keywords": "额外工作负担、工作负担、操作复杂、流程衔接、衔接不畅、工作流、流程、耗时、额外操作、系统切换",
        "mapped_question": "Q19_2, Q19_4, Q19_5",
    },
}


# ============================================================
# 工具函数
# ============================================================
def cronbach_alpha(items_df):
    """计算Cronbach's alpha"""
    items = items_df.dropna()
    k = items.shape[1]
    if k < 2:
        return np.nan
    item_vars = items.var(axis=0, ddof=1)
    total_var = items.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return np.nan
    alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
    return alpha


def read_data():
    """读取原始数据，优先CSV，失败则Excel"""
    csv_path = BASE_DIR / "原始医生问卷数据.csv"
    xlsx_path = BASE_DIR / "医生主数据库.xlsx"
    source = None

    if csv_path.exists():
        for enc in ["utf-8-sig", "utf-8", "gbk", "gb18030"]:
            try:
                df = pd.read_csv(csv_path, encoding=enc)
                source = f"CSV ({enc}): {csv_path.name}"
                print(f"[读取成功] {source}, N={len(df)}, cols={len(df.columns)}")
                return df, source
            except Exception:
                continue

    if xlsx_path.exists():
        try:
            df = pd.read_excel(xlsx_path, sheet_name=0, header=3)
            source = f"Excel: {xlsx_path.name}"
            print(f"[读取成功] {source}, N={len(df)}, cols={len(df.columns)}")
            return df, source
        except Exception as e:
            print(f"[错误] Excel读取失败: {e}")
            sys.exit(1)

    print("[错误] 未找到任何数据文件")
    sys.exit(1)


def profile_columns(df, log_lines):
    """输出列名档案 → output_py/00_column_profile.xlsx"""
    rows = []
    for col in df.columns:
        non_miss = df[col].notna().sum()
        uniq5 = df[col].dropna().unique()[:5]
        rows.append({
            "column_name": col,
            "dtype": str(df[col].dtype),
            "non_missing_n": non_miss,
            "missing_n": df[col].isna().sum(),
            "first5_unique": str(list(uniq5)),
        })
    profile = pd.DataFrame(rows)
    profile.to_excel(OUTPUT_DIR / "00_column_profile.xlsx", index=False)
    msg = f"列名档案已保存: 00_column_profile.xlsx ({len(rows)}列)"
    print(f"[输出] {msg}")
    log_lines.append(msg)
    return profile


def check_column_map(df, log_lines):
    """检查column_map中所有列是否存在于df"""
    all_cols = []
    for v in column_map.values():
        if isinstance(v, list):
            all_cols.extend(v)
        else:
            all_cols.append(v)
    missing = [c for c in all_cols if c not in df.columns]
    if missing:
        msg = f"[警告] 以下列名在数据中不存在: {missing}，请手动修改column_map"
        print(msg)
        log_lines.append(msg)
        return False
    log_lines.append("column_map中所有列名均已验证通过")
    return True


def build_indices(df, log_lines):
    """构造 PainIndex, ValueIndex, AdoptTop2"""
    # --- PainIndex ---
    pain_cols = column_map["pain_items"]
    pain_df = df[pain_cols].apply(pd.to_numeric, errors="coerce")
    df["PainIndex"] = pain_df.mean(axis=1)
    alpha_pain = cronbach_alpha(pain_df)
    n_valid_pain = pain_df.dropna().shape[0]
    msg_pain = f"PainIndex: items={pain_cols}, alpha={alpha_pain:.4f}, n_valid={n_valid_pain}"
    print(f"[构造] {msg_pain}")
    log_lines.append(msg_pain)

    # --- ValueIndex ---
    value_cols = column_map["value_items"]
    value_df = df[value_cols].apply(pd.to_numeric, errors="coerce")
    df["ValueIndex"] = value_df.mean(axis=1)
    alpha_value = cronbach_alpha(value_df)
    n_valid_value = value_df.dropna().shape[0]
    msg_val = f"ValueIndex: items={value_cols}, alpha={alpha_value:.4f}, n_valid={n_valid_value}"
    print(f"[构造] {msg_val}")
    log_lines.append(msg_val)

    # --- AdoptTop2 ---
    adopt_col = column_map["adoption"]
    adopt_raw = df[adopt_col]
    uniq_vals = sorted(adopt_raw.dropna().unique())
    if set(uniq_vals).issubset({1, 2, 3, 4, 5}):
        df["AdoptTop2"] = (adopt_raw >= 4).astype(int)
        msg_adopt = f"AdoptTop2: {adopt_col}(1-5) → >=4为1, N1={df['AdoptTop2'].sum()}"
    else:
        df["AdoptTop2"] = np.nan
        msg_adopt = f"AdoptTop2: 无法自动判断, {adopt_col}唯一值={uniq_vals}, 请手动确认"
    print(f"[构造] {msg_adopt}")
    log_lines.append(msg_adopt)

    # --- 信度表 ---
    reliability = pd.DataFrame([
        {
            "scale_name": "PainIndex",
            "item_count": len(pain_cols),
            "cronbach_alpha": round(alpha_pain, 4),
            "n_valid": n_valid_pain,
        },
        {
            "scale_name": "ValueIndex",
            "item_count": len(value_cols),
            "cronbach_alpha": round(alpha_value, 4),
            "n_valid": n_valid_value,
        },
    ])
    reliability.to_csv(OUTPUT_DIR / "01_reliability_alpha.csv", index=False)
    print("[输出] 01_reliability_alpha.csv")
    log_lines.append("信度表已保存: 01_reliability_alpha.csv")

    return df, alpha_pain, alpha_value


def build_gap_variables(df, log_lines):
    """构造五类0/1鸿沟变量"""
    total_n = len(df)
    coverage_rows = []
    missing_info = {}

    for gap_var, info in gap_mapping.items():
        items = info["items"]
        items_in_df = [c for c in items if c in df.columns]
        if not items_in_df:
            df[gap_var] = 0
            msg = f"{gap_var}: 未找到对应题项，赋全0"
            print(f"[警告] {msg}")
            log_lines.append(msg)
            coverage_n = 0
        else:
            subset = df[items_in_df].apply(pd.to_numeric, errors="coerce").fillna(0)
            miss_per_item = {c: int(df[c].isna().sum()) for c in items_in_df if df[c].isna().sum() > 0}
            if miss_per_item:
                missing_info[gap_var] = miss_per_item
            df[gap_var] = (subset.sum(axis=1) >= 1).astype(int)
            coverage_n = int(df[gap_var].sum())

        coverage_pct = coverage_n / total_n
        coverage_rows.append({
            "gap_variable": gap_var,
            "gap_name_cn": info["cn_name"],
            "coverage_n": coverage_n,
            "total_n": total_n,
            "coverage_pct": round(coverage_pct, 4),
        })
        msg = f"{gap_var}({info['cn_name']}): items={items_in_df}, coverage={coverage_n}/{total_n}={coverage_pct:.2%}"
        print(f"[构造] {msg}")
        log_lines.append(msg)

    if missing_info:
        msg_miss = f"缺失值说明: {missing_info}，缺失按未选择(0)处理"
        print(f"[信息] {msg_miss}")
        log_lines.append(msg_miss)

    coverage_df = pd.DataFrame(coverage_rows)
    coverage_df.to_csv(OUTPUT_DIR / "02_gap_coverage.csv", index=False)
    print("[输出] 02_gap_coverage.csv")
    log_lines.append("鸿沟覆盖率表已保存: 02_gap_coverage.csv")

    return df, coverage_df


def entropy_weight(df, gap_vars, log_lines):
    """熵权法计算MAI_LGI_entropy"""
    n = len(df)
    eps = 1e-12
    X = df[gap_vars].copy().values.astype(float)

    low_distinction = []
    weights_info = []

    for j, gap_var in enumerate(gap_vars):
        col_sum = X[:, j].sum()
        if col_sum == 0 or col_sum == n:
            low_distinction.append(gap_var)
            e_j = 1.0
            d_j = 0.0
        else:
            p = X[:, j] / col_sum
            p = np.clip(p, eps, None)
            e_j = -1.0 / np.log(n) * np.sum(p * np.log(p))
            e_j = np.clip(e_j, 0.0, 1.0)
            d_j = 1.0 - e_j
        weights_info.append({
            "gap_variable": gap_var,
            "gap_name_cn": gap_mapping[gap_var]["cn_name"],
            "coverage_pct": round(X[:, j].sum() / n, 4),
            "entropy": round(e_j, 6),
            "diversity_coefficient": round(d_j, 6),
        })

    if low_distinction:
        msg = f"区分度极低的鸿沟变量: {low_distinction}（所有人取值完全相同）"
        print(f"[警告] {msg}")
        log_lines.append(msg)

    d_sum = sum(w["diversity_coefficient"] for w in weights_info)
    if d_sum == 0:
        w_equal = 1.0 / len(gap_vars)
        for w in weights_info:
            w["entropy_weight"] = round(w_equal, 6)
        msg = "所有差异系数为0，退化为等权"
        print(f"[警告] {msg}")
        log_lines.append(msg)
    else:
        for w in weights_info:
            w["entropy_weight"] = round(w["diversity_coefficient"] / d_sum, 6)

    w_arr = np.array([w["entropy_weight"] for w in weights_info])
    df["MAI_LGI_entropy"] = X @ w_arr

    entropy_df = pd.DataFrame(weights_info)
    entropy_df.to_csv(OUTPUT_DIR / "03_entropy_weights.csv", index=False)

    print("[输出] 03_entropy_weights.csv")
    print("[熵权结果]")
    for w in weights_info:
        print(f"  {w['gap_variable']}({w['gap_name_cn']}): weight={w['entropy_weight']:.4f}, entropy={w['entropy']:.4f}")
    log_lines.append(f"熵权结果: {weights_info}")
    log_lines.append("熵权表已保存: 03_entropy_weights.csv")

    return df, entropy_df


def export_outputs(df, log_lines):
    """导出SPSS数据集和论文表格"""
    # --- SPSS数据集 ---
    spss_cols = [
        "ID", "HospitalGrade", "CaseVolume", "AIExperience",
        "PainIndex", "ValueIndex", "AdoptTop2",
        "TrustGap", "LiabilityGap", "DataGap", "ManageGap", "WorkflowGap",
        "MAI_LGI_entropy",
    ]
    spss_df = pd.DataFrame()
    spss_df["ID"] = range(1, len(df) + 1)
    spss_df["HospitalGrade"] = df[column_map["hospital_grade"]]
    spss_df["CaseVolume"] = df[column_map["case_volume"]]
    spss_df["AIExperience"] = df[column_map["ai_experience"]]
    spss_df["PainIndex"] = df["PainIndex"]
    spss_df["ValueIndex"] = df["ValueIndex"]
    spss_df["AdoptTop2"] = df["AdoptTop2"]
    spss_df["TrustGap"] = df["TrustGap"]
    spss_df["LiabilityGap"] = df["LiabilityGap"]
    spss_df["DataGap"] = df["DataGap"]
    spss_df["ManageGap"] = df["ManageGap"]
    spss_df["WorkflowGap"] = df["WorkflowGap"]
    spss_df["MAI_LGI_entropy"] = df["MAI_LGI_entropy"]
    spss_df.to_csv(OUTPUT_DIR / "SPSS_MAI_LGI_entropy_dataset.csv", index=False)
    print("[输出] SPSS_MAI_LGI_entropy_dataset.csv")
    log_lines.append("SPSS数据集已保存")

    # --- 变量字典 ---
    var_dict = pd.DataFrame([
        {"variable_name": "ID", "variable_label_cn": "序号", "value_coding": "1-N", "measure_level": "scale", "role": "ID"},
        {"variable_name": "HospitalGrade", "variable_label_cn": "医院等级", "value_coding": "1=三级甲等 2=三级乙等 3=二级甲等 4=二级乙等", "measure_level": "ordinal", "role": "IV"},
        {"variable_name": "CaseVolume", "variable_label_cn": "病例量", "value_coding": "1=>=200 2=100-199 3=50-99 4=<50", "measure_level": "ordinal", "role": "IV"},
        {"variable_name": "AIExperience", "variable_label_cn": "AI接触经验", "value_coding": "1=经常 2=偶尔 3=很少 4=从未", "measure_level": "ordinal", "role": "IV"},
        {"variable_name": "PainIndex", "variable_label_cn": "流程痛点指数", "value_coding": "1-5均值", "measure_level": "scale", "role": "IV"},
        {"variable_name": "ValueIndex", "variable_label_cn": "AI综合价值感知指数", "value_coding": "1-5均值", "measure_level": "scale", "role": "IV"},
        {"variable_name": "AdoptTop2", "variable_label_cn": "高采用意愿", "value_coding": "1=愿意(4-5) 0=不愿意(1-3)", "measure_level": "nominal", "role": "DV"},
        {"variable_name": "TrustGap", "variable_label_cn": "技术信任鸿沟", "value_coding": "0/1", "measure_level": "nominal", "role": "IV"},
        {"variable_name": "LiabilityGap", "variable_label_cn": "责任治理鸿沟", "value_coding": "0/1", "measure_level": "nominal", "role": "IV"},
        {"variable_name": "DataGap", "variable_label_cn": "数据安全鸿沟", "value_coding": "0/1", "measure_level": "nominal", "role": "IV"},
        {"variable_name": "ManageGap", "variable_label_cn": "医院管理鸿沟", "value_coding": "0/1", "measure_level": "nominal", "role": "IV"},
        {"variable_name": "WorkflowGap", "variable_label_cn": "流程嵌入鸿沟", "value_coding": "0/1", "measure_level": "nominal", "role": "IV"},
        {"variable_name": "MAI_LGI_entropy", "variable_label_cn": "熵权法医疗AI落地鸿沟指数", "value_coding": "0-1连续", "measure_level": "scale", "role": "IV"},
    ])
    var_dict.to_csv(OUTPUT_DIR / "SPSS_variable_dictionary.csv", index=False)
    print("[输出] SPSS_variable_dictionary.csv")
    log_lines.append("变量字典已保存")

    # --- 论文表1: gap_mapping ---
    t1_rows = []
    for gap_var, info in gap_mapping.items():
        t1_rows.append({
            "gap_type_cn": info["cn_name"],
            "variable_name": gap_var,
            "meaning": info["meaning"],
            "mapped_question": info["mapped_question"],
            "keywords": info["keywords"],
        })
    pd.DataFrame(t1_rows).to_csv(OUTPUT_DIR / "table_gap_mapping.csv", index=False)
    print("[输出] table_gap_mapping.csv")

    # --- 论文表2: gap_coverage_entropy ---
    cov_df = pd.read_csv(OUTPUT_DIR / "02_gap_coverage.csv")
    ent_df = pd.read_csv(OUTPUT_DIR / "03_entropy_weights.csv")
    merged = cov_df.merge(ent_df[["gap_variable", "entropy_weight"]], on="gap_variable")
    t2_rows = []
    for _, row in merged.iterrows():
        pct = row["coverage_pct"]
        w = row["entropy_weight"]
        if pct >= 0.9 and w < 0.2:
            interp = "普遍性约束（覆盖率高但区分度低）"
        elif pct < 0.9 and w >= 0.2:
            interp = "区分性约束（覆盖率不高但区分度高）"
        elif pct >= 0.9 and w >= 0.2:
            interp = "高覆盖高区分约束"
        else:
            interp = "低覆盖低区分约束"
        t2_rows.append({
            "gap_type_cn": row["gap_name_cn"],
            "variable_name": row["gap_variable"],
            "coverage_pct": round(pct, 4),
            "entropy_weight": round(w, 6),
            "interpretation": interp,
        })
    pd.DataFrame(t2_rows).to_csv(OUTPUT_DIR / "table_gap_coverage_entropy.csv", index=False)
    print("[输出] table_gap_coverage_entropy.csv")

    # --- 论文表3: variable_summary ---
    summary_cols = [
        "HospitalGrade", "CaseVolume", "AIExperience",
        "PainIndex", "ValueIndex", "AdoptTop2",
        "TrustGap", "LiabilityGap", "DataGap", "ManageGap", "WorkflowGap",
        "MAI_LGI_entropy",
    ]
    t3_rows = []
    for col in summary_cols:
        s = spss_df[col]
        t3_rows.append({
            "variable_name": col,
            "mean": round(s.mean(), 4),
            "std": round(s.std(), 4),
            "min": round(s.min(), 4),
            "max": round(s.max(), 4),
            "missing_n": int(s.isna().sum()),
        })
    pd.DataFrame(t3_rows).to_csv(OUTPUT_DIR / "table_variable_summary.csv", index=False)
    print("[输出] table_variable_summary.csv")

    log_lines.append("论文展示表全部输出完成")
    return spss_df


def run_logistic_check(spss_df, log_lines):
    """Python核验Logistic回归"""
    import statsmodels.api as sm

    dv = "AdoptTop2"
    ivs = ["ValueIndex", "MAI_LGI_entropy", "PainIndex", "AIExperience", "CaseVolume", "HospitalGrade"]
    analysis_df = spss_df[[dv] + ivs].dropna()

    if analysis_df[dv].nunique() < 2:
        msg = "因变量AdoptTop2只有一个水平，无法做Logistic回归"
        print(f"[错误] {msg}")
        log_lines.append(msg)
        return

    X = sm.add_constant(analysis_df[ivs])
    y = analysis_df[dv]

    try:
        model = sm.Logit(y, X).fit(disp=0)
    except Exception as e:
        msg = f"Logistic回归不收敛: {e}"
        print(f"[错误] {msg}")
        log_lines.append(msg)
        return

    rows = []
    for var in ivs:
        coef = model.params[var]
        OR = np.exp(coef)
        ci = model.conf_int().loc[var]
        ci_lower = np.exp(ci[0])
        ci_upper = np.exp(ci[1])
        p_val = model.pvalues[var]
        rows.append({
            "variable": var,
            "coef": round(coef, 6),
            "OR": round(OR, 4),
            "CI_lower": round(ci_lower, 4),
            "CI_upper": round(ci_upper, 4),
            "p_value": round(p_val, 6),
        })

    logit_df = pd.DataFrame(rows)
    logit_df.to_csv(OUTPUT_DIR / "04_python_logistic_check.csv", index=False)
    print("[输出] 04_python_logistic_check.csv")
    print("[Python核验Logistic结果]")
    for r in rows:
        sig = "*" if r["p_value"] < 0.05 else ""
        print(f"  {r['variable']}: OR={r['OR']:.3f}, 95%CI=[{r['CI_lower']:.3f},{r['CI_upper']:.3f}], p={r['p_value']:.4f}{sig}")
    log_lines.append("Python核验Logistic回归完成")
    log_lines.append("注意: 正式论文结果以SPSS为准")


def write_log(log_lines, source, df, spss_df):
    """写入运行日志"""
    lines = [
        "=" * 60,
        "MAI-LGI 熵权法构建 运行日志",
        f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        f"数据来源: {source}",
        f"样本量: {len(df)}",
        "",
        "=== 核心变量构造来源 ===",
        f"  HospitalGrade ← {column_map['hospital_grade']}",
        f"  CaseVolume ← {column_map['case_volume']}",
        f"  AIExperience ← {column_map['ai_experience']}",
        f"  PainIndex ← mean({column_map['pain_items']})",
        f"  ValueIndex ← mean({column_map['value_items']})",
        f"  AdoptTop2 ← {column_map['adoption']} >= 4",
        "",
        "=== 五类鸿沟命中规则 ===",
    ]
    for gap_var, info in gap_mapping.items():
        lines.append(f"  {gap_var}({info['cn_name']}) = OR({info['items']})")

    lines.extend([
        "",
        "=== 熵权法 ===",
        "  使用熵权法，非等权法",
        "  eps = 1e-12",
        "",
        "=== 缺失值 ===",
        f"  总缺失数: {int(spss_df.isna().sum().sum())}",
        "",
        "=== 输出文件 ===",
    ])
    output_files = sorted(OUTPUT_DIR.glob("*"))
    for f in output_files:
        lines.append(f"  {f.name}")

    lines.append("")
    lines.append("=== 详细日志 ===")
    lines.extend(log_lines)

    with open(OUTPUT_DIR / "run_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[输出] run_log.txt")


# ============================================================
# 主函数
# ============================================================
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    log_lines = []

    print("=" * 50)
    print("MAI-LGI 熵权法医疗AI落地鸿沟指数构建")
    print("=" * 50)

    # 1. 读取数据
    df, source = read_data()

    # 2. 列名档案
    profile_columns(df, log_lines)

    # 3. 检查列名映射
    if not check_column_map(df, log_lines):
        print("\n[暂停] 请修改column_map后重新运行")
        return

    # 4. 构造指数
    df, alpha_pain, alpha_value = build_indices(df, log_lines)

    # 5. 构造鸿沟变量
    gap_vars = list(gap_mapping.keys())
    df, coverage_df = build_gap_variables(df, log_lines)

    # 6. 熵权法
    df, entropy_df = entropy_weight(df, gap_vars, log_lines)

    # 7. 导出
    spss_df = export_outputs(df, log_lines)

    # 8. Logistic核验
    run_logistic_check(spss_df, log_lines)

    # 9. 日志
    write_log(log_lines, source, df, spss_df)

    print("\n" + "=" * 50)
    print("全部完成！输出文件均在 output_py/ 文件夹中")
    print("=" * 50)


if __name__ == "__main__":
    main()
