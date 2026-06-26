# 数据契约

## 契约原则

业务说明使用中文，接口字段、数据字段和代码命名使用英文。第一版数据全部来自 mock 数据和规则模板，接口形态先保持稳定，方便后续替换真实数据库、知识库、配方引擎和预测模型。

## Shared Types

```ts
type RiskLevel = "low" | "medium" | "high";

type ConfidenceLevel = "low" | "medium" | "high";

type RecommendationType = "rd_experiment_suggestion";
```

## AkkProduct

```ts
interface AkkProduct {
  productId: string;
  productName: string;
  productCategory: string;
  description: string;
  keyProperties: ProductProperty[];
  functionalAssumptions: string[];
  recommendedApplications: string[];
  constraints: string[];
  riskItems: RiskItem[];
  validationMetrics: ValidationMetric[];
  sourceType: "mock";
}
```

## ProductProperty

```ts
interface ProductProperty {
  propertyId: string;
  propertyName: string;
  propertyValue: string;
  unit?: string;
  description?: string;
}
```

## ApplicationTarget

```ts
interface ApplicationTarget {
  applicationTargetId: string;
  applicationName: string;
  applicationCategory: string;
  targetPropertyOptions: string[];
  defaultConstraints: string[];
  sourceType: "mock";
}
```

## FormulaGenerationRequest

```ts
interface FormulaGenerationRequest {
  applicationTargetId: string;
  targetProperties: string[];
  constraints: string[];
  preferredProductIds: string[];
  excludedProductIds: string[];
  maxIngredientCount: number;
  notes?: string;
}
```

## FormulaGenerationResponse

```ts
interface FormulaGenerationResponse {
  resultId: string;
  recommendationType: RecommendationType;
  disclaimer: string;
  candidates: FormulaCandidate[];
  createdAt: string;
  sourceType: "mock";
}
```

## FormulaCandidate

```ts
interface FormulaCandidate {
  candidateId: string;
  candidateName: string;
  composition: FormulaIngredient[];
  predictions: PredictionResult[];
  confidenceScore: number;
  confidenceLevel: ConfidenceLevel;
  riskItems: RiskItem[];
  validationMetrics: ValidationMetric[];
  experimentSuggestions: string[];
}
```

## FormulaIngredient

```ts
interface FormulaIngredient {
  productId: string;
  productName: string;
  ratioPercent: number;
  role: string;
}
```

## PredictionResult

```ts
interface PredictionResult {
  predictionId: string;
  targetName: string;
  predictedValue: string;
  unit?: string;
  confidenceScore: number;
  explanation: string;
}
```

## RiskItem

```ts
interface RiskItem {
  riskId: string;
  riskName: string;
  riskLevel: RiskLevel;
  description: string;
  mitigationSuggestion: string;
}
```

## ValidationMetric

```ts
interface ValidationMetric {
  metricId: string;
  metricName: string;
  methodSuggestion: string;
  expectedRange?: string;
  priority: "required" | "recommended" | "optional";
}
```

## API Endpoints

第一版可以用本地 mock API 或前端 mock service 实现。接口路径先定义如下：

```http
GET /api/dashboard
GET /api/products
GET /api/products/:productId
GET /api/application-targets
POST /api/formula-generations
GET /api/formula-results/:resultId
```

## GET /api/dashboard

```ts
interface DashboardResponse {
  productCount: number;
  applicationTargetCount: number;
  recentFormulaCount: number;
  highRiskCount: number;
  recentResults: FormulaResultSummary[];
  riskSummary: RiskSummaryItem[];
  sourceType: "mock";
}
```

## FormulaResultSummary

```ts
interface FormulaResultSummary {
  resultId: string;
  applicationName: string;
  candidateCount: number;
  createdAt: string;
  highestRiskLevel: RiskLevel;
}
```

## RiskSummaryItem

```ts
interface RiskSummaryItem {
  riskName: string;
  riskLevel: RiskLevel;
  count: number;
}
```

## Mock Data Requirement

所有 mock 数据必须能支持完整页面闭环：

- Dashboard overview
- Product list
- Product detail
- Application target options
- Formula generation request
- Formula result detail

所有结果中的 `recommendationType` 必须为 `rd_experiment_suggestion`。

