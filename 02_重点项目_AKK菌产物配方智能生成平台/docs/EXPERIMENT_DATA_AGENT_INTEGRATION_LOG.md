# 实验数据智能化多核 Agent 融合记录

## Step 001：实验文本文件上传入口

- 日期：2026-07-17
- 当前主项目路径：`D:\林世宇职业规划+AI工程经验+项目成果\个人项目经历\创赛（Akk菌产物配方平台）`
- 目标：把“实验数据智能化平台”的第一阶段能力融合进当前 AKK 配方/工艺/仿真主项目
- 本步范围：实验设备文本文件上传 → 生成 FileAsset 响应 → 同实验内重复内容复用

## 已实现能力

新增 API：

`POST /experiments/{experiment_id}/files`

请求：

```json
{
  "fileName": "bioreactor_temperature.csv",
  "content": "time,Temp,rpm\n2026-01-01 00:00:00,36.5,120\n"
}
```

响应：

```json
{
  "assetId": "file-...",
  "experimentId": "exp-akk-001",
  "originalName": "bioreactor_temperature.csv",
  "detectedFormat": "csv",
  "parseStatus": "parsed",
  "rowCount": 1,
  "columnNames": ["time", "Temp", "rpm"],
  "contentHash": "...",
  "duplicate": false,
  "duplicateOfAssetId": null
}
```

## 设计说明

当前主项目尚未引入真实实验数据库和 Agent 编排层，因此本步采用内存型 `ExperimentFileService` 作为最小落点。

该实现先稳定 API 契约和数据资产入口，后续可以逐步替换为：

- SQLite/PostgreSQL 持久化 FileAsset
- 多文件批量上传
- DataCollectionLocalizationAgent
- 审计日志
- 多 Agent 编排
- Dashboard 时间线

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`

## 验证

专项测试：

```text
2 passed
```

全量测试：

```text
26 passed
```

## 下一步

Step 002 建议实现：批量上传多个实验设备文件，并在同一实验批次下返回多个 FileAsset。

## Step 002：多设备文本文件批量上传入口

- 日期：2026-07-17
- 目标：让一次实验中的多个设备导出文件作为同一批次进入系统
- 本步范围：批量上传多个 CSV/TXT 文本文件 → 逐个解析 → 返回多个 FileAsset → 同实验内重复内容复用

## 已实现能力

新增 API：

`POST /experiments/{experiment_id}/files/batch`

请求：

```json
{
  "files": [
    {
      "fileName": "bioreactor_temperature.csv",
      "content": "time,Temp\n2026-01-01 00:00:00,36.5\n"
    },
    {
      "fileName": "ph_meter_log.csv",
      "content": "time,pH\n2026-01-01 00:00:00,6.8\n"
    }
  ]
}
```

响应：

```json
{
  "experimentId": "exp-akk-batch",
  "assetCount": 2,
  "assets": [
    {
      "assetId": "file-...",
      "originalName": "bioreactor_temperature.csv",
      "detectedFormat": "csv",
      "parseStatus": "parsed",
      "rowCount": 1,
      "columnNames": ["time", "Temp"],
      "duplicate": false
    }
  ]
}
```

## 设计说明

批量上传复用 Step 001 的 `save_text_file` 能力，因此同一实验内重复内容会自动返回已有 FileAsset：

- 第一次出现：`duplicate=false`
- 重复内容：`duplicate=true`
- 重复内容返回同一个 `assetId`
- `duplicateOfAssetId` 指向已有资产

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`

## 验证

专项测试：

```text
4 passed
```

全量测试：

```text
28 passed
```

## 下一步

Step 003 建议实现：为单文件/批量上传增加上传审计记录，为后续 dashboard 时间线和多 Agent 编排提供可追溯证据。

## Step 003：实验文件上传审计记录

- 日期：2026-07-17
- 目标：为实验文件入口增加可追溯证据链
- 本步范围：单文件/批量上传后写入内存审计事件，并提供查询 API

## 已实现能力

新增 API：

`GET /experiments/{experiment_id}/file-audits`

审计事件包含：

- `auditId`
- `experimentId`
- `action`
  - `upload_file`
  - `upload_files_batch`
- `fileNames`
- `assetIds`
- `contentHashes`
- `duplicates`
- `createdAt`

## 示例响应

```json
{
  "experimentId": "exp-akk-audit",
  "eventCount": 1,
  "events": [
    {
      "auditId": "audit-...",
      "experimentId": "exp-akk-audit",
      "action": "upload_file",
      "fileNames": ["bioreactor_temperature.csv"],
      "assetIds": ["file-..."],
      "contentHashes": ["..."],
      "duplicates": [false],
      "createdAt": "2026-07-17T..."
    }
  ]
}
```

## 设计说明

当前仍采用内存型审计记录，目的是先把审计 API 契约接入当前主项目。

批量上传只写一条 `upload_files_batch` 审计事件，避免把一次批量上传拆成多条单文件审计，便于后续 dashboard 按批次展示。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`

## 验证

专项测试：

```text
6 passed
```

全量测试：

```text
30 passed
```

## 下一步

Step 004 建议实现：实验文件审计时间线阶段标签，把上传事件映射为“文件上传”阶段，为后续 dashboard 时间线做准备。

## Step 004：实验文件审计阶段标签

- 日期：2026-07-17
- 目标：把技术审计事件翻译成 dashboard 可展示的研发流程阶段
- 本步范围：为文件上传审计事件增加 `stage` 和 `stageLabel`

## 已实现能力

`GET /experiments/{experiment_id}/file-audits` 返回的每个事件新增：

- `stage`
- `stageLabel`

当前规则：

```json
{
  "action": "upload_file",
  "stage": "file_upload",
  "stageLabel": "文件上传"
}
```

批量上传同样归类为：

```json
{
  "action": "upload_files_batch",
  "stage": "file_upload",
  "stageLabel": "文件上传"
}
```

## 设计说明

当前只接入了实验文件入口，因此阶段映射先覆盖“文件上传”阶段。

后续多 Agent 链路接入后，会继续扩展：

- `data_collection_localization` → 数据收集定位
- `schema_mapping` → 字段识别映射
- `data_cleaning` → 数据清洗
- `unit_conversion` → 单位转换
- `time_alignment` → 时间轴对齐
- `feature_engineering` → 特征工程
- `visualization` → 可视化
- `explanation` → 结果解释
- `report` → 报告生成
- `repository` → 入库沉淀

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/tests/test_experiment_file_upload.py`

## 验证

专项测试：

```text
6 passed
```

全量测试：

```text
30 passed
```

## 下一步

Step 005 建议实现：文件审计时间线汇总接口，返回阶段汇总、事件数量和最近上传状态，为 dashboard 卡片和时间线组件提供数据。

## Step 005：实验文件审计时间线汇总接口

- 日期：2026-07-17
- 目标：为 dashboard 提供文件上传入口的聚合视图
- 本步范围：基于已有文件上传审计事件，返回事件数、资产数、阶段汇总和最近一次上传事件

## 已实现能力

新增 API：

`GET /experiments/{experiment_id}/file-audit-summary`

响应包含：

