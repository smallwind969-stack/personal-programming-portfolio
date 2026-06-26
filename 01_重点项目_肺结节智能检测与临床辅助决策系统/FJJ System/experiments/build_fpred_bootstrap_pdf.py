import json
from datetime import datetime
from pathlib import Path
from textwrap import wrap

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final"
VAL = ROOT / "docs" / "world_frontier" / "luna16" / "fpred_finetune_subset0" / "metrics" / "bootstrap_summary.json"
TEST = ROOT / "docs" / "world_frontier" / "luna16" / "patch_test_103" / "metrics" / "bootstrap_summary.json"
FIGURE = ROOT / "docs" / "world_frontier" / "luna16" / "patch_test_103" / "metrics" / "fpred_publication_validation.png"


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Source Han Sans SC", "SimSun", "Arial"],
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
})


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def add_title(ax, title, subtitle=None):
    ax.text(0.06, 0.94, title, fontsize=20, fontweight="bold", va="top")
    if subtitle:
        ax.text(0.06, 0.89, subtitle, fontsize=10, color="#555555", va="top")


def add_wrapped(ax, text, x, y, width=52, fontsize=10, line_gap=0.036, color="#111111"):
    yy = y
    for para in text.split("\n"):
        if not para.strip():
            yy -= line_gap
            continue
        for line in wrap(para, width=width):
            ax.text(x, yy, line, fontsize=fontsize, color=color, va="top")
            yy -= line_gap
        yy -= 0.006
    return yy


def add_table(ax, columns, rows, bbox, fontsize=8.5):
    table = ax.table(cellText=rows, colLabels=columns, cellLoc="center", colLoc="center", bbox=bbox)
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#d8d8d8")
        if row == 0:
            cell.set_facecolor("#e8f1f7")
            cell.set_text_props(fontweight="bold")
    return table


def metric_table(summary):
    labels = {
        "auc": "AUC",
        "accuracy": "accuracy",
        "precision": "precision",
        "sensitivity": "sensitivity",
        "specificity": "specificity",
        "f1": "F1",
    }
    rows = []
    for key, label in labels.items():
        point = summary["point"][key]
        ci = summary["ci95"][key]
        rows.append([label, f"{point:.4f}", f"{ci['lower']:.4f}-{ci['upper']:.4f}"])
    return rows


def cover_page(pdf, val, test):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    add_title(ax, "肺结节检测 Agent：FPRED 分支统计升级报告", f"LUNA16 subset0 独立候选测试与 bootstrap 95% CI | 生成时间：{now}")
    add_wrapped(
        ax,
        "本报告面向大创结题、下周阶段汇报和后续论文初稿，记录当前项目从系统演示升级为可复现科研证据链的一次关键推进。"
        "本轮工作新增固定阈值独立测试、bootstrap 置信区间、论文级多面板图和可复现实验脚本。",
        0.06,
        0.80,
        width=49,
        fontsize=11,
    )
    rows = [
        ["validation", val["prediction_count"], val["positive_count"], val["negative_count"], val["resampling_unit"]],
        ["independent test", test["prediction_count"], test["positive_count"], test["negative_count"], test["resampling_unit"]],
    ]
    add_table(ax, ["split", "candidates", "positive", "negative", "bootstrap unit"], rows, [0.08, 0.58, 0.84, 0.14], fontsize=9)
    add_wrapped(
        ax,
        "核心结论：在固定阈值 0.30 下，独立测试集 AUC 为 "
        f"{test['point']['auc']:.4f}（95% CI: {test['ci95']['auc']['lower']:.4f}-{test['ci95']['auc']['upper']:.4f}），"
        f"敏感度为 {test['point']['sensitivity']:.4f}，特异度为 {test['point']['specificity']:.4f}。"
        "由于测试阳性候选仅 7 个，敏感度和精确率区间较宽；该结果应表述为子集级候选分类证据，而不是完整 LUNA16 官方 FROC/CPM 成绩。",
        0.06,
        0.48,
        width=50,
        fontsize=10,
        color="#222222",
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def result_page(pdf, val, test):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    add_title(ax, "1. 固定阈值结果与置信区间", "阈值在 validation set 锁定，test set 不再反向调参")
    add_wrapped(
        ax,
        "bootstrap 次数为 2000，随机种子为 20260614。测试集预测文件包含 seriesuid，因此采用病例/扫描级重采样；验证集预测文件未保存 seriesuid，因此采用候选级重采样。",
        0.06,
        0.82,
        width=52,
        fontsize=10,
    )
    ax.text(0.08, 0.70, "validation", fontsize=11, fontweight="bold")
    add_table(ax, ["metric", "point", "95% CI"], metric_table(val), [0.08, 0.43, 0.38, 0.24], fontsize=8.2)
    ax.text(0.54, 0.70, "independent test", fontsize=11, fontweight="bold")
    add_table(ax, ["metric", "point", "95% CI"], metric_table(test), [0.54, 0.43, 0.38, 0.24], fontsize=8.2)
    add_wrapped(
        ax,
        "可写入论文的审慎表述：微调后的 ResNet-CBAM FPRED 分支在 LUNA16 subset0 独立候选测试中显示出较强假阳性削减能力，但当前证据仍受限于测试阳性候选数和 subset0 范围。",
        0.06,
        0.31,
        width=52,
        fontsize=10,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def figure_page(pdf):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    add_title(ax, "2. 论文级结果图", "三面板：置信区间、验证/测试迁移、混淆矩阵")
    img = Image.open(FIGURE)
    ax_img = fig.add_axes([0.06, 0.25, 0.88, 0.58])
    ax_img.imshow(img)
    ax_img.axis("off")
    add_wrapped(
        ax,
        "图注：a，独立测试集各指标点估计及 95% bootstrap CI；b，固定阈值从验证集迁移到独立测试集后的指标变化；c，固定阈值 0.30 下的测试集混淆矩阵。",
        0.06,
        0.18,
        width=56,
        fontsize=9,
        color="#333333",
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def limits_page(pdf):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    add_title(ax, "3. 科研诚信边界与下一步", "现在能支撑阶段性结题，但还不能宣称完整官方领先")
    add_wrapped(
        ax,
        "不能写成：本系统已经达到完整 LUNA16 官方世界前沿水平。\n\n"
        "可以写成：本阶段结果证明系统已经从本地病例演示升级为具备公开数据、固定阈值、独立测试、置信区间和论文级图表的可复现科研闭环。\n\n"
        "下一步必须继续推进：扩展更多 LUNA16 subset；将 FPRED 概率回接完整 detection candidate 流；生成 LUNA-style prediction CSV；用 FROC/CPM 评价端到端检测；补齐 CLAIM 2024 所要求的数据来源、划分、阈值选择、统计区间和局限性披露。",
        0.06,
        0.82,
        width=53,
        fontsize=10,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    val = load_json(VAL)
    test = load_json(TEST)
    pdf_path = OUT / "肺结节检测Agent_FPRED置信区间与论文图升级报告.pdf"
    with PdfPages(pdf_path) as pdf:
        cover_page(pdf, val, test)
        result_page(pdf, val, test)
        figure_page(pdf)
        limits_page(pdf)
    print(pdf_path)


if __name__ == "__main__":
    main()
