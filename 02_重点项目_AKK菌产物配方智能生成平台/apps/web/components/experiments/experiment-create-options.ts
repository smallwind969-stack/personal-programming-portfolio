export type ExperimentCreateOption = {
  id: "enterprise" | "sample" | "blank";
  title: string;
  description: string;
  actionLabel: string;
  emphasis: "primary" | "secondary";
};

export const experimentCreateOptions: readonly ExperimentCreateOption[] = [
  {
    id: "enterprise",
    title: "上传企业实验数据",
    description: "建立正式实验档案，随后上传 CSV、TXT、Excel 或解密后的设备数据。",
    actionLabel: "填写实验信息",
    emphasis: "primary",
  },
  {
    id: "sample",
    title: "使用行业示例数据",
    description: "创建隔离的菌藻培养示例，完整体验数据分析、仿真模拟和工艺优化。",
    actionLabel: "创建示例实验",
    emphasis: "secondary",
  },
  {
    id: "blank",
    title: "建立空白实验档案",
    description: "先记录实验目标、对象、指标和批次，后续再补充真实数据。",
    actionLabel: "填写档案信息",
    emphasis: "secondary",
  },
] as const;