- `experimentId`
- `eventCount`
- `assetCount`
- `stageSummary`
- `lastEvent`

## 示例响应

```json
{
  "experimentId": "exp-akk-summary",
  "eventCount": 2,
  "assetCount": 3,
  "stageSummary": [
    {
      "stage": "file_upload",
      "stageLabel": "文件上传",
      "eventCount": 2,
      "assetCount": 3
    }
  ],
  "lastEvent": {
    "action": "upload_files_batch",
    "fileNames": ["ph_meter_log.csv", "od600_reader.csv"]
  }
}
```

## 设计说明

当前 summary 只覆盖文件上传阶段。

这是 dashboard 时间线的最小可用聚合接口。后续接入多 Agent 后，可以扩展更多阶段：

- 数据收集定位
- 字段识别映射
- 数据清洗
- 单位转换
- 时间轴对齐
- 特征工程
- 可视化
- 解释
- 报告
- 入库沉淀

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`

## 验证

专项测试：

```text
7 passed
```

全量测试：

```text
31 passed
```

## 下一步

Step 006 建议实现：把文件审计 summary 接入前端实验页面或 dashboard 卡片，让用户能看到“已上传文件数、最近上传、阶段状态”。
## Step 006：文件审计 summary 接入前端实验页

- 日期：2026-07-17
- 目标：把后端实验文件审计汇总接口接入前端实验页，让用户在实验平台页面直接看到“上传审计事件、文件资产数量、阶段数量、最近上传文件”。
- 本步范围：只接入已有 `file-audit-summary` 聚合结果，不新增真实持久化、不新增实时设备流、不做清洗/对齐/建模逻辑。

## 已实现能力

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增文件审计事件、阶段汇总、审计 summary 的 zod schema。
- `apps/web/lib/api.ts`：新增 `getExperimentFileAuditSummary(experimentId)` API 客户端方法。
- `apps/web/lib/types.ts`：导出 `ExperimentFileAuditSummary` 类型。
- `apps/web/app/experiments/page.tsx`：重写实验页中文文案，并新增“实验数据入口审计”卡片。

页面现在展示：
- 上传审计事件数
- 文件资产数量
- 审计阶段数量
- 最近上传文件名
- 当前阶段标签

## 设计说明

当前前端使用固定实验 ID `exp-akk-summary` 调用：

```text
GET /experiments/exp-akk-summary/file-audit-summary
```

由于后端目前仍是内存态服务，若当前后端进程没有发生过文件上传，页面会显示 0 和“暂无上传文件”。这是符合当前阶段预期的：本步先打通“后端 summary → 前端看板”的闭环，后续再接入真实实验选择、数据库持久化和多阶段 agent 事件流。

## 修改文件

- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/lib/types.ts`
- `apps/web/app/experiments/page.tsx`

## 验证

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

后端测试：

```text
py -m pytest apps/api/tests -q
```

结果：31 passed。

## 下一步

Step 007 建议实现：为前端增加一个最小文件上传入口，允许用户在实验页提交 CSV/TXT 文本文件，并在上传成功后刷新审计 summary，使“上传 → 审计记录 → 页面可见”形成端到端闭环。

## Step 007：前端最小文件上传闭环

- 日期：2026-07-17
- 目标：让实验页具备最小可用的 CSV/TXT 上传入口，形成“前端选择文件 → 后端保存文件资产 → 写入审计记录 → 前端刷新 summary”的闭环。
- 本步范围：只支持浏览器读取文本文件并调用已有单文件上传 API；暂不做多文件拖拽、数据库持久化、实时设备采集、清洗预览和字段映射 UI。

## 已实现能力

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增 `experimentTextFileUploadRequestSchema` 和 `experimentFileAssetSchema`。
- `apps/web/lib/api.ts`：新增 `uploadExperimentTextFile(experimentId, payload)`。
- `apps/web/lib/types.ts`：导出上传请求和文件资产类型。
- `apps/web/components/experiments/experiment-file-upload-card.tsx`：新增客户端上传卡片。
- `apps/web/app/experiments/page.tsx`：把上传卡片接入实验页，并统一使用 `SUMMARY_EXPERIMENT_ID`，确保上传和审计 summary 读取同一个实验上下文。

上传卡片当前行为：
- 选择 `.csv` / `.txt` 文件。
- 使用浏览器 `File.text()` 读取文本内容。
- POST 到 `/experiments/{experimentId}/files`。
- 成功后显示资产 ID、解析行数或重复文件复用提示。
- 调用 `router.refresh()` 刷新实验页服务端数据，使审计 summary 重新读取。

## 设计说明

本步严格对应平台第一阶段最痛点之一：把设备导出的原始文本数据先收进系统，并生成可追溯记录。当前上传入口不是最终形态，而是 DataCollectionLocalizationAgent 的前端触发入口：先能接收真实文件，再逐步扩展字段识别、单位转换、时间轴对齐、清洗日志和人工确认。

## 修改文件

- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/lib/types.ts`
- `apps/web/components/experiments/experiment-file-upload-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

后端测试：

```text
py -m pytest apps/api/tests -q
31 passed
```

## 下一步

Step 008 建议实现：新增“上传后的文件资产列表/最近上传明细”接口或前端展示区，让用户不仅看到 summary 数字，还能看到每个文件的格式、列名、行数、hash、是否重复，为后续字段识别和数据清洗确认做准备。

## Step 008：文件资产列表与最近上传明细

- 日期：2026-07-17
- 目标：补齐实验文件资产的可见性，让研发人员不仅看到审计 summary 数字，还能检查每个文件的格式、字段、行数、hash 和解析状态。
- 本步范围：新增按实验查询唯一文件资产列表的后端接口，并在实验页展示资产明细；暂不实现文件内容预览、字段映射编辑、单位转换确认和时间轴对齐。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_list_experiment_file_assets_returns_uploaded_file_details -q
```

初始结果：

```text
405 Method Not Allowed
```

原因：已有 `POST /experiments/{experiment_id}/files`，但尚无对应 `GET /experiments/{experiment_id}/files`。

实现后专项测试：

```text
8 passed
```

## 已实现能力

后端新增：
- `GET /experiments/{experiment_id}/files`
- `ExperimentFileService.list_file_assets(experiment_id)`
- 返回该实验下唯一文件资产列表，包括：
  - `assetId`
  - `experimentId`
  - `originalName`
  - `detectedFormat`
  - `parseStatus`
  - `rowCount`
  - `columnNames`
  - `contentHash`
  - `duplicate`
  - `duplicateOfAssetId`

前端新增/接入：
- `apps/web/lib/api.ts`：新增 `getExperimentFileAssets(experimentId)`。
- `apps/web/components/experiments/experiment-file-assets-card.tsx`：新增“最近上传文件资产”明细卡片。
- `apps/web/app/experiments/page.tsx`：并行读取文件资产列表，并在上传卡片/审计 summary 后展示资产表。

## 设计说明

本步让 DataCollectionLocalizationAgent 的底层数据入口从“只知道发生过上传”推进到“能看到已沉淀的数据资产”。后续字段识别、单位转换、时间轴对齐和人工确认都可以基于这张资产表继续展开。

当前资产列表返回的是唯一资产视角：同一实验内重复内容会复用同一资产。重复上传行为仍可通过 file-audits 查看。

## 修改文件

- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-file-assets-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
8 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
32 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 009 建议实现：新增字段识别/标准化建议能力。基于文件资产的 `columnNames` 生成标准字段映射建议，例如 `Temp` → `temperature_c`、`pH` → `ph`、`rpm` → `agitation_rpm`，并标出需要人工确认的字段，为后续清洗和时间轴对齐做准备。

## Step 009：字段识别与标准化建议

- 日期：2026-07-17
- 目标：把设备文件里的原始列名转成平台可理解的标准字段建议，并给出置信度、单位、解释原因和人工确认标记。
- 本步范围：基于已上传文件资产的 `columnNames` 做规则型识别；暂不写入最终字段映射、不执行数据清洗、不做单位换算、不调用 LLM。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_field_mapping_suggestions_standardize_known_device_columns -q
```

