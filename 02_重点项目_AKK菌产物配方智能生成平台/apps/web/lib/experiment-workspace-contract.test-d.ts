import {
  experimentArchiveResponseSchema,
  experimentWorkspaceOverviewSchema,
  sampleExperimentCreateSchema,
  sampleExperimentResultSchema,
  type ExperimentArchiveResponse,
  type ExperimentWorkspaceOverview,
  type SampleExperimentCreate,
  type SampleExperimentResult,
} from "@/lib/schemas";
import {
  getExperimentArchive,
  getExperimentWorkspaceOverview,
  createSampleExperimentWorkspace,
} from "@/lib/api";

const archive = experimentArchiveResponseSchema.parse({
  totalCount: 0,
  runningCount: 0,
  completedCount: 0,
  averageConfidenceScore: 0,
  experiments: [],
}) satisfies ExperimentArchiveResponse;

const overview = experimentWorkspaceOverviewSchema.parse({
  experimentId: "exp-contract",
  name: "契约测试实验",
  objective: "验证前后端类型契约",
  batchCode: null,
  statusLabel: "待补充数据",
  updatedAt: "2026-07-19T00:00:00+08:00",
  confidenceScore: null,
  modelVersion: "untrained",
  modelType: "待选择",
  reliabilityMetrics: [],
  stages: [
    { stage: "dataAnalysis", label: "数据分析", status: "waiting", canEnter: true, detail: "待运行" },
    { stage: "simulation", label: "仿真模拟", status: "waiting", canEnter: true, detail: "仅可查看" },
    { stage: "optimization", label: "工艺优化", status: "waiting", canEnter: false, detail: "已锁定" },
  ],
  resultMetrics: [],
  riskItems: [],
  validationItems: [],
  sourceType: "blank",
  sampleTemplateVersion: null,
}) satisfies ExperimentWorkspaceOverview;

const sourceType: "enterprise" | "sample" | "blank" = overview.sourceType;
const sampleRequest = sampleExperimentCreateSchema.parse({ templateKey: "algae-culture" }) satisfies SampleExperimentCreate;
declare const sampleResult: SampleExperimentResult;
sampleExperimentResultSchema.parse(sampleResult);

void archive;
void overview;
void sourceType;
void sampleRequest;
void createSampleExperimentWorkspace;
void getExperimentArchive;
void getExperimentWorkspaceOverview;
