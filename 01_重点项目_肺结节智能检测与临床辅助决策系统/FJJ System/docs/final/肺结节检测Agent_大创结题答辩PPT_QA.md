# 肺结节检测 Agent 大创结题答辩 PPT QA

- PPTX：docs/final/肺结节检测Agent_大创结题答辩PPT.pptx
- slide count：15
- preview dir：docs/final/ppt_scratch_lung_agent/tmp/preview
- montage：docs/final/ppt_scratch_lung_agent/tmp/preview/deck-montage.webp
- contact sheet：docs/final/ppt_scratch_lung_agent/tmp/preview/contact_sheet.png
- source notes：docs/final/ppt_scratch_lung_agent/tmp/source-notes.txt

## 自检结论

- 已使用可编辑文本框、形状、指标卡与嵌入式图表图片；未使用整页截图作为幻灯片。
- 已为每页写入 speaker notes。
- 关键科研数字均来自工作区现有报告/JSON；未知团队与导师信息保留为待补充。
- 已渲染每页 PNG 与整套 montage，用于后续视觉复核。
- 已用系统 Python 3.9 环境运行 `python -m unittest discover -s tests`，结果为 55 tests OK。

## 已知边界

- deck 未套用学校官方模板；后续拿到模板后可做 template-following 版本。
- Codex bundled Python 缺少 `torch` / `matplotlib`，完整项目测试需使用系统 Python 3.9 环境。
- 当前公共验证限定为 LUNA16 subset0 / subset0 evaluation split，不能表述为完整 LUNA16 官方成绩。