初始结果：

```text
404 Not Found
```

原因：尚无字段映射建议接口。

实现后专项测试：

```text
9 passed
```

## 已实现能力

后端新增：
- `GET /experiments/{experiment_id}/field-mapping-suggestions`
- `ExperimentFileService.suggest_field_mappings(experiment_id)`
- 字段映射响应模型：
  - `ExperimentFieldMappingSuggestion`
  - `ExperimentAssetFieldMappingSuggestions`
  - `ExperimentFieldMappingSuggestionResponse`

当前规则库可识别：
- `time` / `timestamp` / `datetime` → `timestamp`
- `Temp` / `temperature` / `temperatureC` → `temperature_c`
- `pH` → `ph`
- `rpm` / `agitation_rpm` → `agitation_rpm`
- `OD600` → `optical_density_600`
- 未知字段 → `standardField = null`，并标记 `requiresHumanConfirmation = true`

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增字段映射建议 schema/type。
- `apps/web/lib/api.ts`：新增 `getExperimentFieldMappingSuggestions(experimentId)`。
- `apps/web/components/experiments/experiment-field-mapping-card.tsx`：新增字段识别与标准化建议卡片。
- `apps/web/app/experiments/page.tsx`：并行读取字段映射建议，并展示在文件资产表之后。

## 设计说明

本步是 DataCollectionLocalizationAgent 从“文件收集”进入“字段理解”的第一步。为了控制幻觉和保证可解释性，当前使用确定性规则库，而不是直接让 LLM 猜字段含义。每条建议都带有：
- 原始字段
- 标准字段
- 展示名
- 单位
- 置信度
- 是否需要人工确认
- 解释原因

这为后续人工确认、企业字段词典、单位转换、时间轴对齐和数据清洗日志提供基础。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-field-mapping-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
9 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
33 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 010 建议实现：新增“字段映射人工确认”能力。用户可以确认或修改系统建议，把最终字段映射保存为实验级配置，为后续单位转换、数据清洗和时间轴对齐提供可信输入。

## Step 010：字段映射人工确认

- 日期：2026-07-17
- 目标：把系统生成的字段映射建议转化为实验级“已确认字段映射配置”，为后续清洗、单位转换、时间轴对齐和建模提供可信输入。
- 本步范围：支持保存和读取确认后的字段映射；前端支持一键确认当前可识别字段。暂不实现未知字段的手动编辑表单、字段词典管理和数据库持久化。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_confirm_field_mappings_saves_experiment_level_mapping_configuration -q
```

初始结果：

```text
404 Not Found
```

原因：尚无字段映射确认保存接口。

实现后专项测试：

```text
10 passed
```

## 已实现能力

后端新增：
- `POST /experiments/{experiment_id}/field-mappings/confirm`
- `GET /experiments/{experiment_id}/field-mappings`
- `ExperimentConfirmFieldMappingsRequest`
- `ExperimentConfirmedFieldMapping`
- `ExperimentConfirmedFieldMappingSet`
- `ExperimentFileService.confirm_field_mappings(...)`
- `ExperimentFileService.get_confirmed_field_mappings(...)`

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增确认字段映射 schema/type。
- `apps/web/lib/api.ts`：新增 `confirmExperimentFieldMappings(...)` 和 `getExperimentConfirmedFieldMappings(...)`。
- `apps/web/components/experiments/experiment-field-mapping-confirm-card.tsx`：新增字段映射人工确认卡片。
- `apps/web/app/experiments/page.tsx`：读取已确认映射并展示确认入口。

## 设计说明

本步将 DataCollectionLocalizationAgent 的字段识别结果推进到“人工确认闭环”。当前前端一键确认所有可识别字段，未知字段仍保留为待确认，避免系统把低置信度内容强行写入清洗配置。

保存后的字段映射配置是后续步骤的可信输入：
- 单位转换
- 数据清洗
- 时间轴对齐
- 特征工程
- 建模与报告解释

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-field-mapping-confirm-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
10 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
34 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 011 建议实现：新增“未知字段手动编辑/企业字段词典扩展”能力。用户可以把未知字段手动映射到标准字段，或新增企业自定义字段词典条目，让系统在后续实验中自动识别同类字段。

## Step 011：未知字段手动编辑与企业字段词典扩展

- 日期：2026-07-17
- 目标：让未知字段可以被人工沉淀为企业字段词典规则，使后续字段识别优先使用企业自定义知识，减少重复人工判断。
- 本步范围：支持实验级字段词典新增/读取，并让字段映射建议优先匹配该词典；前端提供最小词典扩展表单。暂不实现全局企业词典、多租户权限、词典版本管理和批量导入。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_custom_field_dictionary_teaches_suggestions_for_unknown_columns -q
```

初始结果：

```text
404 Not Found
```

原因：尚无企业字段词典接口。

实现后专项测试：

```text
11 passed
```

## 已实现能力

后端新增：
- `POST /experiments/{experiment_id}/field-dictionary`
- `GET /experiments/{experiment_id}/field-dictionary`
- `ExperimentFieldDictionaryEntry`
- `ExperimentFieldDictionaryUpsertRequest`
- `ExperimentFieldDictionary`
- `ExperimentFileService.upsert_field_dictionary(...)`
- `ExperimentFileService.get_field_dictionary(...)`

字段识别逻辑更新：
- `suggest_field_mappings(...)` 会优先读取当前实验的企业字段词典。
- 企业词典命中时返回：
  - `confidenceScore = 0.9`
  - `requiresHumanConfirmation = false`
  - `reason = "Matched enterprise field dictionary entry."`

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增企业字段词典 schema/type。
- `apps/web/lib/api.ts`：新增 `upsertExperimentFieldDictionary(...)` 和 `getExperimentFieldDictionary(...)`。
- `apps/web/components/experiments/experiment-field-dictionary-card.tsx`：新增企业字段词典扩展卡片。
- `apps/web/app/experiments/page.tsx`：读取词典并展示扩展入口。

## 设计说明

本步让 DataCollectionLocalizationAgent 具备“企业知识沉淀”的雏形：当系统遇到未知列名时，用户不只是一次性修正，而是可以把修正保存为字段词典规则。后续同名字段会自动识别，这符合项目“沉淀企业自己的实验数据库和规律库”的方向。

