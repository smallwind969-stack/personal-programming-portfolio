import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Presentation, PresentationFile } from "file:///C:/Users/LSY/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const finalDir = path.join(root, "docs", "final");
const scratch = path.join(root, "docs", "final", "ppt_scratch_lung_agent");
const tmpDir = path.join(scratch, "tmp");
const previewDir = path.join(tmpDir, "preview");
const qaDir = path.join(tmpDir, "qa");
const finalPptx = path.join(finalDir, "肺结节检测Agent_大创结题答辩PPT.pptx");
const qaReport = path.join(finalDir, "肺结节检测Agent_大创结题答辩PPT_QA.md");

const W = 1280;
const H = 720;
const page = { left: 62, top: 48, width: 1156, height: 624 };
const colors = {
  bg: "#F7FAFC",
  ink: "#17212B",
  muted: "#5B6975",
  faint: "#DCE5EC",
  panel: "#FFFFFF",
  navy: "#12395A",
  teal: "#0E766E",
  cyan: "#3AA7C7",
  amber: "#D99027",
  red: "#B64A4A",
};

function rel(p) {
  return path.relative(root, p).replaceAll("\\", "/");
}

async function ensureDirs() {
  await fs.mkdir(finalDir, { recursive: true });
  await fs.mkdir(previewDir, { recursive: true });
  await fs.mkdir(qaDir, { recursive: true });
}

async function exists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

function addText(slide, text, x, y, w, h, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontSize: style.fontSize ?? 22,
    bold: style.bold ?? false,
    color: style.color ?? colors.ink,
    alignment: style.alignment ?? "left",
  };
  return shape;
}

function addTitle(slide, title, eyebrow = "大创结题冲刺材料") {
  addText(slide, eyebrow, page.left, 30, 420, 26, {
    fontSize: 14,
    bold: true,
    color: colors.teal,
  });
  addText(slide, title, page.left, 62, 880, 55, {
    fontSize: 34,
    bold: true,
    color: colors.navy,
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: page.left, top: 126, width: 74, height: 5 },
    fill: colors.amber,
    line: { style: "solid", fill: colors.amber, width: 0 },
  });
}

function addFooter(slide, n, source = "数据来源：本项目工作区实验文件；公开规范：LUNA16 / CLAIM 2024 / TRIPOD+AI") {
  addText(slide, source, page.left, 684, 980, 18, {
    fontSize: 10,
    color: colors.muted,
  });
  addText(slide, String(n).padStart(2, "0"), 1170, 680, 44, 22, {
    fontSize: 13,
    bold: true,
    color: colors.navy,
    alignment: "right",
  });
}

function panel(slide, x, y, w, h, fill = colors.panel, line = colors.faint) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: 1 },
    borderRadius: 8,
  });
}

function metric(slide, label, value, hint, x, y, w, accent = colors.teal) {
  panel(slide, x, y, w, 118);
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: 7, height: 118 },
    fill: accent,
    line: { style: "solid", fill: accent, width: 0 },
  });
  addText(slide, value, x + 22, y + 18, w - 36, 42, {
    fontSize: 32,
    bold: true,
    color: colors.navy,
  });
  addText(slide, label, x + 22, y + 62, w - 36, 24, {
    fontSize: 17,
    bold: true,
    color: colors.ink,
  });
  addText(slide, hint, x + 22, y + 88, w - 36, 20, {
    fontSize: 12,
    color: colors.muted,
  });
}

function bullets(slide, items, x, y, w, h, opts = {}) {
  const text = items.map((v) => `• ${v}`).join("\n");
  return addText(slide, text, x, y, w, h, {
    fontSize: opts.fontSize ?? 20,
    color: opts.color ?? colors.ink,
  });
}

async function image(slide, source, x, y, w, h, alt, fit = "contain") {
  if (!(await exists(source))) {
    panel(slide, x, y, w, h, "#FFF8EF", "#EDC98F");
    addText(slide, `图表缺失：${rel(source)}`, x + 18, y + h / 2 - 20, w - 36, 40, {
      fontSize: 18,
      color: colors.red,
      alignment: "center",
    });
    return false;
  }
  const blob = await fs.readFile(source);
  slide.images.add({
    blob,
    contentType: "image/png",
    alt,
    fit,
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: 8,
  });
  return true;
}

