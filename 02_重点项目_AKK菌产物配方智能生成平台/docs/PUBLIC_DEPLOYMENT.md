# 公网测试发布说明

目标：让组员不在同一个局域网，也能通过一个网址访问平台，类似 Vercel 项目体验。

推荐方案：

- 前端：Vercel
- 后端 API：Render
- 数据：当前仍使用项目内 mock JSON + SQLite 临时生成记录
- LLM：公网测试默认关闭本地 Ollama；如果需要公网 LLM，需要接云端模型或单独部署云端 Ollama

## 1. 上传到 GitHub

先把当前项目上传到一个 GitHub 仓库。

如果本地还没有 Git 仓库：

```powershell
git init
git add .
git commit -m "public test deployment"
git branch -M main
git remote add origin https://github.com/你的账号/你的仓库名.git
git push -u origin main
```

## 2. 部署后端到 Render

1. 打开 Render，新建 `Blueprint` 或 `Web Service`。
2. 连接 GitHub 仓库。
3. 如果使用 Blueprint，Render 会读取根目录的 `render.yaml`。
4. 如果手动创建 Web Service：
   - Runtime: Docker
   - Dockerfile Path: `./apps/api/Dockerfile`
   - Docker Context: `.`
   - Health Check Path: `/health`

后端环境变量建议：

```text
API_PORT=8000
PYTHONUNBUFFERED=1
LOCAL_LLM_ENABLED=false
CORS_ORIGIN_REGEX=^(https://[a-z0-9-]+\.vercel\.app|http://localhost:3000|http://127\.0\.0\.1:3000)$
```

部署完成后，你会得到类似地址：

```text
https://akk-formula-api.onrender.com
```

测试：

```text
https://akk-formula-api.onrender.com/health
```

应返回：

```json
{"status":"ok"}
```

## 3. 部署前端到 Vercel

1. 打开 Vercel，新建 Project。
2. 选择同一个 GitHub 仓库。
3. Project Root 选择：

```text
apps/web
```

4. Framework Preset 选择 Next.js。
5. 配置环境变量：

```text
NEXT_PUBLIC_API_BASE_URL=https://你的-render-api.onrender.com
SERVER_API_BASE_URL=https://你的-render-api.onrender.com
NEXT_TELEMETRY_DISABLED=1
```

6. 点击 Deploy。

部署完成后，你会得到类似地址：

```text
https://akk-formula-lab.vercel.app
```

这个地址就可以发给组员体验。

## 4. 公网测试版的体验路径

组员打开 Vercel 地址后：

1. 在首页输入目标商品类型，例如“牛奶”“低糖酸奶”“儿童软糖”“银发营养粉”。
2. 点击“智能推荐配方”。
3. 查看左侧 AKK 原料比例和右侧方案预览变化。
4. 点击“生成商品方案”。
5. 查看方案建议书。
6. 在“商品方案库”查看历史方案。
7. 在“实验平台”查看模拟实验数据。

## 5. 重要限制

公网测试版不是正式生产系统：

- Render 免费实例可能冷启动，第一次打开会慢一些。
- SQLite 文件在免费云环境中可能不是长期可靠持久化。
- 当前没有登录系统，拿到网址的人都可以访问。
- 默认关闭本地 Ollama，因为云端无法访问你电脑里的模型。
- 所有方案仍是研发实验建议，不是可直接上市配方。

## 6. 如果公网也要接 LLM

有三种升级方式：

1. 使用 OpenAI-compatible 云模型服务。
2. 买一台云服务器部署 Ollama，并让 API 的 `LOCAL_LLM_BASE_URL` 指向云服务器。
3. 把后端部署到有 GPU/大内存的服务器上，并在同一服务器运行 Ollama。

对应环境变量示例：

```text
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=openai_compatible
LOCAL_LLM_BASE_URL=https://你的模型服务/v1
LOCAL_LLM_MODEL=你的模型名
```

或云端 Ollama：

```text
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=ollama
LOCAL_LLM_BASE_URL=https://你的-ollama-api
LOCAL_LLM_MODEL=qwen2.5:7b
```