当前词典是实验级内存态，后续应升级为数据库持久化和企业级共享词典。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-field-dictionary-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
11 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
35 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 012 建议实现：基于“已确认字段映射”新增数据清洗预览能力。系统应输出每个文件的标准字段视图、缺失值/无法解析值统计、单位转换计划和清洗日志，为正式数据入库前提供人工确认依据。

## Step 012：数据清洗预览

- 日期：2026-07-17
- 目标：基于已确认字段映射生成标准字段视图，并输出缺失值、非法数值、未映射列和清洗日志，作为正式入库前的人工确认依据。
- 本步范围：实现清洗预览，不直接写入实验数据库；暂不做持久化清洗结果、复杂单位换算、跨文件时间轴对齐和异常插补。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_cleaning_preview_uses_confirmed_mappings_and_reports_quality_issues -q
```

初始结果：

```text
404 Not Found
```

原因：尚无清洗预览接口。

实现后专项测试：

```text
12 passed
```

## 已实现能力

后端新增：
- `GET /experiments/{experiment_id}/cleaning-preview`
- `ExperimentCleaningQualitySummary`
- `ExperimentAssetCleaningPreview`
- `ExperimentCleaningPreviewResponse`
- `ExperimentFileService.preview_cleaning(experiment_id)`

服务层增强：
- `StoredExperimentFileAsset` 现在保存解析后的原始数据行 `rows`。
- `_parse_table_text(...)` 返回 `columnNames`、`rowCount` 和行字典。
- 清洗预览基于已确认字段映射生成 `cleanedRows`。
- 除 `timestamp` 外，标准字段默认按数值解析。
- 统计：
  - `missingValueCount`
  - `invalidNumericCount`
  - `unmappedColumnCount`
- 生成 `cleaningLogs`，例如：
  - `Missing value: Temp at row 2`
  - `Invalid numeric value: rpm=bad at row 2`

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增清洗预览 schema/type。
- `apps/web/lib/api.ts`：新增 `getExperimentCleaningPreview(experimentId)`。
- `apps/web/components/experiments/experiment-cleaning-preview-card.tsx`：新增数据清洗预览卡片。
- `apps/web/app/experiments/page.tsx`：并行读取并展示清洗预览。

## 设计说明

本步让 DataCollectionLocalizationAgent 从“字段确认”进入“可解释清洗”。系统不会直接把数据写入数据库，而是先展示标准字段视图和质量问题，让研发人员确认数据是否可信。

当前版本刻意保守：
- 只预览，不入库。
- 只做基础数值解析，不做插补。
- 清洗日志保留具体字段和行号，方便追溯。

这符合项目要求里的“数据怎么被清洗、字段怎么被识别、哪些地方需要人工确认”的展示闭环。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-cleaning-preview-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
12 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
36 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 013 建议实现：新增“时间轴对齐预览”。基于已清洗的标准字段和 `timestamp`，对多设备数据按时间轴进行对齐，输出采样频率差异、缺失时间点和对齐后的宽表预览，为后续特征工程和建模准备输入。

## Step 013：时间轴对齐预览

- 日期：2026-07-17
- 目标：基于清洗后的标准字段视图，按 `timestamp` 合并多设备数据，生成对齐后的宽表预览，并暴露缺失单元和设备时间点摘要。
- 本步范围：实现预览级时间轴对齐；暂不做插值、重采样、采样频率自动推断、时区标准化和正式入库。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_alignment_preview_merges_cleaned_assets_by_timestamp -q
```

初始结果：

```text
404 Not Found
```

原因：尚无时间轴对齐预览接口。

实现后专项测试：

```text
13 passed
```

## 已实现能力

后端新增：
- `GET /experiments/{experiment_id}/alignment-preview`
- `ExperimentAlignmentAssetSummary`
- `ExperimentAlignmentPreviewResponse`
- `ExperimentFileService.preview_alignment(experiment_id)`

对齐逻辑：
- 复用 `preview_cleaning(...)` 的标准字段视图。
- 汇总所有非空 `timestamp`。
- 将多设备字段合并为统一宽表 `alignedRows`。
- 缺失设备字段填充 `null`。
- 统计：
  - `assetCount`
  - `timestampCount`
  - `missingCellCount`
- 输出：
  - `assetSummaries`
  - `alignmentLogs`

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增时间轴对齐预览 schema/type。
- `apps/web/lib/api.ts`：新增 `getExperimentAlignmentPreview(experimentId)`。
- `apps/web/components/experiments/experiment-alignment-preview-card.tsx`：新增时间轴对齐预览卡片。
- `apps/web/app/experiments/page.tsx`：并行读取并展示对齐结果。

## 设计说明

本步让 DataCollectionLocalizationAgent 从“单文件清洗预览”进入“多设备数据对齐预览”。这一步是后续特征工程和建模的关键，因为模型不能直接吃多台设备各自独立的时间序列，必须先形成同一时间轴下的宽表。

当前版本不自动插值，原因是插值策略会影响科研结论。系统只暴露缺失位置和对齐日志，留给后续人工确认或规则配置。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-alignment-preview-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
13 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
37 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 014 建议实现：新增“特征工程预览”。基于对齐后的宽表，计算基础统计特征、变化率、窗口均值和异常点提示，为后续自动建模和规律沉淀准备特征输入。

## Step 014：特征工程预览

- 日期：2026-07-17
- 目标：基于时间轴对齐后的宽表，计算数值字段的基础统计、变化量、窗口均值和异常点提示，为后续自动建模和规律沉淀准备特征输入。
- 本步范围：实现预览级特征摘要；暂不训练模型、不做特征选择、不做复杂窗口配置和异常确认入库。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_feature_preview_computes_statistics_delta_and_anomaly_hints -q
```

初始结果：

```text
404 Not Found
```

原因：尚无特征工程预览接口。

实现后专项测试：

```text
14 passed
```

## 已实现能力

后端新增：
- `GET /experiments/{experiment_id}/feature-preview`
- `ExperimentFeatureSummary`
- `ExperimentFeatureAnomalyHint`
- `ExperimentFeaturePreviewResponse`
- `ExperimentFileService.preview_features(experiment_id)`

特征计算逻辑：
- 复用 `preview_alignment(...)` 的对齐宽表。
- 对每个数值字段计算：
  - `count`
  - `min`
  - `max`
  - `mean`
  - `first`
  - `last`
  - `delta`
  - `windowMean`
- 异常点提示：
  - 相邻点绝对变化 `>= 5`
  - 或相对变化 `>= 20%`

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增特征工程预览 schema/type。
- `apps/web/lib/api.ts`：新增 `getExperimentFeaturePreview(experimentId)`。
- `apps/web/components/experiments/experiment-feature-preview-card.tsx`：新增特征工程预览卡片。
- `apps/web/app/experiments/page.tsx`：并行读取并展示特征预览。

## 设计说明

本步让 DataCollectionLocalizationAgent 从“对齐数据”进入“建模输入准备”。系统现在可以把对齐宽表转换成基础特征摘要，并指出可能异常的变化点。

当前异常规则是保守启发式，只作为提示，不作为自动结论。后续应加入人工确认、领域阈值配置、窗口配置和模型训练记录。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-feature-preview-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
14 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
38 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 015 建议实现：新增“建模准备/数据集快照”能力。将已确认字段映射、清洗预览、对齐宽表和特征摘要打包成一个可追溯的数据集快照，为后续自动建模、模型训练记录和报告生成提供稳定输入。

## Step 015：建模准备 / 数据集快照

- 日期：2026-07-18
- 目标：将当前实验的数据资产、已确认字段映射、时间轴对齐结果和特征摘要打包成一个可追溯的数据集快照，作为后续自动建模、训练记录和报告生成的稳定输入。
- 本步范围：实现内存态最新快照创建/读取；暂不做数据库持久化、快照版本列表、权限控制和模型训练任务触发。

## TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py::test_dataset_snapshot_packages_modeling_ready_experiment_state -q
```

