const applicationLabels: Record<string, string> = {
  yogurt: "功能酸奶",
  nutrition_powder: "营养粉",
  functional_beverage: "即饮功能饮品",
  meal_replacement: "代餐奶昔",
  jelly: "功能果冻",
  culture_substrate: "培养底物",
  mechanism_validation: "机制验证",
  beverage: "饮品体系",
  encapsulation: "包埋体系",
  texture_system: "质构体系",
  functional_jelly: "功能果冻",
  functional_powder: "功能粉剂",
  prototype_bead: "爆爆珠原型",
  seaweed_food: "海藻食品",
  fish_ball_matrix: "鱼丸基质",
  fermentation_screening: "发酵筛选",
  control_substrate: "对照底物",
  custom: "自定义产品",
};

const riskLabels: Record<string, string> = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

const confidenceLabels: Record<string, string> = {
  low: "低置信度",
  medium: "中等置信度",
  high: "高置信度",
};

const priorityLabels: Record<string, string> = {
  required: "必须验证",
  recommended: "建议验证",
  optional: "可选验证",
};

const categoryLabels: Record<string, string> = {
  postbiotic: "后生元原料",
  metabolite_blend: "代谢物组合",
  fiber_complex: "纤维复配物",
  algae_polysaccharide: "海藻多糖底物",
  modified_algae_polysaccharide: "改性海藻多糖",
  carrageenan_substrate: "卡拉胶底物",
  algae_glycoprotein: "海藻糖蛋白",
  fermented_fiber: "发酵膳食纤维",
  encapsulation: "包埋颗粒",
  food_matrix: "食品基质",
  prototype_product: "产品原型",
  polysaccharide_control: "对照多糖",
};

export function formatApplication(value: string) {
  return applicationLabels[value] ?? value;
}

export function formatRisk(value: string) {
  return riskLabels[value] ?? value;
}

export function formatConfidence(value: string) {
  return confidenceLabels[value] ?? value;
}

export function formatPriority(value: string) {
  return priorityLabels[value] ?? value;
}

export function formatCategory(value: string) {
  return categoryLabels[value] ?? value;
}

export function getProductRole(productCategory: string) {
  if (["postbiotic", "metabolite_blend", "fiber_complex"].includes(productCategory)) {
    return "AKK 功能产物";
  }
  if (["algae_polysaccharide", "modified_algae_polysaccharide", "carrageenan_substrate", "algae_glycoprotein", "polysaccharide_control"].includes(productCategory)) {
    return "论文底物与对照组";
  }
  if (["fermented_fiber", "food_matrix"].includes(productCategory)) {
    return "食品基质与加工场景";
  }
  if (["encapsulation", "prototype_product"].includes(productCategory)) {
    return "包埋与样品原型";
  }
  return "其他研发对象";
}

export function getApplicationProfile(value: string) {
  const profiles: Record<
    string,
    {
      title: string;
      description: string;
      format: string;
      audience: string;
      claimTags: string[];
      checks: string[];
    }
  > = {
    yogurt: {
      title: "功能酸奶",
      description: "适合做低糖、轻负担、肠道健康概念酸奶，重点关注酸性体系稳定性、口感遮蔽和加工保留。",
      format: "杯装酸奶、饮用型酸奶、低糖发酵乳",
      audience: "关注体重管理、肠道状态和早餐轻食的人群",
      claimTags: ["肠道健康", "低糖", "后生元", "轻负担"],
      checks: ["酸性稳定性", "风味遮蔽", "关键标志物保留率"],
    },
    nutrition_powder: {
      title: "营养粉",
      description: "适合做冲调粉、成人营养粉和膳食补充方向，重点关注复水速度、粉体流动性和配料表表达。",
      format: "成人营养粉、冲调粉包、早餐营养粉",
      audience: "白领、银发、轻养生和家庭营养补充人群",
      claimTags: ["益生元", "膳食纤维", "冲调便捷", "清洁标签"],
      checks: ["复水时间", "粉体流动性", "均匀性"],
    },
    functional_beverage: {
      title: "即饮功能饮品",
      description: "适合做水相轻功能饮品，重点关注浊度、沉淀、酸甜体系风味和低负担功能表达。",
      format: "轻功能饮料、餐前饮品、肠道健康饮品",
      audience: "年轻办公、运动轻补给和便利店即饮消费人群",
      claimTags: ["即饮", "低负担", "肠道舒适", "清爽口感"],
      checks: ["浊度变化", "沉淀风险", "酸性体系稳定性"],
    },
    meal_replacement: {
      title: "代餐奶昔",
      description: "适合评估饱腹感、纤维支撑、口感厚度和复配营养结构，可延展为体重管理产品线。",
      format: "代餐粉、营养棒、即饮代餐",
      audience: "体重管理、轻断食和运动营养人群",
      claimTags: ["饱腹感", "体重管理", "高纤维", "营养均衡"],
      checks: ["黏度", "复水性", "感官接受度"],
    },
  };

  return (
    profiles[value] ?? {
      title: formatApplication(value),
      description: "可作为内部研发样品方向进行小试验证，输出仅作为研发实验建议。",
      format: "待定义产品形态",
      audience: "待定义目标人群",
      claimTags: ["肠道健康", "功能食品"],
      checks: ["稳定性", "感官", "目标性质"],
    }
  );
}

export function getIngredientProfile(productCategory: string) {
  const profiles: Record<
    string,
    {
      component: string;
      activity: string;
      supplyForm: string;
      usageRange: string;
      costIndex: number;
      stabilityIndex: number;
    }
  > = {
    postbiotic: {
      component: "灭活 AKK 菌体、外膜蛋白和细胞结构片段",
      activity: "适合肠道屏障、代谢健康和热稳定概念表达",
      supplyForm: "浅米色细粉，适合粉体和乳基体系",
      usageRange: "建议 0.2%-1.5%",
      costIndex: 68,
      stabilityIndex: 74,
    },
    metabolite_blend: {
      component: "AKK 相关代谢物、胞外分泌蛋白和短链脂肪酸相关信号组分",
      activity: "适合水相功能表达、轻负担饮品和风味型概念",
      supplyForm: "液体或浓缩粉，适合饮品和低温后添加",
      usageRange: "建议 0.05%-0.8%",
      costIndex: 82,
      stabilityIndex: 61,
    },
    fiber_complex: {
      component: "膳食纤维复配基质、益生元支持组分和粉体结构支撑组分",
      activity: "适合粉体结构、复水口感和饱腹感方向",
      supplyForm: "白色至浅黄色粉末，适合冲调和烘焙体系",
      usageRange: "建议 1%-8%",
      costIndex: 55,
      stabilityIndex: 79,
    },
  };

  return (
    profiles[productCategory] ?? {
      component: `${formatCategory(productCategory)}相关功能组分`,
      activity: "适合内部研发验证，不作为最终生产结论",
      supplyForm: "待定义供应形态",
      usageRange: "建议按样品规格确认",
      costIndex: 65,
      stabilityIndex: 65,
    }
  );
}
