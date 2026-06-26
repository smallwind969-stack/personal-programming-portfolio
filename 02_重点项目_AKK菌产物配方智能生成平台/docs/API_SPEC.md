# API 规格

## 总体说明

第一版 API 使用 FastAPI + Pydantic 实现，数据来源为 `data/mock` 下的 JSON 文件。API router 只负责 HTTP 入参和出参，不直接读取 mock JSON；mock JSON 只能由 repository 层读取。

后端分层：

- `routers`: HTTP request and response handling.
- `schemas`: Pydantic request and response models.
- `services`: Business logic, formula generation, prediction assembly, risk warnings.
- `repositories`: Mock JSON data access, replaceable by database later.
- `tests`: API behavior tests.

## Base URL

本地开发：

```text
http://localhost:8000
```

Docker Compose 内部服务访问：

```text
http://api:8000
```

## GET /health

健康检查。

Response:

```json
{
  "status": "ok"
}
```

## GET /akk-products

获取 AKK 产物列表。

Response fields use `AkkProduct[]`.

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
  riskLevel: "low" | "medium" | "high";
  evidenceLevel: string;
  sourceType: "mock";
}
```

## GET /akk-products/{product_id}

获取单个 AKK 产物详情。

Path params:

```ts
interface ProductDetailParams {
  product_id: string;
}
```

Response fields use `AkkProduct`.

## POST /formula/generate

生成 mock 配方研发实验建议。

Request:

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

Response:

```ts
interface FormulaResult {
  resultId: string;
  recommendationType: "rd_experiment_suggestion";
  researchUseOnly: boolean;
  research_use_only: boolean;
  disclaimer: string;
  applicationName: string;
  createdAt: string;
  sourceType: "mock";
  candidates: FormulaCandidate[];
}
```

所有响应必须满足：

- `researchUseOnly: true`
- `research_use_only: true`
- `recommendationType: "rd_experiment_suggestion"`
- `disclaimer` 明确说明仅用于研发实验建议

## GET /formula-results

获取 mock 配方结果列表，供 Dashboard 展示最近结果。

Response fields use `FormulaResult[]`.

## GET /formula-results/{result_id}

查询配方结果详情。

Path params:

```ts
interface FormulaResultParams {
  result_id: string;
}
```

Response fields use `FormulaResult`.

## Shared Field Types

```ts
interface ProductProperty {
  propertyId: string;
  propertyName: string;
  propertyValue: string;
  unit?: string;
  description?: string;
}

interface FormulaCandidate {
  candidateId: string;
  candidateName: string;
  composition: FormulaIngredient[];
  predictions: PredictionResult[];
  confidenceScore: number;
  confidenceLevel: "low" | "medium" | "high";
  riskItems: RiskItem[];
  validationMetrics: ValidationMetric[];
  experimentSuggestions: string[];
}

interface FormulaIngredient {
  productId: string;
  productName: string;
  ratioPercent: number;
  role: string;
}

interface PredictionResult {
  predictionId: string;
  targetName: string;
  predictedValue: string;
  unit?: string;
  confidenceScore: number;
  explanation: string;
}

interface RiskItem {
  riskId: string;
  riskName: string;
  riskLevel: "low" | "medium" | "high";
  description: string;
  mitigationSuggestion: string;
}

interface ValidationMetric {
  metricId: string;
  metricName: string;
  methodSuggestion: string;
  expectedRange?: string;
  priority: "required" | "recommended" | "optional";
}
```
