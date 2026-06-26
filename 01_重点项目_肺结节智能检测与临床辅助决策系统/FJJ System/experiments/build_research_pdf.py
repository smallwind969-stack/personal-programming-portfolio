import csv
from datetime import datetime
from pathlib import Path
from textwrap import wrap

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research_loop"
FIG = DOCS / "figures"
OUT = ROOT / "docs" / "final"


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "axes.spines.right": False,
    "axes.spines.top": False,
})


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def add_title(ax, title, subtitle=None):
    ax.text(0.06, 0.93, title, fontsize=19, fontweight="bold", va="top")
    if subtitle:
        ax.text(0.06, 0.875, subtitle, fontsize=10, color="#555555", va="top")


def add_wrapped(ax, text, x, y, width_chars=48, fontsize=10, line_gap=0.036, color="#111111"):
    yy = y
    for para in text.split("\n"):
        if not para.strip():
            yy -= line_gap
            continue
        for line in wrap(para, width=width_chars):
            ax.text(x, yy, line, fontsize=fontsize, color=color, va="top")
            yy -= line_gap
    return yy


def add_bullets(ax, items, x, y, width_chars=44, fontsize=10):
    yy = y
    for item in items:
        lines = wrap(item, width=width_chars)
        ax.text(x, yy, "•", fontsize=fontsize, va="top")
        ax.text(x + 0.025, yy, lines[0], fontsize=fontsize, va="top")
        yy -= 0.036
        for line in lines[1:]:
            ax.text(x + 0.025, yy, line, fontsize=fontsize, va="top")
            yy -= 0.036
        yy -= 0.008
    return yy