function setNotes(slide, lines) {
  slide.speakerNotes.textFrame.setText(lines);
  slide.speakerNotes.setVisible(true);
}

function makeSlide(prs, title, eyebrow, n, source) {
  const slide = prs.slides.add();
  slide.background.fill = colors.bg;
  addTitle(slide, title, eyebrow);
  addFooter(slide, n, source);
  return slide;
}

async function writeBlob(p, blob) {
  await fs.writeFile(p, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await ensureDirs();
  const prs = Presentation.create({ slideSize: { width: W, height: H } });
  const figures = {
    caseInventory: path.join(root, "docs", "research_loop", "figures", "fig_case_inventory.png"),
    fpred: path.join(root, "docs", "world_frontier", "luna16", "patch_test_103", "metrics", "fpred_publication_validation.png"),
    froc: path.join(root, "docs", "world_frontier", "luna16", "subset0_full_candidates_stream", "froc", "fpred_subset0_candidates_v2_froc.png"),
    split: path.join(root, "docs", "world_frontier", "luna16", "subset0_full_candidates_stream", "calibration_split", "split_valid_nms.png"),
    ci: path.join(root, "docs", "world_frontier", "luna16", "subset0_full_candidates_stream", "calibration_split", "evaluation_nms_sweep", "radius_10", "bootstrap", "froc_bootstrap_ci.png"),
  };

  let s = prs.slides.add();
  s.background.fill = colors.navy;
  addText(s, "肺结节检测/标注与随访 Agent 系统", 70, 92, 980, 80, {
    fontSize: 43,
    bold: true,
    color: "#FFFFFF",
  });
  addText(s, "大创结题答辩材料｜基于本地系统闭环与 LUNA16 subset0 公开数据验证", 74, 182, 1000, 44, {
    fontSize: 23,
    color: "#E7F2F5",
  });
  metric(s, "subset0 evaluation fixed 10 mm NMS", "CPM 0.6888", "95% CI 0.6026-0.7804", 78, 330, 320, colors.teal);
  metric(s, "独立候选分类测试", "AUC 0.9926", "series-level bootstrap CI 0.9731-1.0000", 430, 330, 320, colors.cyan);
  metric(s, "完整 candidates_V2 桥接", "79,135", "89 series / 112 annotations", 782, 330, 320, colors.amber);
  addText(s, "项目成员/指导教师/学院信息：待按学校模板补充", 76, 630, 840, 24, {
    fontSize: 14,
    color: "#D7E4EA",
  });
  addFooter(s, 1, "本页指标来自工作区 docs/world_frontier 系列实验报告；未写入未确认团队信息");
  setNotes(s, [
    "开场强调：本材料不是堆文字，而是把已有系统、实验、统计验证和结题提交物组织成可答辩的证据链。",
    "主动声明边界：当前公共验证为 LUNA16 subset0 内分区验证，不宣称完整 LUNA16 官方领先。",
  ]);

  s = makeSlide(prs, "项目从“演示系统”升级为可复现实验闭环", "01 项目定位", 2);
  bullets(s, [
    "临床场景：胸部 CT 中肺结节候选点多，低假阳性区间的检出稳定性是关键。",
    "工程场景：需要把检测、标注、医生复核、随访建议和实验记录接成闭环。",
    "结题策略：用本地病例证明系统链路，用 LUNA16 subset0 证明公开数据上的可复现实验能力。",
    "科研边界：所有性能结论绑定数据分区、候选池和评估脚本，不把阶段性结果包装成临床结论。",
  ], page.left, 168, 690, 280);
  metric(s, "本地病例闭环", "3 cases", "607 DICOM slices", 805, 166, 320, colors.teal);
  metric(s, "医生复核代理参考", "11 nodules", "7 model + 4 doctor-added", 805, 300, 320, colors.cyan);
  metric(s, "公开 benchmark 子集", "89 CT", "LUNA16 subset0", 805, 434, 320, colors.amber);
  setNotes(s, ["这一页给评委建立判断框架：不是只讲模型，而是讲可落地系统加可复现实验。"]);

  s = makeSlide(prs, "系统架构：检测模型、人工复核与随访 Agent 进入同一工作流", "02 系统闭环", 3);
  const steps = [
    ["CT/DICOM", "病例导入与切片管理"],
    ["候选检测", "3D VNet 候选生成"],
    ["FPRED", "ResNet-CBAM 假阳性抑制"],
    ["人工复核", "医生新增/确认/修正"],
    ["随访 Agent", "风险字段检查与建议生成"],
    ["科研闭环", "FROC/CPM、CI、报告/PPT"],
  ];
  steps.forEach((st, i) => {
    const x = 88 + (i % 3) * 372;
    const y = 176 + Math.floor(i / 3) * 185;
    panel(s, x, y, 300, 112);
    addText(s, st[0], x + 22, y + 20, 240, 34, { fontSize: 24, bold: true, color: colors.navy });
    addText(s, st[1], x + 22, y + 62, 250, 30, { fontSize: 17, color: colors.muted });
  });
  addText(s, "核心升级不是单点模型，而是“检测-复核-建议-评估-材料化”的闭环能力。", 94, 566, 960, 36, {
    fontSize: 24,
    bold: true,
    color: colors.teal,
  });
  setNotes(s, ["把技术路线说成闭环：每一步都有输入、输出和可审计文件。"]);

  s = makeSlide(prs, "本地病例闭环用于证明系统能运行，但不冒充临床验证", "03 本地证据", 4);
  await image(s, figures.caseInventory, 74, 162, 620, 392, "本地病例清单图");
  bullets(s, [
    "已有本地 3 例病例、607 张 DICOM 切片纳入研究闭环。",
    "以医生复核代理参考进行系统链路检查：11 个参考结节，模型 7 个预测，医生补充 4 个。",
    "proxy precision = 1.0000，proxy recall = 0.6364；该指标用于系统调试，不作为真实临床性能声明。",
  ], 740, 174, 420, 230, { fontSize: 19 });
  metric(s, "review-proxy CPM", "0.6364", "本地闭环调试指标", 748, 430, 330, colors.teal);
  setNotes(s, ["强调审慎：本地病例是演示和工作流证据，真实泛化看公开数据。"]);

  s = makeSlide(prs, "随访 Agent 的价值在于结构化补全和安全审计", "04 Agent 升级", 5);
  bullets(s, [
    "输入端检查结节大小、密度、数量、风险因素、既往影像等随访关键字段。",
    "输出端生成可解释随访建议，同时保留缺失字段提示，避免过度确定。",
    "安全审计按病例运行，当前工作区记录显示 3 例审计无 failed 项。",
    "定位为医生辅助与科研材料自动化，不替代临床诊断。",
  ], 86, 174, 545, 290, { fontSize: 20 });
  const guardrails = [
    ["不编造", "缺失风险字段时显式提示"],
    ["可追溯", "建议与病例字段绑定"],
    ["可审计", "输出安全检查 JSON"],
  ];
  guardrails.forEach((g, i) => {
    metric(s, g[0], g[1], i === 2 ? "docs/world_frontier/agent_safety" : "Agent 输出规则", 696, 168 + i * 138, 410, [colors.teal, colors.cyan, colors.amber][i]);
  });
  setNotes(s, ["这一页把 Agent 从聊天功能提升为医疗 AI 安全边界的一部分。"]);

  s = makeSlide(prs, "公共数据验证以 LUNA16 subset0 为当前主线", "05 公开数据", 6);
  bullets(s, [
    "LUNA16 官方挑战聚焦 LIDC-IDRI 上的肺结节自动检测评估；官方数据页说明共 888 个 CT。",
    "当前工作区已完成 subset0 89 个 CT series 的完整 candidates_V2 候选池 FPRED 评分。",
    "subset0 内含 112 个官方 annotations；全量候选池导出 79,135 条预测。",
    "结题表述坚持写“subset0 内分区验证”，不写成完整 LUNA16 官方成绩。",
  ], 80, 166, 670, 310, { fontSize: 20 });
  metric(s, "LUNA16 subset0", "89 series", "公开 CT 子集", 812, 170, 320, colors.teal);
  metric(s, "官方 annotations", "112", "subset0 范围", 812, 304, 320, colors.cyan);
  metric(s, "FPRED predictions", "79,135", "candidates_V2 全候选池", 812, 438, 320, colors.amber);
  setNotes(s, ["这页是评委最容易认可的外部基准入口：公开数据、公开评估逻辑、明确边界。"]);

  s = makeSlide(prs, "FPRED 分支在独立候选测试上达到高区分度", "06 候选分类", 7);
  await image(s, figures.fpred, 62, 150, 690, 445, "FPRED validation and independent test figure");
  metric(s, "AUC", "0.9926", "95% CI 0.9731-1.0000", 805, 160, 315, colors.teal);
  metric(s, "Sensitivity", "0.8571", "threshold 0.30", 805, 295, 315, colors.cyan);
  metric(s, "Specificity", "0.9792", "threshold 0.30", 805, 430, 315, colors.amber);
  addText(s, "独立测试：103 candidates，其中阳性 7、阴性 96；CI 使用 seriesuid 重采样。", 802, 568, 360, 42, {
    fontSize: 15,
    color: colors.muted,
  });
  setNotes(s, ["注意解释：这个 AUC 是候选分类，不是端到端检测最终指标。"]);

  s = makeSlide(prs, "完整候选池 FROC 把模型从分类推向检测评估", "07 FROC 桥接", 8);
  await image(s, figures.froc, 72, 150, 710, 444, "subset0 candidates_V2 FROC");
  bullets(s, [
    "raw bridge CPM = 0.6020。",
    "0.125 FP/scan sensitivity = 0.2143；0.25 FP/scan sensitivity = 0.2589。",
    "高 FP/scan 区间 sensitivity > 0.92，提示主要短板在低假阳性区间。",
    "该结论直接引出后处理和 hard negative mining 的必要性。",
  ], 824, 166, 348, 330, { fontSize: 18 });
  setNotes(s, ["从这一页开始进入真正答辩核心：低 FP 区间是检测系统实用价值的关键。"]);

  s = makeSlide(prs, "NMS 半径只在 calibration 上选择，再固定到 evaluation 报告", "08 调参与验证分离", 9);
  await image(s, figures.split, 64, 150, 690, 450, "split-valid NMS figure");
  metric(s, "calibration", "55 series", "56 annotations", 805, 158, 315, colors.teal);
  metric(s, "evaluation", "34 series", "56 annotations", 805, 292, 315, colors.cyan);
  metric(s, "selected radius", "10 mm", "仅在 calibration 选择", 805, 426, 315, colors.amber);
  setNotes(s, ["主动说明为什么不用 evaluation 上事后更高的半径：防止调参乐观偏倚。"]);

  s = makeSlide(prs, "固定 10 mm NMS 在 evaluation split 上带来可量化提升", "09 关键结果", 10);
  const xs = [84, 386, 688, 990];
  metric(s, "No NMS CPM", "0.6199", "evaluation split", xs[0], 170, 230, colors.muted);
  metric(s, "10 mm NMS CPM", "0.6888", "+0.0689 absolute", xs[1], 170, 230, colors.teal);
  metric(s, "No NMS Sens", "0.3214", "@0.25 FP/scan", xs[2], 170, 230, colors.muted);
  metric(s, "10 mm NMS Sens", "0.4821", "+0.1607 absolute", xs[3], 170, 230, colors.amber);
  panel(s, 112, 365, 1000, 150, "#EFF8F7", "#C7E5DF");
  addText(s, "结题可讲的硬结论", 145, 392, 260, 32, { fontSize: 24, bold: true, color: colors.navy });
  addText(s, "在 subset0 内按 annotation 数平衡划分 calibration/evaluation 后，10 mm NMS 是预先从 calibration 选出的固定后处理；它在 evaluation 上提升 CPM 与低 FP/scan sensitivity。", 145, 438, 900, 54, {
    fontSize: 22,
    color: colors.ink,
  });
  setNotes(s, ["这一页可以作为汇报的中心页。说清楚分区、固定参数和提升幅度。"]);

  s = makeSlide(prs, "置信区间让结论更像科研，而不是单次跑分", "10 不确定性报告", 11);
  await image(s, figures.ci, 68, 150, 690, 448, "FROC bootstrap confidence interval");
  metric(s, "CPM", "0.6888", "95% CI 0.6026-0.7804", 805, 164, 325, colors.teal);
  metric(s, "Sens @0.25", "0.4821", "95% CI 0.2833-0.6545", 805, 300, 325, colors.amber);
  metric(s, "Bootstrap", "1000", "series-level resampling", 805, 436, 325, colors.cyan);
  setNotes(s, ["说明为什么按 series 重采样：同一 CT 内候选点不是独立样本。"]);

  s = makeSlide(prs, "创新点集中在可复现闭环，而不是空泛地堆模型名", "11 创新与贡献", 12);
  const innovation = [
    ["闭环系统", "检测、标注、复核、随访建议与实验记录贯通"],
    ["科研评估", "LUNA16-style FROC/CPM、分区验证、bootstrap CI"],
    ["工程能力", "流式 candidates_V2 评分、断点续跑、NMS sweep"],
    ["安全边界", "Agent 输出缺失字段提示与审计记录"],
  ];
  innovation.forEach((it, i) => {
    const x = 90 + (i % 2) * 550;
    const y = 168 + Math.floor(i / 2) * 190;
    panel(s, x, y, 465, 132);
    addText(s, it[0], x + 24, y + 24, 200, 34, { fontSize: 25, bold: true, color: colors.navy });
    addText(s, it[1], x + 24, y + 70, 390, 42, { fontSize: 19, color: colors.ink });
  });
  setNotes(s, ["这一页把创新点写成可验证产物，避免答辩时被问住。"]);

  s = makeSlide(prs, "结题材料应主动承认边界，并给出下一步实验路线", "12 局限与路线", 13);
  bullets(s, [
    "当前公共验证为 LUNA16 subset0，不是完整 888 CT 官方提交成绩。",
    "candidates_V2 桥接仍不等同于端到端 VNet+FPRED 全流程官方评估。",
    "低 FP/scan 区间 CI 较宽，需扩展到 subset1/subset2，并进行固定 10 mm 外部验证。",
    "下一步建议：hard negative mining、概率校准、更多子集验证、消融实验和最终论文格式化。",
  ], 90, 168, 760, 290, { fontSize: 21 });
  panel(s, 910, 170, 230, 260, "#FFF7E8", "#EDC98F");
  addText(s, "答辩口径", 938, 200, 170, 34, { fontSize: 25, bold: true, color: colors.navy });
  addText(s, "我们已经完成可复现实验闭环，下一阶段目标是从 subset0 扩展到多子集固定验证。", 938, 256, 150, 124, {
    fontSize: 20,
    color: colors.ink,
  });
  setNotes(s, ["有边界反而更可信。把局限讲成路线，不讲成失败。"]);

  s = makeSlide(prs, "一周汇报建议：先展示系统，再用三张证据图压实结果", "13 汇报结构", 14);
  const agenda = [
    ["1", "系统演示", "上传 CT、查看候选、医生复核、Agent 建议"],
    ["2", "本地闭环", "3 cases / 607 slices / review-proxy evidence"],
    ["3", "公开验证", "FPRED AUC、subset0 FROC、split-valid NMS"],
    ["4", "结题提交", "报告、PPT、实验索引、脚本、图表、系统说明"],
  ];
  agenda.forEach((a, i) => {
    panel(s, 96, 160 + i * 104, 960, 78);
    addText(s, a[0], 124, 178 + i * 104, 42, 34, { fontSize: 28, bold: true, color: colors.amber, alignment: "center" });
    addText(s, a[1], 190, 174 + i * 104, 190, 32, { fontSize: 24, bold: true, color: colors.navy });
    addText(s, a[2], 410, 178 + i * 104, 560, 30, { fontSize: 19, color: colors.ink });
  });
  setNotes(s, ["这页可以直接作为下周汇报排练提纲。"]);

  s = makeSlide(prs, "结题提交清单：先补齐可交付物，再继续冲论文", "14 提交包", 15);
  bullets(s, [
    "结题报告：系统背景、方法、实验、创新点、贡献分工、局限与下一步。",
    "答辩 PPT：本文件，可按学校模板继续替换封面和页脚。",
    "演示材料：Flask 系统启动说明、病例演示流程、截图或录屏。",
    "实验附件：docs/world_frontier/experiment_index.md、核心 CSV/JSON、FROC 图、CI 图。",
    "论文预稿：现有中文投稿预稿继续按 CLAIM/TRIPOD+AI 补齐披露项。",
  ], 94, 164, 780, 330, { fontSize: 21 });
  metric(s, "当前优先级", "PPT + 报告", "半个月截止", 928, 174, 260, colors.teal);
  metric(s, "证据底座", "55 tests", "最新测试全部通过", 928, 310, 260, colors.cyan);
  metric(s, "下一产物", "讲稿", "按 8-10 分钟压缩", 928, 446, 260, colors.amber);
  setNotes(s, ["收尾要让评委感觉项目有交付、有实验、有边界、有下一步。"]);

  const sourceNotes = [
    "肺结节检测/标注与随访 Agent 系统结题答辩 PPT 来源记录",
    "",
    "本地来源：",
    "- docs/world_frontier/luna16_evaluation_froc_bootstrap_ci_report.md：evaluation fixed 10 mm NMS CPM、CI、bootstrap 设置。",
    "- docs/world_frontier/luna16_subset0_split_valid_nms_report.md：calibration/evaluation 分区、固定 10 mm NMS 提升。",
    "- docs/world_frontier/luna16/patch_test_103/metrics/bootstrap_summary.json：FPRED 独立测试 AUC、sensitivity、specificity 和 CI。",
    "- docs/research_loop/：本地病例闭环、review-proxy 指标和病例清单图。",
    "- docs/world_frontier/experiment_index.md：实验索引和产物路径。",
    "",
    "公开来源：",
    "- LUNA16 Grand Challenge Data page: https://luna16.grand-challenge.org/Data/",
    "- CLAIM 2024 Update: https://pubs.rsna.org/doi/abs/10.1148/ryai.240300",
    "- TRIPOD+AI statement: https://www.bmj.com/content/385/bmj-2023-078378",
    "",
    "重要边界：本 PPT 不宣称完整 LUNA16 官方成绩；所有公共性能表述均限定为 subset0 或 subset0 evaluation split。",
  ].join("\n");
  await fs.writeFile(path.join(tmpDir, "source-notes.txt"), sourceNotes, "utf8");

  const previews = [];
  for (const [index, slide] of prs.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(previewDir, `${stem}.png`), await prs.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(path.join(previewDir, `${stem}.layout.json`), await (await slide.export({ format: "layout" })).text());
    previews.push(`${stem}.png`);
  }
  await writeBlob(path.join(previewDir, "deck-montage.webp"), await prs.export({ format: "webp", montage: true, scale: 1 }));
  await (await PresentationFile.exportPptx(prs)).save(finalPptx);

  const inspect = await prs.inspect({ kind: "slide,textbox,shape,image,notes", maxChars: 12000 });
  await fs.writeFile(path.join(qaDir, "inspect.ndjson"), inspect.ndjson, "utf8");
  const qa = [
    "# 肺结节检测 Agent 大创结题答辩 PPT QA",
    "",
    `- PPTX：${rel(finalPptx)}`,
    `- slide count：${prs.slides.items.length}`,
    `- preview dir：${rel(previewDir)}`,
    `- montage：${rel(path.join(previewDir, "deck-montage.webp"))}`,
    `- source notes：${rel(path.join(tmpDir, "source-notes.txt"))}`,
    "",
    "## 自检结论",
    "",
    "- 已使用可编辑文本框、形状、指标卡与嵌入式图表图片；未使用整页截图作为幻灯片。",
    "- 已为每页写入 speaker notes。",
    "- 关键科研数字均来自工作区现有报告/JSON；未知团队与导师信息保留为待补充。",
    "- 已渲染每页 PNG 与整套 montage，用于后续视觉复核。",
    "",
    "## 已知边界",
    "",
    "- deck 未套用学校官方模板；后续拿到模板后可做 template-following 版本。",
    "- 当前公共验证限定为 LUNA16 subset0 / subset0 evaluation split，不能表述为完整 LUNA16 官方成绩。",
  ].join("\n");
  await fs.writeFile(qaReport, qa, "utf8");
  console.log(JSON.stringify({ finalPptx, qaReport, slideCount: prs.slides.items.length, previews }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