初始结果：

```text
404 Not Found
```

原因：尚无数据集快照接口。

实现后专项测试：

```text
15 passed
```

## 已实现能力

后端新增：
- `POST /experiments/{experiment_id}/dataset-snapshots`
- `GET /experiments/{experiment_id}/dataset-snapshots/latest`
- `ExperimentDatasetSnapshot`
- `ExperimentFileService.create_dataset_snapshot(experiment_id)`
- `ExperimentFileService.get_latest_dataset_snapshot(experiment_id)`

快照内容包括：
- `snapshotId`
- `experimentId`
- `assetCount`
- `mappingCount`
- `alignedRowCount`
- `featureCount`
- `anomalyCount`
- `contentHash`
- `status`
- `createdAt`

快照 `contentHash` 基于：
- 文件资产 ID
- 文件内容 hash
- 已确认字段映射数量
- 对齐宽表
- 特征摘要
- 异常提示

前端新增/接入：
- `apps/web/lib/schemas.ts`：新增数据集快照 schema/type。
- `apps/web/lib/api.ts`：新增 `createExperimentDatasetSnapshot(...)` 和 `getLatestExperimentDatasetSnapshot(...)`。
- `apps/web/components/experiments/experiment-dataset-snapshot-card.tsx`：新增建模数据集快照卡片。
- `apps/web/app/experiments/page.tsx`：读取并展示最新快照，支持创建/刷新快照。

## 设计说明

本步把第一阶段数据处理链条收束成一个“可交付数据资产”。它不是简单展示中间结果，而是把当前实验处理状态固定下来，形成后续建模、报告、复现实验和审计追踪的稳定输入。

当前快照仍是内存态，后续应升级为数据库持久化，并支持多版本快照、差异比较、训练任务绑定和报告生成引用。

## 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-dataset-snapshot-card.tsx`
- `apps/web/app/experiments/page.tsx`

## 验证

后端专项测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -q
15 passed
```

后端全量测试：

```text
py -m pytest apps/api/tests -q
39 passed
```

前端类型检查：

```text
npm.cmd run typecheck
tsc --noEmit
```

结果：通过。

## 下一步

Step 016 建议实现：新增“建模任务准备/训练计划预览”。基于数据集快照生成建模任务草案，包括目标字段、候选特征、训练/验证拆分、推荐模型类型、评估指标和风险提示，作为深度学习 agent 介入前的可解释入口。
## Step 016 - 建模任务预览（2026-07-17）

本步目标：在“数据集快照”之后补上一层可展示的建模任务草案，让平台能明确说明下一步准备如何训练、评估和控风险，而不是直接跳到黑箱建模。

### TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -k modeling_plan_preview -q
```

初始结果：

```text
404 Not Found
```

失败原因正确：`/experiments/{experiment_id}/modeling-plan-preview` 尚未实现。

实现后专项复测：

```text
1 passed, 15 deselected
```

### 已实现能力

后端新增：

- `GET /experiments/{experiment_id}/modeling-plan-preview`
- `ExperimentModelingPlanPreview`
- `ExperimentFileService.preview_modeling_plan(experiment_id)`

返回内容包括：

- `snapshotId`
- `targetField`
- `candidateFeatures`
- `recommendedModelType`
- `trainSplitRatio`
- `validationSplitRatio`
- `evaluationMetrics`
- `riskHints`
- `status`

当前演示规则：

- 以已确认字段映射中的首个非 `timestamp` 字段作为默认目标字段
- 其余非时间字段作为候选特征
- 若存在时间轴对齐结果，则推荐 `time_series_regression`
- 默认评估指标为 `mae / rmse / r2`
- 当对齐行数过少、特征过少、异常提示存在时，自动生成风险提示

前端新增：

- `apps/web/lib/schemas.ts`：新增建模任务预览 schema/type
- `apps/web/lib/api.ts`：新增 `getExperimentModelingPlanPreview(...)`
- `apps/web/components/experiments/experiment-modeling-plan-card.tsx`：新增建模任务预览卡片
- `apps/web/app/experiments/page.tsx`：接入页面展示

## Step 017 - 训练任务执行卡（2026-07-17）

本步目标：把“建模计划预览”继续推进为一个真正可展示的多 agent 训练任务对象，让页面能展示训练任务创建、agent 分工与状态流转，而不是只停留在训练计划层。

### TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -k training_task_preview -q
```

初始结果：

```text
404 Not Found
```

失败原因正确：`/experiments/{experiment_id}/training-tasks` 尚未实现。

实现后专项复测：

```text
1 passed, 16 deselected
```

### 已实现能力

后端新增：

- `POST /experiments/{experiment_id}/training-tasks`
- `GET /experiments/{experiment_id}/training-tasks/latest`
- `ExperimentTrainingTaskPreview`
- `ExperimentTrainingAgentStage`
- `ExperimentFileService.create_training_task(experiment_id)`
- `ExperimentFileService.get_latest_training_task(experiment_id)`

训练任务当前演示能力：

- 从现有建模计划自动生成 demo 训练任务
- 记录目标字段、推荐模型、评估指标、时间戳
- 生成三段 agent 分工：
  - `data_agent`
  - `modeling_agent`
  - `report_agent`
- 演示状态自动推进：
  - `queued`
  - `running`
  - `completed`

前端新增：

- `apps/web/lib/schemas.ts`：新增训练任务 schema/type
- `apps/web/lib/api.ts`：新增训练任务创建与读取 API
- `apps/web/components/experiments/experiment-training-task-card.tsx`：新增训练任务执行卡片
- `apps/web/app/experiments/page.tsx`：接入页面展示

### 设计说明

这一步仍然是展示型实现，不做真实训练，不产出真实模型文件，也不调用本地 LLM。它的价值在于先把“多核 agent 如何协同执行训练任务”这层交互和结构稳定下来，后续再把 demo 状态机替换成真实 worker、真实模型和真实报告链路即可。

### 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-training-task-card.tsx`
- `apps/web/app/experiments/page.tsx`

## Step 018 - 训练结果摘要卡（2026-07-17）

