import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.cwd();
const SKILL_DIR = "C:/Users/LSY/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const TMP_DIR = path.join(workspaceDir, "outputs", "ppt_build_social_value");
const IMAGE_DIR = path.join(workspaceDir, "outputs", "ppt_images", "social_value_split");

const { resolvePresentationFont } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href,
);

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(IMAGE_DIR, { recursive: true });

const family = resolvePresentationFont({ fontFamily: "Microsoft YaHei" });
const blue = "#1677E8";
const navy = "#05295F";
const ink = "#202B3A";
const pale = "#F6FAFF";
const cyan = "#16A4F5";
const green = "#10A579";
const red = "#B63131";

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function addText(slide, text, left, top, width, height, style = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    typeface: family,
    fontSize: 24,
    color: ink,
    autoFit: "shrinkText",
    ...style,
  };
  return box;
}

function addRule(slide, left, top, width, height, fill = blue) {
  slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: "none", width: 0 },
  });
}

function addBackground(slide) {
  slide.background.fill = "#EEF3FA";
  slide.shapes.add({
    geometry: "rect",
    position: { left: 80, top: 38, width: 1120, height: 626 },
    fill: "white/92",
    line: { style: "solid", fill: "#D6E4F6", width: 1 },
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 80, top: 90, width: 1120, height: 2 },
    fill: blue,
    line: { style: "solid", fill: "none", width: 0 },
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 80, top: 612, width: 1120, height: 10 },
    fill: blue,
    line: { style: "solid", fill: "none", width: 0 },
  });
  slide.shapes.add({
    geometry: "arc",
    position: { left: 30, top: 28, width: 130, height: 120 },
    fill: "none",
    line: { style: "solid", fill: "#8BD6FF", width: 8 },
  });
  addText(slide, "QIRA", 1114, 84, 60, 24, {
    fontSize: 16,
    color: blue,
    bold: true,
    italic: true,
    alignment: "center",
  });
  slide.shapes.add({
    geometry: "ellipse",
    position: { left: 1115, top: 48, width: 48, height: 48 },
    fill: "#E7F6FF",
    line: { style: "solid", fill: blue, width: 2 },
  });
}

function addHeader(slide, mainTitle, subtitle) {
  addText(slide, mainTitle, 160, 48, 170, 44, {
    fontSize: 36,
    bold: true,
    color: blue,
  });
  addText(slide, subtitle, 330, 57, 640, 32, {
    fontSize: 23,
    bold: true,
    color: "#333333",
  });
}

function addColumn(slide, left, top, width, title, lead, items) {
  addText(slide, title, left + 22, top, width - 44, 56, {
    fontSize: 40,
    bold: true,
    color: navy,
    alignment: "center",
  });
  addText(slide, lead, left + 30, top + 86, width - 60, 78, {
    fontSize: 25,
    bold: true,
    color: "#111827",
    alignment: "center",
    lineSpacing: 1.15,
  });
  items.forEach((item, index) => {
    const y = top + 186 + index * 88;
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: left + 36, top: y + 3, width: 38, height: 38 },
      fill: blue,
      line: { style: "solid", fill: "#D8ECFF", width: 2 },
    });
    addText(slide, item.icon, left + 44, y + 9, 22, 22, {
      fontSize: 18,
      bold: true,
      color: "white",
      alignment: "center",
    });
    addText(slide, item.text, left + 88, y, width - 120, 44, {
      fontSize: 21,
      bold: true,
      color: navy,
    });
  });
}

function addMetric(slide, label, value, suffix, left, top, width, accent = blue) {
  addText(slide, label, left, top, width, 28, {
    fontSize: 22,
    color: ink,
    alignment: "center",
  });
  addText(slide, value, left + 38, top + 28, 140, 60, {
    fontSize: 48,
    bold: true,
    color: accent,
    alignment: "right",
  });
  addText(slide, suffix, left + 184, top + 43, width - 190, 38, {
    fontSize: 25,
    bold: true,
    color: navy,
  });
}

function addSlash(slide, left) {
  slide.shapes.add({
    geometry: "line",
    position: { left: left - 70, top: 112, width: 70, height: 452 },
    fill: "none",
    line: { style: "solid", fill: navy, width: 2 },
  });
}

const slide1 = deck.slides.add();
addBackground(slide1);
addHeader(slide1, "社会价值", "国产增效  健康赋能");
addColumn(slide1, 105, 120, 480, "行业效用", "校企协同促创新\n掌握国际行业话语权", [
  { icon: "校", text: "校企协同，促创新" },
  { icon: "标", text: "标准引领，树标杆" },
  { icon: "替", text: "国产替代，破垄断" },
]);
addSlash(slide1, 620);
addColumn(slide1, 650, 120, 500, "公益价值", "开展肠道健康科普\n提升全民健康素养", [
  { icon: "13", text: "覆盖全国 13 个省份" },
  { icon: "24", text: "科普活动 24 场，线上线下同步开展" },
  { icon: "8万", text: "累计触达受众 8 万+ 人次" },
]);
slide1.speakerNotes.textFrame.setText("Content split from supplied reference image. The employment section was intentionally moved to a separate slide per user request.");

const slide2 = deck.slides.add();
addBackground(slide2);
addHeader(slide2, "社会价值", "就业增生");
addText(slide2, "带动就业", 200, 116, 880, 70, {
  fontSize: 52,
  bold: true,
  color: navy,
  alignment: "center",
});
addText(slide2, "联动上下游产业，形成“项目-产业-就业”良性格局", 210, 190, 860, 44, {
  fontSize: 29,
  bold: true,
  color: red,
  alignment: "center",
});
addMetric(slide2, "带动农户就业增收", "300", "余户", 140, 275, 270, blue);
addMetric(slide2, "户均年增收", "超万", "元", 505, 275, 270, blue);
addMetric(slide2, "直接创造稳定就业岗位", "8+", "个", 870, 275, 270, blue);
addRule(slide2, 430, 360, 420, 4, navy);
addText(slide2, "年均提供高校实训岗位", 175, 408, 320, 34, {
  fontSize: 25,
  color: ink,
  alignment: "right",
});
addText(slide2, "50+", 510, 386, 140, 64, {
  fontSize: 54,
  bold: true,
  color: blue,
  alignment: "center",
});
addText(slide2, "人次/年", 650, 410, 120, 34, {
  fontSize: 25,
  color: ink,
});
addText(slide2, "保守估计带动原料加工、包装物流、质控检测等协同岗位 20-30 个", 160, 462, 960, 42, {
  fontSize: 26,
  bold: true,
  color: navy,
  alignment: "center",
});
addText(slide2, "就业链路覆盖：海藻种植户、代工生产、检测质控、研发实训", 200, 520, 880, 42, {
  fontSize: 25,
  bold: true,
  color: navy,
  alignment: "center",
});
addText(slide2, "按启动期和试点期口径估算，优先体现稳定就业与可验证岗位，不夸大长期规模化收益。", 190, 568, 900, 42, {
  fontSize: 21,
  color: "#334155",
  alignment: "center",
});
slide2.speakerNotes.textFrame.setText("Employment section isolated into a standalone page while preserving the reference page's blue-white visual style, numeric emphasis, and social value framing.");

for (const [index, slide] of [slide1, slide2].entries()) {
  const preview = await deck.export({ slide, format: "png", scale: 2 });
  await fs.writeFile(path.join(IMAGE_DIR, `social-value-${index + 1}.png`), new Uint8Array(await preview.arrayBuffer()));
}

console.log(IMAGE_DIR);
