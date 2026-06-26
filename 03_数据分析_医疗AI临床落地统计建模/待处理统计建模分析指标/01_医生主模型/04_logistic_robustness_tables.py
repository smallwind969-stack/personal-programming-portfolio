# -*- coding: utf-8 -*-
"""
04_logistic_robustness_tables.py
第九章：Logistic模型稳健性检验汇总表

依次估计M1-M5五个Logistic模型，检验核心变量方向和显著性稳定性
所有输出写入 output_robustness/ 文件夹
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys
import io
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output_robustness"


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


def read_data():
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
            return df
    logger.log("[错误] 未找到数据文件")
    sys.exit(1)


def fit_logit(y, X_df, model_name, logger):
    """
    拟合Logistic回归
    P_i = 1 / (1 + exp(-X_i beta))
    OR = exp(beta)
    95%CI = exp(beta ± 1.96 × SE)
    """
    X = sm.add_constant(X_df)
    try:
        model = sm.Logit(y, X).fit(disp=0)
    except Exception as e:
        logger.log(f"[警告] {model_name} 不收敛: {e}")
        return None

    n = int(model.nobs)
    aic = model.aic
    # McFadden pseudo R2
    pseudo_r2 = 1 - model.llf / model.llnull

    return {
        "model_obj": model,
        "n": n,
        "aic": round(aic, 2),
        "pseudo_r2": round(pseudo_r2, 4),
    }


def extract_var_result(model_obj, var_name):
    """提取单个变量的coef, OR, CI, p"""
    if var_name not in model_obj.params.index:
        return None
    coef = model_obj.params[var_name]
    se = model_obj.bse[var_name]
    or_val = np.exp(coef)
    ci_lower = np.exp(coef - 1.96 * se)
    ci_upper = np.exp(coef + 1.96 * se)
    p_val = model_obj.pvalues[var_name]
    return {
        "coef": round(coef, 6),
        "OR": round(or_val, 4),
        "CI_lower": round(ci_lower, 4),
        "CI_upper": round(ci_upper, 4),
        "p": round(p_val, 6),
    }


def build_conclusion(vi_result, mai_result):
    """生成核心结论"""
    parts = []
    if vi_result:
        if vi_result["OR"] > 1:
            parts.append("价值感知方向稳定为正")
        else:
            parts.append("价值感知方向不稳定")
        if vi_result["p"] < 0.05:
            parts.append("ValueIndex显著")
        else:
            parts.append("ValueIndex方向一致，显著性有所变化")

    if mai_result:
        if mai_result["OR"] < 1:
            parts.append("落地鸿沟方向稳定为负")
        else:
            parts.append("落地鸿沟方向不稳定")
        if mai_result["p"] < 0.05:
            parts.append("MAI-LGI显著")
        else:
            parts.append("MAI-LGI方向一致，显著性有所变化")

    return "；".join(parts)


def run_all_models(df, logger):
    y = df["AdoptTop2"]

    models_spec = [
        {
            "name": "M1",
            "desc": "核心变量模型",
            "vars": ["ValueIndex", "MAI_LGI_entropy"],
            "treatment": "仅核心变量",
        },
        {
            "name": "M2",
            "desc": "机制变量模型",
            "vars": ["ValueIndex", "MAI_LGI_entropy", "PainIndex", "AIExperience"],
            "treatment": "加入痛点与AI经验",
        },
        {
            "name": "M3",
            "desc": "完整模型",
            "vars": ["ValueIndex", "MAI_LGI_entropy", "PainIndex", "AIExperience", "CaseVolume", "HospitalGrade"],
            "treatment": "加入病例量与医院等级",
        },
        {
            "name": "M4",
            "desc": "哑变量模型",
            "treatment": "分类变量设为哑变量",
            "dummy": True,
        },
        {
            "name": "M5",
            "desc": "五类鸿沟分解模型",
            "vars": ["ValueIndex", "PainIndex", "AIExperience", "CaseVolume", "HospitalGrade",
                     "TrustGap", "LiabilityGap", "DataGap", "ManageGap", "WorkflowGap"],
            "treatment": "五类鸿沟分解替代MAI-LGI",
        },
    ]

    results = []
    cn_rows = []

    for spec in models_spec:
        name = spec["name"]
        desc = spec["desc"]
        treatment = spec["treatment"]

        logger.log(f"\n[拟合] {name}: {desc}")

        # 构造X
        if spec.get("dummy"):
            # M4: 分类变量用哑变量
            X_df = df[["ValueIndex", "MAI_LGI_entropy", "PainIndex"]].copy()
            for cat_var in ["AIExperience", "CaseVolume", "HospitalGrade"]:
                dummies = pd.get_dummies(df[cat_var], prefix=cat_var, drop_first=True).astype(float)
                X_df = pd.concat([X_df, dummies], axis=1)
            X_df = X_df.astype(float)
        else:
            X_df = df[spec["vars"]].copy()

        fit = fit_logit(y, X_df, name, logger)
        if fit is None:
            results.append({
                "model": name, "model_description": desc, "n": len(df),
                "AIC": np.nan, "pseudo_r2": np.nan,
                "ValueIndex_coef": np.nan, "ValueIndex_OR": np.nan,
                "ValueIndex_CI_lower": np.nan, "ValueIndex_CI_upper": np.nan, "ValueIndex_p": np.nan,
                "MAI_LGI_coef": np.nan, "MAI_LGI_OR": np.nan,
                "MAI_LGI_CI_lower": np.nan, "MAI_LGI_CI_upper": np.nan, "MAI_LGI_p": np.nan,
                "core_conclusion": "模型不收敛",
            })
            cn_rows.append({
                "模型": name, "处理方式": treatment,
                "ValueIndex OR": np.nan, "ValueIndex p值": np.nan,
                "MAI-LGI OR": np.nan, "MAI-LGI p值": np.nan,
                "补充结果": "", "结论": "模型不收敛",
            })
            continue

        model_obj = fit["model_obj"]

        # ValueIndex
        vi = extract_var_result(model_obj, "ValueIndex")

        # MAI_LGI_entropy (M1-M4有，M5没有)
        mai = extract_var_result(model_obj, "MAI_LGI_entropy")

        # 核心结论
        conclusion = build_conclusion(vi, mai)

        row = {
            "model": name,
            "model_description": desc,
            "n": fit["n"],
            "AIC": fit["aic"],
            "pseudo_r2": fit["pseudo_r2"],
            "ValueIndex_coef": vi["coef"] if vi else np.nan,
            "ValueIndex_OR": vi["OR"] if vi else np.nan,
            "ValueIndex_CI_lower": vi["CI_lower"] if vi else np.nan,
            "ValueIndex_CI_upper": vi["CI_upper"] if vi else np.nan,
            "ValueIndex_p": vi["p"] if vi else np.nan,
            "MAI_LGI_coef": mai["coef"] if mai else np.nan,
            "MAI_LGI_OR": mai["OR"] if mai else np.nan,
            "MAI_LGI_CI_lower": mai["CI_lower"] if mai else np.nan,
            "MAI_LGI_CI_upper": mai["CI_upper"] if mai else np.nan,
            "MAI_LGI_p": mai["p"] if mai else np.nan,
            "core_conclusion": conclusion,
        }
        results.append(row)

        # 中文表行
        cn_row = {
            "模型": name,
            "处理方式": treatment,
            "ValueIndex OR": vi["OR"] if vi else np.nan,
            "ValueIndex p值": vi["p"] if vi else np.nan,
            "MAI-LGI OR": mai["OR"] if mai else "—",
            "MAI-LGI p值": mai["p"] if mai else "—",
            "补充结果": "",
            "结论": conclusion,
        }

        # M5特殊处理：输出LiabilityGap和WorkflowGap
        if name == "M5":
            liab = extract_var_result(model_obj, "LiabilityGap")
            wf = extract_var_result(model_obj, "WorkflowGap")
            supp_parts = []
            if liab:
                supp_parts.append(f"LiabilityGap OR={liab['OR']:.3f}, p={liab['p']:.4f}")
            if wf:
                supp_parts.append(f"WorkflowGap OR={wf['OR']:.3f}, p={wf['p']:.4f}")
            cn_row["补充结果"] = "; ".join(supp_parts)
            # M5结论补充
            m5_extra = []
            if liab and liab["OR"] < 1 and liab["p"] < 0.05:
                m5_extra.append("责任治理鸿沟为显著阻力")
            if wf and wf["OR"] < 1 and wf["p"] < 0.05:
                m5_extra.append("流程嵌入鸿沟为显著阻力")
            if m5_extra:
                cn_row["结论"] = conclusion + "；" + "；".join(m5_extra)

        cn_rows.append(cn_row)

        # 日志输出
        logger.log(f"  N={fit['n']}, AIC={fit['aic']:.2f}, Pseudo-R2={fit['pseudo_r2']:.4f}")
        if vi:
            sig = "*" if vi["p"] < 0.05 else ""
            logger.log(f"  ValueIndex: coef={vi['coef']:.4f}, OR={vi['OR']:.3f}, "
                        f"CI=[{vi['CI_lower']:.3f},{vi['CI_upper']:.3f}], p={vi['p']:.4f}{sig}")
        if mai:
            sig = "*" if mai["p"] < 0.05 else ""
            logger.log(f"  MAI_LGI: coef={mai['coef']:.4f}, OR={mai['OR']:.3f}, "
                        f"CI=[{mai['CI_lower']:.3f},{mai['CI_upper']:.3f}], p={mai['p']:.4f}{sig}")
        logger.log(f"  结论: {conclusion}")

    return pd.DataFrame(results), pd.DataFrame(cn_rows)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    logger.log("=" * 60)
    logger.log("第九章：Logistic模型稳健性检验")
    logger.log(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log("=" * 60)
    logger.log("")
    logger.log("Logistic模型预测概率为：")
    logger.log("  P_i = 1 / (1 + exp(-X_i beta))")
    logger.log("  OR = exp(beta)")
    logger.log("  95%CI = exp(beta ± 1.96 × SE)")
    logger.log("")

    df = read_data()
    results_df, cn_df = run_all_models(df, logger)

    results_df.to_csv(OUTPUT_DIR / "logistic_robustness_results.csv", index=False)
    logger.log("\n[输出] logistic_robustness_results.csv")

    cn_df.to_csv(OUTPUT_DIR / "table_logistic_robustness_cn.csv", index=False)
    logger.log("[输出] table_logistic_robustness_cn.csv")

    # 稳健性总结
    logger.log("\n" + "=" * 50)
    logger.log("稳健性总结")
    vi_or_all = results_df["ValueIndex_OR"].dropna()
    mai_or_all = results_df["MAI_LGI_OR"].dropna()
    if all(vi_or_all > 1):
        logger.log("ValueIndex OR在所有模型中均>1，方向稳定为正")
    else:
        logger.log("ValueIndex OR方向存在变化，需关注")
    if all(mai_or_all < 1):
        logger.log("MAI_LGI OR在所有模型中均<1，方向稳定为负")
    else:
        logger.log("MAI_LGI OR方向存在变化，需关注")

    logger.log("\n[注意] 第九章使用该表时，重点解释核心变量方向是否稳定，而不是要求所有稳健性模型均显著。")

    logger.save(OUTPUT_DIR / "run_log_logistic_robustness.txt")

    print("\n第九章Logistic稳健性检验汇总表已完成，输出文件位于 output_robustness/。")


if __name__ == "__main__":
    main()