本步目标：在训练任务执行卡之后，补上训练完成后的结果展示层，让平台能够说明“训练后得到了什么、可信度如何、风险在哪里、下一步建议是什么”。

### TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -k training_result_summary -q
```

初始结果：

```text
404 Not Found
```

失败原因正确：`/experiments/{experiment_id}/training-results/latest` 尚未实现。

实现后专项复测：

```text
1 passed, 17 deselected
```

### 已实现能力

后端新增：

- `GET /experiments/{experiment_id}/training-results/latest`
- `ExperimentTrainingResultMetrics`
- `ExperimentTrainingResultSummary`
- `ExperimentFileService.get_latest_training_result(experiment_id)`

结果摘要当前演示内容：

- 训练指标：
  - `mae`
  - `rmse`
  - `r2`
- `confidenceLevel`
- `riskNotes`
- `recommendations`
- `manualReviewItems`

演示逻辑说明：

- 基于训练任务、数据快照和特征异常提示生成 demo 结果摘要
- 当样本偏少或存在异常提示时，置信度降为 `medium`
- 结果卡会明确声明当前仍是 demo 训练流，不是最终真实模型结论

前端新增：

- `apps/web/lib/schemas.ts`：新增训练结果摘要 schema/type
- `apps/web/lib/api.ts`：新增读取训练结果摘要 API
- `apps/web/components/experiments/experiment-training-result-card.tsx`：新增训练结果摘要卡片
- `apps/web/app/experiments/page.tsx`：接入页面展示

### 设计说明

这一步继续围绕“解释链路可视化”推进，不追求真实训练，而是优先把指标、置信度、风险、建议、人工复核点这些用户真正关心的输出显式化。这样后续接入真实本地模型或真实 worker 时，展示层和解释层都可以直接复用。

### 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-training-result-card.tsx`
- `apps/web/app/experiments/page.tsx`

## Step 019 - 研发建议书摘要卡（2026-07-17）

本步目标：把训练结果进一步整理为可用于研发汇报和后续交付展示的“建议书摘要对象”，让平台不仅能展示分析过程，还能展示一版结构化结论。

### TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -k research_brief_summary -q
```

初始结果：

```text
404 Not Found
```

失败原因正确：`/experiments/{experiment_id}/research-brief/latest` 尚未实现。

实现后专项复测：

```text
1 passed, 18 deselected
```

### 已实现能力

后端新增：

- `GET /experiments/{experiment_id}/research-brief/latest`
- `ExperimentResearchBriefSummary`
- `ExperimentFileService.get_latest_research_brief(experiment_id)`

摘要当前包含：

- `title`
- `objective`
- `dataSummary`
- `modelSummary`
- `riskSummary`
- `nextActions`
- `manualConfirmationItems`
- `status`

当前演示逻辑：

- 基于训练结果摘要自动拼装研发建议书摘要
- 形成“目标 - 数据 - 模型 - 风险 - 下一步动作 - 人工确认”结构
- 作为后续正式报告、论文 agent、导出文档的上游对象

前端新增：

- `apps/web/lib/schemas.ts`：新增研发建议书摘要 schema/type
- `apps/web/lib/api.ts`：新增读取研发建议书摘要 API
- `apps/web/components/experiments/experiment-research-brief-card.tsx`：新增研发建议书摘要卡片
- `apps/web/app/experiments/page.tsx`：接入页面展示

### 设计说明

这一步仍然是展示型实现，不直接生成 Word、PDF 或论文正文，而是先把建议书的核心结构做成稳定对象。这样后续无论接 PaperOrchestra、导出报告，还是接本地 LLM 生成正式文本，都可以直接复用这一层。

### 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-research-brief-card.tsx`
- `apps/web/app/experiments/page.tsx`

## Step 020 - 仿真输入 / 条件调参卡（2026-07-17）

本步目标：把研发建议书摘要继续推进为仿真模拟前的标准输入对象，让平台开始显式展示“接下来准备如何调参、如何进入仿真”的过程。

### TDD 记录

先新增失败测试：

```text
py -m pytest apps/api/tests/test_experiment_file_upload.py -k simulation_input_summary -q
```

初始结果：

```text
404 Not Found
```

失败原因正确：`/experiments/{experiment_id}/simulation-inputs/latest` 尚未实现。

实现后专项复测：

```text
1 passed, 19 deselected
```

### 已实现能力

后端新增：

- `GET /experiments/{experiment_id}/simulation-inputs/latest`
- `ExperimentSimulationRange`
- `ExperimentSimulationCandidatePlan`
- `ExperimentSimulationInputSummary`
- `ExperimentFileService.get_latest_simulation_input(experiment_id)`

当前仿真输入摘要包含：

- `targetField`
- `objective`
- `recommendedRanges`
- `candidatePlans`
- `manualConfirmationItems`
- `status`

当前演示逻辑：

- 基于研发建议书摘要生成仿真前的参数输入对象
- 给出温度、pH、时长等推荐区间
- 自动生成三组候选方案：
  - 稳健基线方案
  - 产量拉升方案
  - 保守验证方案
- 明确哪些参数仍需人工确认

前端新增：

- `apps/web/lib/schemas.ts`：新增仿真输入摘要 schema/type
- `apps/web/lib/api.ts`：新增读取仿真输入摘要 API
- `apps/web/components/experiments/experiment-simulation-input-card.tsx`：新增仿真输入/条件调参卡片
- `apps/web/app/experiments/page.tsx`：接入页面展示

### 设计说明

这一步还不是正式仿真，也没有接设备控制，而是先把“仿真前需要哪些标准化输入”这一层显式化。这样后面无论接仿真 agent、产线条件优化 agent，还是接真实设备接口，都有稳定的上游对象可以复用。

### 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-simulation-input-card.tsx`
- `apps/web/app/experiments/page.tsx`

### 设计说明

这一步仍然是“展示完整研发过程”的一部分，不做真实训练，也不产出最终模型文件。它的作用是把“准备怎么建模”本身做成可解释对象，便于你后续接入本地 LLM、多 agent 调度和真实训练任务编排。

### 修改文件

- `apps/api/app/schemas/experiments.py`
- `apps/api/app/services/experiment_file_service.py`
- `apps/api/app/routers/experiments.py`
- `apps/api/tests/test_experiment_file_upload.py`
- `apps/web/lib/schemas.ts`
- `apps/web/lib/api.ts`
- `apps/web/components/experiments/experiment-modeling-plan-card.tsx`
- `apps/web/app/experiments/page.tsx`
## Step 021 - 实验归档与实验工作区骨架（2026-07-19）

### 本步目标

把平台默认入口调整为“实验归档”，建立“选择实验 / 新建实验 → 数据分析 → 仿真模拟 → 工艺优化”的单实验工作流骨架，为后续多智能体执行过程、模型版本和人工控制能力提供统一入口。

### TDD 记录

- 后端先新增归档列表、实验概览和未知实验测试；首次运行因接口尚不存在返回 `404`，随后实现接口并通过测试。
- 前端先新增类型契约测试；首次运行因 schema、API 方法和组件尚不存在而失败，随后补齐实现并通过 TypeScript 检查。

### 已实现能力

