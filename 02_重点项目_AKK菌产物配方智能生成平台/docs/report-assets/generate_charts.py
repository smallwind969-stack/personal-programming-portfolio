from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


OUT = Path(__file__).resolve().parent
FONT_PATH = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"

font_manager.fontManager.addfont(FONT_PATH)
font_name = font_manager.FontProperties(fname=FONT_PATH).get_name()
mpl.rcParams["font.family"] = font_name
mpl.rcParams["font.sans-serif"] = [font_name]
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["figure.dpi"] = 160

BG = "#F6FAF8"
INK = "#10231F"
MUTED = "#60746E"
GREEN = "#0F766E"
LIGHT_GREEN = "#9FE7D1"
AMBER = "#F4B942"
BLUE = "#3D7EA6"
RED = "#D66A5F"
GRID = "#D8E4DF"


def clean(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)


def chart_efficiency_cycle():
    phases = ["需求整理", "参数窗口搜索", "候选方案设计", "建议书整理", "复盘回填"]
    traditional = np.array([1.5, 2.5, 3.0, 1.5, 1.0])
    platform = np.array([0.25, 0.08, 0.15, 0.25, 0.2])
    fig, ax = plt.subplots(figsize=(12, 6.75), facecolor=BG)
    ax.set_facecolor(BG)
    y = np.arange(len(phases))
    ax.barh(y + 0.18, traditional, height=0.32, color="#C8D6D1", label="传统流程（天）")
    ax.barh(y - 0.18, platform, height=0.32, color=GREEN, label="平台辅助（天）")
    for i, (old, new) in enumerate(zip(traditional, platform)):
        ax.text(old + 0.08, i + 0.18, f"{old:g}天", va="center", color=INK, fontsize=10)
        ax.text(new + 0.08, i - 0.18, f"{new:g}天", va="center", color=GREEN, fontsize=10)
    ax.set_yticks(y, phases)
    ax.invert_yaxis()
    ax.set_xlim(0, 3.8)
    ax.set_xlabel("单轮研发前置工作耗时")
    ax.set_title("图1 研发前置流程效率提升：天级流程压缩到小时级", loc="left", fontsize=18, color=INK, pad=16)
    fig.text(
        0.06,
        0.035,
        "内部试算：传统约 9.5 天，平台辅助约 0.93 天，前置周期压缩约 90%。实际值取决于数据完整度和人工审核时长。",
        color=MUTED,
        fontsize=10,
    )
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.legend(loc="lower right", frameon=False)
    clean(ax)
    plt.tight_layout(rect=(0, 0.06, 1, 1), pad=2)
    save(fig, "chart-1-efficiency-cycle.png")


def chart_cost_reduction():
    items = ["人工方案整理", "无效小试次数", "原料与培养基浪费", "建议书与复盘", "综合降本"]
    values = [45, 30, 22, 55, 32]
    colors = [BLUE, GREEN, AMBER, "#7A9E7E", RED]
    fig, ax = plt.subplots(figsize=(12, 6.75), facecolor=BG)
    ax.set_facecolor(BG)
    bars = ax.bar(items, values, color=colors, width=0.58)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 2,
            f"{val}%",
            ha="center",
            va="bottom",
            color=INK,
            fontsize=12,
            fontweight="bold",
        )
    ax.set_ylim(0, 65)
    ax.set_ylabel("预计降低比例")
    ax.set_title("图2 降本增效来源拆解：主要来自少走弯路和自动整理", loc="left", fontsize=18, color=INK, pad=16)
    fig.text(
        0.06,
        0.035,
        "内部试算口径：仅统计方案探索、小试设计、材料消耗和文档整理，不包含真实产线自动控制收益。",
        color=MUTED,
        fontsize=10,
    )
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    clean(ax)
    plt.tight_layout(rect=(0, 0.06, 1, 1), pad=2)
    save(fig, "chart-2-cost-reduction.png")


def chart_confidence_layers():
    labels = ["当前方案评分", "论文锚点可信度", "产线适配可信度", "真实生产可信度"]
    scores = [84, 78, 76, 58]
    notes = ["可用于方案筛选", "依赖论文与模拟增强", "受设备档案完整度影响", "等待真实实验回填"]
    fig, ax = plt.subplots(figsize=(12, 6.75), facecolor=BG)
    ax.set_facecolor(BG)
    y = np.arange(len(labels))
    ax.barh(y, scores, color=[GREEN, BLUE, AMBER, RED], height=0.5)
    for i, (score, note) in enumerate(zip(scores, notes)):
        ax.text(score + 1.5, i, f"{score}/100  {note}", va="center", color=INK, fontsize=11)
    ax.axvspan(0, 60, color=RED, alpha=0.08)
    ax.axvspan(60, 80, color=AMBER, alpha=0.10)
    ax.axvspan(80, 100, color=GREEN, alpha=0.10)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("置信度分值")
    ax.set_title("图3 置信度分层：第一版可做研发建议，不能直接替代真实生产验证", loc="left", fontsize=18, color=INK, pad=16)
    fig.text(
        0.06,
        0.035,
        "汇报口径建议：系统方案置信度约 76-88/100；真实生产置信度目前约 55-65/100，需实验回填后提升。",
        color=MUTED,
        fontsize=10,
    )
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    clean(ax)
    plt.tight_layout(rect=(0, 0.06, 1, 1), pad=2)
    save(fig, "chart-3-confidence-layers.png")


def chart_model_performance():
    metrics = ["功能产物预测", "结构/稳定性预测", "风险识别", "大模型建议效率"]
    current = [86.1, 69.7, 72, 80]
    target = [90, 82, 85, 92]
    x = np.arange(len(metrics))
    width = 0.34
    fig, ax = plt.subplots(figsize=(12, 6.75), facecolor=BG)
    ax.set_facecolor(BG)
    ax.bar(x - width / 2, current, width, label="当前第一版", color=GREEN)
    ax.bar(x + width / 2, target, width, label="真实数据回填后目标", color=LIGHT_GREEN, edgecolor=GREEN, linewidth=1)
    for i, (cur, tgt) in enumerate(zip(current, target)):
        ax.text(i - width / 2, cur + 1.8, f"{cur:g}", ha="center", color=INK, fontsize=10)
        ax.text(i + width / 2, tgt + 1.8, f"{tgt:g}", ha="center", color=INK, fontsize=10)
    ax.set_xticks(x, metrics)
    ax.set_ylim(0, 105)
    ax.set_ylabel("性能指标 / 100 或 R²×100")
    ax.set_title("图4 模型性能现状与提升空间：数学模型为主，大模型做解释增效", loc="left", fontsize=18, color=INK, pad=16)
    fig.text(
        0.06,
        0.035,
        "当前口径：功能产物模型 R²=0.861；结构/稳定性模型 R²=0.697；大模型尚未写入密钥时只展示接口状态。",
        color=MUTED,
        fontsize=10,
    )
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.legend(loc="lower right", frameon=False)
    clean(ax)
    plt.tight_layout(rect=(0, 0.06, 1, 1), pad=2)
    save(fig, "chart-4-model-performance.png")


if __name__ == "__main__":
    chart_efficiency_cycle()
    chart_cost_reduction()
    chart_confidence_layers()
    chart_model_performance()