def table_page(pdf, title, subtitle, columns, rows, note=None):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    add_title(ax, title, subtitle)
    table_data = [[row.get(c, "") for c in columns] for row in rows]
    table = ax.table(
        cellText=table_data,
        colLabels=columns,
        cellLoc="center",
        colLoc="center",
        bbox=[0.06, 0.30, 0.88, 0.48],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    for (r, _c), cell in table.get_celld().items():
        cell.set_edgecolor("#d9d9d9")
        if r == 0:
            cell.set_facecolor("#e8f1f7")
            cell.set_text_props(fontweight="bold")
    if note:
        add_wrapped(ax, note, 0.06, 0.23, width_chars=54, fontsize=9, color="#555555")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def figure_page(pdf, title, subtitle, image_path, caption):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    add_title(ax, title, subtitle)
    img = Image.open(image_path)
    ax_img = fig.add_axes([0.07, 0.32, 0.86, 0.48])
    ax_img.imshow(img)
    ax_img.axis("off")
    add_wrapped(ax, caption, 0.08, 0.25, width_chars=56, fontsize=9, color="#333333")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def plot_real_detection_sweep(rows):
    if not rows:
        return None
    by_patient = {}
    for row in rows:
        by_patient.setdefault(row["patient_id"], []).append(row)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for patient, patient_rows in by_patient.items():
        patient_rows = sorted(patient_rows, key=lambda r: float(r["prob_threshold"]))
        x = [float(r["prob_threshold"]) for r in patient_rows]
        y = [int(float(r["finding_count"])) for r in patient_rows]
        axes[0].plot(x, y, marker="o", label=patient)
    axes[0].set_title("Real rerun: candidate count")
    axes[0].set_xlabel("VNet probability threshold")
    axes[0].set_ylabel("Finding count")
    axes[0].legend(frameon=False)

    labels = [f'{r["patient_id"]}\n{r["prob_threshold"]}' for r in rows]
    times = [float(r["total_detect_sec"]) for r in rows]
    axes[1].bar(range(len(rows)), times, color="#9ecae1")
    axes[1].set_title("CPU inference time")
    axes[1].set_ylabel("Total detect time (s)")
    axes[1].set_xticks(range(len(rows)))
    axes[1].set_xticklabels(labels, rotation=25, ha="right", fontsize=7)
    fig.tight_layout()
    out = FIG / "fig_real_detection_sweep.png"
    fig.savefig(out, dpi=600, bbox_inches="tight")
    fig.savefig(FIG / "fig_real_detection_sweep.pdf", bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = read_csv(DOCS / "case_manifest.csv")
    eval_rows = read_csv(DOCS / "review_proxy_evaluation_by_case.csv")
    sweep_rows = read_csv(DOCS / "threshold_sweep.csv")
    detect_rows = read_csv(DOCS / "detection_sweep_runs.csv")
    real_fig = plot_real_detection_sweep(detect_rows)

    pdf_path = OUT / "肺结节智能检测系统_科研闭环阶段性报告.pdf"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    with PdfPages(pdf_path) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        add_title(
            ax,
            "肺结节智能检测系统：科研闭环阶段性报告",
            f"面向大创结题与论文雏形的实验记录 | 生成时间：{now}",
        )
        add_wrapped(
            ax,
            "本报告不是简单文字堆叠，而是基于当前本地系统、DICOM 病例、医生复核记录和真实模型重跑结果形成的阶段性研究证据包。"
            "报告坚持两个原则：第一，只写已经由脚本或系统日志支撑的结果；第二，凡是尚未达到临床验证标准的指标，均标注为 review-proxy 或工程实验指标。",
            0.06,
            0.78,
            width_chars=49,
            fontsize=11,
        )
        add_bullets(
            ax,
            [
                "研究对象：基于三阶段深度学习的人机协同肺结节检测与复核系统。",
                "系统链路：Attention V-Net 候选生成、3D ResNet-CBAM 假阳性过滤、双分支良恶性识别，以及 Agent 随访建议。",
                "当前证据：3 个病例、607 张 DICOM、2 个已有复核记录病例、11 个 review-proxy 参考结节。",
                "核心发现：保存复核记录上的代理召回率为 0.6364；真实重跑显示阈值 0.10 到 0.15 会减少候选数，0.15 到 0.20 基本稳定。",
                "结论边界：当前结果可支撑大创结题和后续论文实验设计，但不能直接宣称临床敏感性、特异性或外部验证性能。",
            ],
            0.08,
            0.61,
            width_chars=45,
            fontsize=10,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        add_title(ax, "1. 科研闭环设计", "从系统演示升级为可复现实验")
        add_wrapped(
            ax,
            "本项目的科研闭环由五个环节构成：病例索引、模型推理、医生复核、阈值实验、论文图表与报告生成。"
            "其中病例索引负责固定研究对象；模型推理负责生成候选结节；医生复核记录用于构建阶段性 review-proxy 参考集；"
            "阈值实验用于观察候选数量、代理召回和运行时间的变化；最终由脚本自动导出 CSV、JSON、Markdown 和 PDF 图表。",
            0.06,
            0.80,
            width_chars=50,
            fontsize=10,
        )
        steps = [
            ("病例索引", "扫描 uploads 与 case_context，生成 case_manifest.csv。"),
            ("模型推理", "通过 /detect 接口运行 3D 检测，并记录 VNet 阈值、ResNet 阈值与耗时。"),
            ("医生复核", "读取 doctor_review.json，将模型发现与医生补充结节合并为阶段性参考。"),
            ("实验评估", "计算 review-proxy precision、recall、TP、FP、FN，并生成阈值扫描表。"),
            ("论文产物", "输出可复现图表、实验表格和中文 PDF 阶段性报告。"),
        ]
        y = 0.58
        for idx, (name, desc) in enumerate(steps, start=1):
            ax.text(0.10, y, f"{idx}", fontsize=12, fontweight="bold", color="#1f77b4", va="top")
            ax.text(0.15, y, name, fontsize=11, fontweight="bold", va="top")
            ax.text(0.15, y - 0.035, desc, fontsize=9.5, va="top", color="#333333")
            if idx < len(steps):
                ax.annotate("", xy=(0.115, y - 0.11), xytext=(0.115, y - 0.055), arrowprops=dict(arrowstyle="->", lw=1, color="#777777"))
            y -= 0.13
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        table_page(
            pdf,
            "2. 当前病例与复核数据",
            "病例清单是后续所有实验的固定输入。",
            ["patient_id", "dicom_count", "model_finding_count", "doctor_added_count", "has_processed_output"],
            manifest,
            "说明：doctor_added_count 来自本地医生复核记录，当前仍属于小样本阶段。报告中的 proxy 指标只能作为工程闭环评估，不能替代正式临床标注集。",
        )

        figure_page(
            pdf,
            "3. 病例清点图",
            "展示每个病例的 DICOM 数量、模型记录和医生补充记录。",
            FIG / "fig_case_inventory.png",
            "该图说明当前数据规模仍然有限，但已经具备完整闭环所需的关键对象：原始影像、模型输出和复核记录。",
        )

        table_page(
            pdf,
            "4. Review-proxy 评估结果",
            "以当前保存的医生复核记录构建阶段性参考集。",
            ["patient_id", "reference_nodules", "model_predictions", "tp_proxy", "fp_proxy", "fn_proxy", "precision_proxy", "recall_proxy"],
            eval_rows,
            "结果解读：总体代理精确率为 1.0000，代理召回率为 0.6364。该结果不应被包装为临床性能，而应被用于指导下一轮补标注和召回优化。",
        )

        figure_page(
            pdf,
            "5. 保存复核记录上的阈值扫描",
            "该实验读取已保存记录，不重复运行深度模型。",
            FIG / "fig_threshold_sweep.png",
            "当保存记录中的候选概率阈值升高到 0.95 以上时，代理召回率明显下降，说明过高阈值会损失已复核到的阳性结节。",
        )

        if detect_rows:
            table_page(
                pdf,
                "6. 真实模型重跑实验",
                "通过 Flask /detect 接口重新运行 3D 模型得到的真实耗时与候选数。",
                ["patient_id", "prob_threshold", "resnet_threshold", "finding_count", "candidate_count_before_filter", "candidate_count_after_filter", "total_detect_sec"],
                detect_rows[-8:],
                "结果解读：蔡惠平病例在 prob_threshold=0.10 时得到 7 个候选，0.15 与 0.20 时得到 5 个候选；包书木病例在默认阈值 0.15 下得到 6 个候选。单次 CPU 推理约 229 至 316 秒，性能瓶颈主要在 VNet 检测阶段。",
            )
            if real_fig:
                figure_page(
                    pdf,
                    "7. 真实重跑阈值与耗时图",
                    "候选数变化和 CPU 推理时间。",
                    real_fig,
                    "该图把工程可用性问题暴露出来：模型链路可以复现实验，但 CPU 推理较慢，后续需要缓存、GPU 部署或候选生成加速。",
                )

        figure_page(
            pdf,
            "8. 证据缺口",
            "面向论文投稿前必须补足的证据。",
            FIG / "fig_evidence_gap.png",
            "当前最大缺口不是文字表达，而是数据规模与标注完整性。下一阶段应优先完成所有病例的医生复核，并冻结病例列表后重新运行 FROC 风格评价。",
        )

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        add_title(ax, "9. 阶段性结论与下周汇报话术", "真实、克制、能经得起追问")
        add_bullets(
            ax,
            [
                "本项目已经从单纯系统展示升级为可复现实验闭环，能够自动产出病例清单、代理评估表、阈值扫描表和科研图。",
                "三阶段模型链路具备可运行性，真实重跑证明候选数量会随 VNet 概率阈值改变，阈值 0.15 在当前小样本中比 0.10 更克制。",
                "当前 review-proxy 结果显示召回不足，后续优化重点应放在补全复核标注、降低漏检和建立 FROC 分析，而不是继续堆系统功能。",
                "CPU 推理耗时较长，说明工程部署层面还需要模型缓存、GPU 加速或候选生成网络轻量化。",
                "结题报告可以强调：项目已经完成算法链路、医生复核界面、Agent 随访建议和科研闭环脚本，具备继续扩展为论文实验的基础。",
            ],
            0.08,
            0.78,
            width_chars=46,
            fontsize=10,
        )
        add_wrapped(
            ax,
            "建议下周汇报的核心句：我们没有把系统停留在演示层，而是建立了一个可复现实验闭环。当前小样本结果暴露出召回和推理效率问题，"
            "这反而为后续大创结题和论文工作提供了明确路线：补标注、跑阈值、做 FROC、做消融。",
            0.08,
            0.36,
            width_chars=48,
            fontsize=11,
            color="#111111",
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    print(pdf_path)


if __name__ == "__main__":
    main()