- 新增实验归档摘要与单实验工作区概览领域模型。
- 新增 `GET /experiments/archive` 与 `GET /experiments/{experimentId}/overview`。
- 首页改为中文“实验归档”，展示实验数量、阶段、状态、结果摘要和模型置信度。
- 新建实验提供行业样例、上传实验文件、空白实验三个入口。
- 单实验工作区提供总览、数据分析、仿真模拟、工艺优化四个页面入口。
- 阶段门禁根据实验状态展示可进入或锁定原因；仿真与优化仍使用现有 mock 工作台承接演示。
- 页面明确展示研发实验建议边界、具体风险、验证指标和模型依据，不使用笼统风险等级代替证据。

### 架构说明

- 当前版本继续遵守第一版 mock 边界，不接真实大模型、真实数据库或实际产线控制。
- 后续多智能体编排优先采用状态图、检查点、人工确认和可恢复执行思想；对外展示可审计事件与算法步骤，不展示模型隐藏思维链。
- `DataCollectionLocalizationAgent` 作为业务编排角色，底层解析和上传能力保持为工具调用，不再把文件导入工具误作顶层智能体。

### 验证记录

- 后端测试：`py -m pytest apps/api/tests -q`
- 前端类型检查：`npm.cmd run typecheck`
- 前端生产构建：`npm.cmd run build`
- HTTP 冒烟检查：健康接口、实验归档、新建实验、实验总览与阶段页面。
- 浏览器自动视觉检查受本机浏览器运行时路径错误影响，保留人工页面验收；该问题不影响 HTTP 服务和构建检查。

### 下一步

实现数据分析多智能体状态图的演示闭环：任务拆解、智能体执行事件、等待/运行/完成/失败状态、人工提示词引导、停止与重新开始，并把事件记录沉淀到单实验时间线。
## Step 022 - 数据分析多智能体执行中心（2026-07-19）

### 本步目标

把单实验数据分析页从阶段占位入口升级为可演示的七节点多智能体执行中心，支持可审计算法轨迹、显式状态转移和人工控制，为后续真实 LangGraph 检查点执行器预留稳定 API 契约。

### TDD 记录

- 后端先新增状态图、提示词引导、停止与版本化重启测试；首次运行 3 项均因接口不存在返回 `404`，实现后转为通过。
- 前端先新增 API/类型契约测试和组件契约测试；首次分别因导出与组件不存在而失败，实现后通过 TypeScript 检查。

### 已实现能力

- 新增业务编排入口 `AgentOrchestrator`，第一版使用确定性内存状态图，不接真实训练、LLM 或数据库。
- 七个节点依次为数据收集定位、字段识别、清洗对齐、特征工程、数学建模、模型评估和人工确认。
- 每个节点记录输入、方法/公式、指标、输出、进度和时间状态；统一事件时间线记录状态变化与人工指令。
- 支持显式推进 mock 工作流、终止当前运行、保留旧记录并创建新版本重启。
- 支持提示词引导的结构化影响预览；普通字段规则可在安全检查点排队应用，影响特征或模型的引导要求终止并重启。
- 数据分析页展示总进度、七节点状态图、节点算法进程、审计事件、运行版本和人工控制区。
- 页面明确说明当前为 mock 多智能体演示，输出仅作为研发实验建议；不展示不可验证的隐藏思维链。

### 开源架构映射

- 采用 LangGraph 风格的状态节点、合法边、运行版本、人工中断和检查点契约，但本阶段未增加外部运行时依赖。
- 保留 `AgentOrchestrator` 适配层，后续接入真实 LangGraph、本地 LLM 或训练队列时不改变页面与核心 API。
- `DataCollectionLocalizationAgent` 继续作为业务首节点，底层文件解析保持为工具调用。

### 验证记录

- 后端：`py -m pytest apps/api/tests -q`，55 项通过。
- 前端：`npm.cmd run typecheck` 通过；`npm.cmd run build` 通过。
- HTTP：创建运行、推进节点、引导预览、确认排队、终止、v2 重启和数据分析页面均通过。
- `git diff --check` 未发现空白错误，仅有 Windows 行尾转换提示。
- 独立审查后补齐跨实验/跨运行引导隔离、安全检查点越界防护、重复应用防护、未知实验拒绝、结构化人工决策，以及“模型级引导随新版本重启”闭环。

### 下一步

进入仿真阶段工作区：实现模型校验、系统初始化、原料准备、核心生产、下游处理、产物收集和结果评估七环节的运行状态，以及虚拟产线、仪表盘和精确文本参数临时试算。
## Step 023 - 仿真运行状态图与虚拟产线（2026-07-19）

### 本步目标

把实验仿真页从即时预测表单升级为有准入门禁、七环节运行过程、虚拟设备流向、精确参数输入和临时试算快照的仿真工作区。

### TDD 记录

- 后端先新增七环节、准入门禁、临时试算隔离和停止/重启测试；首次 4 项均因实验级仿真接口不存在返回 `404`，实现后转为通过。
- 前端先新增仿真运行类型/API 契约与工作台组件契约；首次因导出和组件不存在而失败，实现后通过 TypeScript 检查。

### 已实现能力

- 新增 `SimulationRunOrchestrator`，使用确定性状态图编排模型校验、系统初始化、原料准备、核心生产、下游处理、产物收集和结果评估七个环节。
- 每个环节包含设备、状态、进度、等待原因、输入、模型依据、输出与事件记录。
- 后端根据实验工作区 `canRun` 二次执行仿真准入，未通过实验只能读取结构模板，不能创建运行或提交试算。
- 支持仿真终止、保留记录和父子版本重启。
- 精确参数使用数值文本框、固定单位、范围和小数精度提示，不再使用滑块作为主要输入。
- 临时试算生成独立快照、参数差异、预测指标、具体风险和验证指标，不覆盖正式参数、模型或实验结果版本。
- 页面展示可靠性、模型版本、总进度、仿真时钟、预计剩余时间、虚拟设备流向和事件记录。

### 边界

- 当前为确定性 mock 仿真和科研过程可视化，不接真实数字孪生引擎，不连接或控制真实产线设备。
- 所有预测和试算结果仅作为研发实验建议。

### 验证记录

- 后端：`py -m pytest apps/api/tests -q`，61 项通过。
- 前端：`npm.cmd run typecheck` 与 `npm.cmd run build` 通过。
- `git diff --check` 未发现空白错误，仅有 Windows 行尾转换提示。
- 独立审查后补齐前后端数值范围/精度一致性、活动运行互斥锁、实时准入复核、实验专属正式参数、正式仿真结果、异常/重试路径、模型验证指标，以及试算置信度、具体风险与待验证指标展示。
- 最终复核进一步加入创建/重试共享原子锁和双线程并发回归测试，并补齐空值输入、新版本前端状态隔离、正式/临时结果切换和实验专属产线环节模板。
- 运行时页面检查发现并修复 `lineTemplateId` 误挂到实验总览 Zod schema 的字段归属问题；重建并重启后，归档、实验总览、已准入仿真页和未准入仿真页均返回 HTTP 200。

### 下一步

