# AGENTS.md

## 项目角色

本项目是“AKK 菌配方自动生成可视化平台”的第一版工程实现仓库。当前阶段目标是完成一个可运行的 UI + API 闭环，用于内部食品研发场景的方案探索。

## 核心边界

- 第一版只用于内部研发，不输出可直接上市的最终食品配方。
- 所有配方输出必须明确标记为“研发实验建议”。
- 所有预测结果必须展示置信度、风险提示和需要验证的实验指标。
- 第一版使用 mock 数据和规则模板。
- 第一版不接真实大模型、不接真实数据库、不做登录系统。

## 页面范围

第一版页面包括：

- Dashboard
- AKK 产物库
- 产物详情
- 配方生成
- 配方结果

## 命名约定

接口字段、数据字段和代码命名使用英文：

- `camelCase` for JSON fields and frontend variables.
- `PascalCase` for component names and type/interface names.
- `kebab-case` for route paths.
- `snake_case` only when required by external systems.

## 工程协作原则

- 先完成 mock 闭环，再替换真实能力。
- 业务逻辑说明使用中文，代码和接口契约使用英文。
- 新增功能前先更新或确认对应文档。
- 不在第一版引入登录、权限、真实数据库或真实模型调用。
- 不把生成结果描述为最终可生产配方。

