# UI 规格

## 设计目标

平台面向内部食品研发人员，第一版界面以清晰、克制、可扫描为主。用户应能完成从 Dashboard 查看概览，到浏览 AKK 产物、进入产物详情、生成配方、查看结果的完整闭环。

第一版必须持续展示研发边界：所有配方结果均为 `Research use only`，仅代表“研发实验建议”，不代表最终上市配方。

## 技术约定

- Framework: `Next.js App Router`
- Language: `TypeScript`
- Styling: `Tailwind CSS`
- UI structure: shadcn/ui 风格的基础组件结构
- API client: `apps/web/lib/api.ts`
- Frontend schemas: `apps/web/lib/schemas.ts`

前端页面不得硬编码 AKK 产物和配方结果，业务数据必须通过 API 获取。

## 页面路由

第一版包含：

- `/`: Dashboard
- `/products`: AKK 产物库
- `/products/[id]`: 产物详情
- `/formula/new`: 配方生成
- `/formula/results/[id]`: 配方结果

## 导航

使用左侧导航，移动端使用顶部导航。

Navigation labels:

- `Dashboard`
- `Products`
- `Generate Formula`

## Dashboard

页面目标：展示平台 mock 数据概览和研发边界。

模块：

- Key metric cards
- Recent formula result
- R&D boundary notice
- `Research use only` badge

Dashboard metric fields:

- `productCount`
- `applicationTargetCount`
- `recentFormulaCount`
- `highRiskCount`

## AKK 产物库

页面目标：展示 AKK 产物列表，支持用户进入详情。

展示字段：

- `productName`
- `productCategory`
- `description`
- `recommendedApplications`
- `riskLevel`
- `sourceType`

## 产物详情

页面目标：展示单个产物的性质、应用适配性、风险等级和证据等级，并允许用户进入配方生成页面。

展示模块：

- Product identity
- Key properties
- Recommended applications
- Functional assumptions
- Risk warnings
- Validation metrics
- Evidence level

用户从详情页点击 `Use in formula` 后进入 `/formula/new?productId={productId}`。

## 配方生成

页面目标：收集目标食品应用、目标性质和限制条件。

表单字段：

- `applicationTargetId`
- `targetProperties`
- `constraints`
- `preferredProductIds`
- `excludedProductIds`
- `maxIngredientCount`
- `notes`

提交后调用：

```text
POST /formula/generate
```

成功后跳转：

```text
/formula/results/{resultId}
```

## 配方结果

页面目标：展示候选配方和实验验证建议。

必须展示：

- 推荐份额配比: `composition`
- 预测结果: `predictions`
- 置信度: `confidenceScore`, `confidenceLevel`
- 风险提示: `riskItems`
- 实验建议: `experimentSuggestions`
- Research use only 标识: `researchUseOnly`, `research_use_only`

## UI 状态

第一版基础状态：

- Mock data badge
- Research use only badge
- Empty list fallback
- API error fallback by framework error boundary later

## 后续增强

后续阶段再增加：

- 数据筛选和排序
- 结果对比
- 文献证据展示
- 实验结果回填
- 登录和权限