进入工艺优化工作区：实现三套候选方案、目标/约束权衡、精确参数编辑、正式提交、mock 权重重训和新实验结果版本。

## Step 024 - 工艺优化与版本化重训（2026-07-19）

### 本步目标

建立“三套候选方案 → 精确调参 → 正式提交 → 新训练数据版本 → mock 重训与评估 → 人工验收 → 新模型与新结果版本”的可演示闭环。

### 已实现能力

- 新增实验级 `OptimizationOrchestrator`，显式编排数据合并、权重重训、模型评估和人工验收。
- 未通过准入的实验只能预览；同一实验只允许一个活动运行。
- 三套方案均展示评分、置信度、预测区间、具体风险和验证指标。
- 精确文本参数执行范围与步长校验；正式提交后冻结并生成独立训练数据版本。
- 父模型、父结果保持只读；人工批准前不生成新模型或新结果。
- 审核记录操作者、原因、决定和影响范围；批准后生成带置信度、风险和验证指标的新结果。
- 工艺优化页支持方案选择、参数编辑、逐环节推进和人工批准或驳回。

### TDD 与验证记录

- 先写 4 项后端行为测试，首次因接口不存在返回 `404`，实现后通过。
- 全量后端 `py -m pytest apps/api/tests -q`：65 项通过。
- 前端 `npm.cmd run typecheck` 与 `npm.cmd run build`：通过。
- 当前保持第一版 mock 边界，不连接真实模型、数据库或产线设备；输出仅为研发实验建议。

## Step 025 - 工艺优化证据层与权威版本链（2026-07-19）

### 本步目标

补齐 Step 024 独立审查发现的解释证据、测试隔离和版本链断点，使下一轮优化能够以刚刚批准的新模型、新结果为父版本继续运行。

### 已实现能力

- 候选方案新增温度—pH 响应面采样点、相对基线改善、多目标评分、预测区间、风险、验证指标与推导依据。
- 页面新增响应面切片、多目标对比、训练轮次损失与验证分数、保留决策、运行事件和人工决策影响范围。
- 参数文本被再次修改后，正式提交按钮自动锁定，必须先保存，避免静默提交旧参数。
- 实验总览新增已验收 `resultVersion`，优化运行不再拼接虚构父结果版本。
- 新增第一版内存版本注册表；人工批准时比较父模型和父结果，并原子晋升新模型、新结果为实验当前权威版本。
- 下一轮优化自动引用上一轮批准的新版本，形成可验证的父子版本链。
- 优化测试使用独立 reset fixture，每项测试自行创建运行，不再依赖执行顺序。

### 验证记录

- 后端全量测试：65 项通过。
- 前端类型检查与生产构建：通过。
- HTTP 完整闭环：首轮生成 `model-012-v6-opt1 / result-012-v6`；紧接创建下一轮时，父版本准确变为相同的新版本；页面返回 HTTP 200。
- `git diff --check` 未发现空白错误，仅有 Windows 行尾提示。

### 当前边界与下一步

版本注册表仍为第一版内存实现，服务重启后恢复 mock 基线。下一阶段将把状态机接口抽象为可持久化运行时适配层，优先评估 LangGraph、AutoGen 或 CrewAI 等开源架构，并接入用户本地 LLM；在完成安全评估前仍不连接真实产线控制。

## Step 026 - 开源多智能体框架选型（2026-07-19）

- 核心编排选择 LangGraph 风格的有状态、可中断、可恢复运行时，并通过自有适配接口隔离具体依赖。
- CrewAI 保留为产品创新、文献研究和论文协作小队候选，不掌管权威版本事务。
- AutoGen 官方已进入维护模式，因此不作为新核心依赖。
- autoresearch 仅借鉴固定修改范围、固定资源预算、权威指标和实验保留/丢弃循环，不允许智能体任意修改平台代码或评估基准。
- 详细决策记录：`docs/architecture/agent-runtime-selection.md`。

## Step 027 - AgentRuntimeAdapter 领域协议（2026-07-19）

### 已实现能力

- 新增图、节点、合法边、运行上下文、命令、结构化节点结果、事件、快照与运行时适配器协议。
- 新增默认 `DeterministicRuntimeAdapter`，支持启动、幂等推进、停止、人工中断、结构化恢复、人工审核门禁、运行隔离和深拷贝快照。
- 节点输出统一包含证据引用、置信度、具体风险和验证指标，不展示不可验证的隐藏思维链。
- 明确标记该适配器为确定性运行时，不伪装为真实 LangGraph 或真实 LLM。

### TDD 与验证

- 先写运行时契约测试，首次因 `app.agent_runtime` 不存在而失败。
- 实现后运行时专项 3 项通过；后端全量 69 项通过。

### 下一步

把现有数据分析七节点迁移到 `DeterministicRuntimeAdapter`，让 `AgentOrchestrator` 降为业务编排和 DTO 映射层，同时保持现有 API 与页面完全兼容。

## Step 028 - 数据分析七节点迁移到统一运行时（2026-07-19）

### 本步目标

让数据分析七节点真正由 `AgentRuntimeAdapter` 驱动，而不是仅在业务层模拟状态；保持现有中文页面、提示词引导、停止、重启、人工审核和 REST 入口兼容。

### 已实现能力

- `AgentOrchestrator` 改为依赖 `AgentRuntimeAdapter` 协议，不再绑定确定性适配器具体类型。
- `RuntimeSnapshot` 成为节点状态、进度、结构化结果、审计事件和修订号的唯一执行状态源；业务 DTO 由纯投影函数生成。
- API 明确返回 `runtimeBackend`、`runtimeRunId` 和 `runtimeRevision`；页面显示“确定性状态图”，不伪装为真实 LangGraph。
- 推进接口加入 `expectedRevision + commandId`；并发、双击或网络重试不能连续跳过两个节点。
- 提示词在安全检查点的应用与节点推进合并为一次原子运行时命令。
- 独立状态 patch 同样具备修订号 CAS 和命令幂等；每个运行最多存在一条待应用引导。
- 创建、推进、停止、重启、引导和审核路径统一由编排锁保护。
- 重启所需引导在 runtime start 的初始状态中写入，不再产生先创建后 patch 的半完成子运行。
- `latest` 每次重新读取权威运行时快照，可观察异步中断；`interrupted` 已加入 Pydantic、Zod 和页面状态。
- 人工审核事件保留审核节点 ID，并正确投影 `completedAt`。

### 验证记录

- 运行时与数据分析专项：33 项通过。
- 后端全量：73 项通过。
- 前端类型检查与生产构建：通过。
- HTTP：数据分析页面返回 200；创建运行后从 revision 1 推进到 revision 2，节点准确进入 `schema-recognition`，最后事件为 `nodeStarted`。
- 并发回归：两个相同旧修订的推进请求只允许一个成功，另一个返回 409。
- 独立复审最终未发现 Critical 或 Important 问题。

### 下一步

实现可选 `LangGraphRuntimeAdapter` 的惰性加载和能力状态接口；依赖未安装时安全回退到 deterministic。随后接入用户本地 OpenAI-compatible LLM，并保持确定性清洗、数学评估、版本晋升和人工门禁不交给大模型。
