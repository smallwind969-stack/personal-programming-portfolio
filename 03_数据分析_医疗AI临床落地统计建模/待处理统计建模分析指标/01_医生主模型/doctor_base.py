
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1. 读取医生主数据库
file_path = r"./医生主数据库.xlsx"

# 你的Excel第4行是变量名，所以 header=3
df = pd.read_excel(file_path, sheet_name=0, header=3)

# 2. 选择变量
use_cols = [
    "Q05_AIExposure",
    "ValueIndex",
    "AdoptTop2",
    "PainIndex",
    "MAI_LGI",
    "Q04_CaseVolume",
    "Q03_HospitalLevel"
]

data = df[use_cols].dropna().copy()

# 3. Bootstrap中介效应
B = 5000
np.random.seed(2026)

indirect_effects = []

for i in range(B):
    sample = data.sample(n=len(data), replace=True)

    # a路径：AI接触经验 -> AI价值感知
    Xa = sm.add_constant(sample[[
        "Q05_AIExposure",
        "PainIndex",
        "Q04_CaseVolume",
        "Q03_HospitalLevel"
    ]])
    ya = sample["ValueIndex"]
    model_a = sm.OLS(ya, Xa).fit()
    a = model_a.params["Q05_AIExposure"]

    # b路径：AI价值感知 -> 高采用意愿
    Xb = sm.add_constant(sample[[
        "ValueIndex",
        "Q05_AIExposure",
        "PainIndex",
        "MAI_LGI",
        "Q04_CaseVolume",
        "Q03_HospitalLevel"
    ]])
    yb = sample["AdoptTop2"]

    try:
        model_b = sm.Logit(yb, Xb).fit(disp=0)
        b = model_b.params["ValueIndex"]
        indirect_effects.append(a * b)
    except:
        continue

indirect_effects = np.array(indirect_effects)

# 4. 输出结果
mean_effect = indirect_effects.mean()
ci_lower = np.percentile(indirect_effects, 2.5)
ci_upper = np.percentile(indirect_effects, 97.5)

result = pd.DataFrame({
    "Path": ["AI Exposure -> Value Perception -> Adoption"],
    "Bootstrap_N": [len(indirect_effects)],
    "Indirect_Effect": [mean_effect],
    "CI_95_Lower": [ci_lower],
    "CI_95_Upper": [ci_upper],
    "Conclusion": ["Significant" if (ci_lower > 0 or ci_upper < 0) else "Not Significant"]
})

print(result)

result.to_excel("Bootstrap中介效应结果.xlsx", index=False)