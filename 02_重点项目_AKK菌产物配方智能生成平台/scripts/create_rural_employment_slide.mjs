import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.cwd();
const skillDir = "C:/Users/LSY/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const pythonExe = "C:/Users/LSY/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const buildDir = path.join(workspaceDir, "outputs", "ppt_build_rural_employment");
const outputDir = path.join(workspaceDir, "outputs", "ppt", "rural_employment");
const imageDir = path.join(workspaceDir, "outputs", "ppt_images", "rural_employment");
const backgroundPath = path.join(workspaceDir, "outputs", "ppt_assets", "rural_employment", "rural-employment-panorama.png");
const candidatePath = path.join(buildDir, "candidate-rural-employment.pptx");
const finalPath = path.join(outputDir, "菌藻启元-就业与乡村经济-v2.pptx");
const previewPath = path.join(imageDir, "菌藻启元-就业与乡村经济-v2.png");

const { resolvePresentationFont, finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, "container_tools", "artifact_tool_utils.mjs")).href,
);

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(imageDir, { recursive: true });

const font = resolvePresentationFont({ fontFamily: "Microsoft YaHei" });
const bgBytes = new Uint8Array(await fs.readFile(backgroundPath));
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const slide = deck.slides.add();

function shape(slideRef, geometry, left, top, width, height, fill, lineFill = "none", lineWidth = 0) {
  return slideRef.shapes.add({
    geometry,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  });
}

function textBox(text, left, top, width, height, style = {}) {
  const box = shape(slide, "textbox", left, top, width, height, "none");
  box.text = text;
  box.text.style = {
    typeface: font,
    fontSize: 24,
    color: "#FFFFFF",
    autoFit: "shrinkText",
    ...style,
  };
  return box;
}

slide.images.add({
  blob: bgBytes,
  contentType: "image/png",
  alt: "海藻种植户、食品生产线与青年研发人员组成的乡村产业链场景",
  fit: "cover",
  position: { left: 0, top: 0, width: 1280, height: 720 },
});

shape(slide, "rect", 0, 0, 1280, 720, "#021B3C/24");
shape(slide, "rect", 0, 0, 760, 525, "#031D42/42");
shape(slide, "rect", 0, 0, 1280, 10, "#19A9EE");
shape(slide, "rect", 0, 523, 1280, 197, "#031A38/80");
shape(slide, "rect", 0, 523, 1280, 4, "#24C4F4");

textBox("社会价值", 68, 36, 150, 34, {
  fontSize: 25,
  bold: true,
  color: "#37C7F4",
});
textBox("乡村振兴  就业增生", 224, 38, 290, 31, {
  fontSize: 19,
  bold: true,
  color: "#FFFFFF",
});
shape(slide, "rect", 68, 78, 54, 3, "#37C7F4");

textBox("一片海藻，带动一条乡村产业链", 66, 103, 880, 75, {
  fontSize: 50,
  bold: true,
  color: "#FFFFFF",
});
textBox("把原料订单留在沿海乡村，让种植、加工与青年就业共享产业增量", 69, 181, 850, 39, {
  fontSize: 23,
  bold: true,
  color: "#DDF7FF",
});

textBox("120", 65, 231, 286, 119, {
  fontSize: 91,
  bold: true,
  color: "#38C9F5",
  alignment: "left",
});
textBox("万元", 320, 289, 100, 51, {
  fontSize: 36,
  bold: true,
  color: "#FFFFFF",
});
textBox("首年原料采购预算", 70, 349, 320, 45, {
  fontSize: 28,
  bold: true,
  color: "#FFFFFF",
});
textBox("占项目资金计划的 40%", 72, 398, 320, 34, {
  fontSize: 20,
  color: "#CDECF7",
});

shape(slide, "rect", 430, 250, 4, 178, "#36C8F4");
textBox("“龙头企业＋合作社＋农户”", 458, 255, 420, 43, {
  fontSize: 27,
  bold: true,
  color: "#FFFFFF",
});
textBox("与沿海藻类企业建立稳定供应，\n通过保底价收购和质量标准把订单传导至种植端", 458, 309, 470, 82, {
  fontSize: 20,
  bold: true,
  color: "#E7F8FD",
  lineSpacing: 1.2,
});
textBox("农户获得稳定销路，企业获得可追溯原料", 458, 404, 410, 34, {
  fontSize: 18,
  color: "#8FE4FA",
});

const metricXs = [66, 362, 658, 954];
const metricValues = ["1–2 家", "15%–20%", "2–3 个", "四类环节"];
const metricLabels = [
  "启动期藻类合作企业",
  "本地化原料成本优势",
  "首期核心岗位｜保守测算",
  "种植·加工·质控·物流",
];
for (let i = 0; i < metricXs.length; i += 1) {
  if (i > 0) shape(slide, "rect", metricXs[i] - 25, 567, 1, 92, "#5B84A5/70");
  textBox(metricValues[i], metricXs[i], 554, 245, 57, {
    fontSize: i === 3 ? 34 : 42,
    bold: true,
    color: i === 0 ? "#37C7F4" : "#FFFFFF",
    alignment: "left",
  });
  textBox(metricLabels[i], metricXs[i], 616, 260, 34, {
    fontSize: 18,
    bold: true,
    color: "#CDECF7",
  });
}

textBox("测算口径：依据项目300万元资金计划，原料采购占40%；岗位数量为启动期规划，农户增收以实际采购合同与结算为准。", 68, 679, 1120, 24, {
  fontSize: 13,
  color: "#AFC9D8",
});
textBox("QIRA", 1168, 39, 82, 28, {
  fontSize: 16,
  bold: true,
  italic: true,
  color: "#7DE5FF",
  alignment: "center",
});

slide.speakerNotes.textFrame.setText(
  "数据来源：用户提供《菌藻启元（无脚本版本）》中的资金用途、商业模式、战略规划与社会效益章节。120万元=300万元资金计划×原料采购40%；启动期计划与1-2家藻类龙头企业合作；材料预计本地化采购可使综合原料成本较进口同类产品降低15%-20%。2-3个首期核心岗位为保守规划口径，不代表已实现就业。背景图由OpenAI图像工具生成；画面真实性参考了福建霞浦海藻养殖公开报道：中国网 https://www.china.org.cn/photos/2022-10/26/content_78486248_6.htm ，新华社 https://english.news.cn/africa/20221022/cbd367c3b970456d818c0cb93b417560/c.html 。",
);

await (await PresentationFile.exportPptx(deck)).save(candidatePath);
const preview = await deck.export({ slide, format: "png", scale: 2 });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const result = await finalizePresentation({
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: pythonExe,
  integrityValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-heading-fit",
  ],
  explicitTotalSlideCount: 1,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, "rural-employment-v2.validation.json"),
});

console.log(JSON.stringify({ finalPath, previewPath, result }, null, 2));
