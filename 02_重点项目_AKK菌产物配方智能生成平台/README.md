# AKK 菌配方自动生成可视化平台

面向食品研发人员的内部研发 Web 平台。Phase 2 已形成产品级 mock 工作台：Dashboard、AKK 产品库、产品详情、分步骤配方生成和配方结果展示。

所有配方结果均为“研发实验建议”，不代表最终上市配方。

## Monorepo 结构

```text
apps/
  api/      FastAPI + Pydantic backend
  web/      Next.js App Router + TypeScript + Tailwind CSS frontend
data/
  mock/     First-version mock JSON data
docs/
  API_SPEC.md
  UI_SPEC.md
```

## 环境变量

复制 `.env.example` 后按需调整：

```bash
cp .env.example .env
```

关键变量：

- `API_PORT`: 后端容器和宿主机端口，默认 `8000`
- `WEB_PORT`: 前端容器和宿主机端口，默认 `3000`
- `CORS_ORIGINS`: 允许访问 API 的前端 origin，默认 `http://localhost:3000`
- `NEXT_PUBLIC_API_BASE_URL`: 浏览器端调用 API 的 base URL
- `SERVER_API_BASE_URL`: Next.js 服务端渲染调用 API 的 base URL

Docker Compose 内部会把 `SERVER_API_BASE_URL` 设置为 `http://api:8000`，浏览器端仍通过 `NEXT_PUBLIC_API_BASE_URL` 访问宿主机暴露的 API。

## 启动

```bash
docker compose up --build
```

或使用 Makefile：

```bash
make dev
```

启动后访问：

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`

`GET /health` 应返回：

```json
{"status":"ok"}
```

## 验收路径

1. 打开 `http://localhost:3000` 查看 Dashboard。
2. 进入 `/products`，确认 AKK 产物列表来自 `GET /akk-products`。
3. 从产品列表进入 `/products/[id]`。
4. 点击 `Generate Formula` 进入 `/formula/new`。
5. 完成分步骤表单，前端调用 `POST /formula/generate`。
6. 页面跳转到 `/formula/results/[id]`。
7. 结果页展示 `research_use_only`、推荐份额配比、预测结果、置信度、风险提示和实验建议。

## 前端页面

- `/`: Dashboard，展示产品数量、生成配方数量、待验证方案、中高风险方案、最近结果和应用方向。
- `/products`: AKK 产品库，展示产品形态、主要功能、应用适配性、证据等级和风险等级。
- `/products/[id]`: AKK 产品详情，展示基础信息、功能性质、应用适配、稳定性、安全合规说明、证据等级和风险等级。
- `/formula/new`: 分步骤配方生成表单。
- `/formula/results`: 配方结果列表。
- `/formula/results/[id]`: 配方结果详情，展示配比、预测、置信度、风险、验证测试、工艺建议和选中产品摘要。

## 测试和检查

后端测试在容器内运行：

```bash
docker compose exec api pytest tests
```

Makefile 等价命令：

```bash
make test-api
```

前端类型检查：

```bash
docker compose exec web npm run lint
make lint-web
```

前端构建：

```bash
docker compose exec web npm run build
make build-web
```

全部检查：

```bash
make check
```

## 后端测试覆盖

- `GET /health`
- `GET /akk-products`
- `GET /akk-products/{product_id}`
- `POST /formula/generate`
- `GET /formula-results/{result_id}`
- `GET /formula-results`

## 后端分层

- `routers`: 只负责 HTTP 入参和出参
- `schemas`: 定义 Pydantic request / response model
- `services`: 负责配方生成、预测结果组装、风险提示等业务逻辑
- `repositories`: 负责读取 mock JSON，未来可替换为数据库

API router 不直接读取 mock JSON。

## 排错

- 如果前端页面请求失败，先确认 `NEXT_PUBLIC_API_BASE_URL` 指向宿主机可访问的 API，例如 `http://localhost:8000`。
- 如果服务端渲染请求失败，确认 Docker Compose 中 `SERVER_API_BASE_URL=http://api:8000`。
- 如果浏览器 CORS 报错，确认 `CORS_ORIGINS` 包含当前前端地址。
- 如果 `docker compose exec` 失败，先确认 `docker compose up --build` 已启动服务。
- 如果依赖安装失败，检查 Docker 网络是否可访问 PyPI 和 npm registry。

## 第一版限制

- 使用 mock JSON 数据。
- 不接真实数据库。
- 不接真实大模型。
- 不接真实文献知识库。
- 不接真实配方引擎或预测模型。
- 不做登录系统。
