# 部署 Nexent 智能体平台

Nexent 是华为开源的零代码智能体自动生成平台（ModelEngine 生态）。
官网 https://nexent.tech ｜ 仓库 https://github.com/ModelEngine-Group/nexent （MIT 协议）。

## 前置
- 已安装 Docker 24+ 与 Docker Compose v2+（见 `install-docker.md`）。
- 满足硬件要求（4 核 / 8 GB 内存 / 40 GB 磁盘）。

## 部署步骤

在 Git Bash 或 WSL 中执行：

```bash
# 1) 克隆仓库
git clone https://github.com/ModelEngine-Group/nexent.git

# 2) 进入目录
cd nexent

# 3) 一键部署（Docker）
bash deploy.sh docker
```

部署脚本会进入交互式向导，按提示选择：

- **版本**：个人/小团队选 `Speed version`（默认，回车即可）。
- **部署模式**：调试选「开发模式」（暴露所有服务端口）。
- **可选组件**：终端工具按需（本机可 `N`）；**区域优化/中国镜像源选 `Y`**（加速拉取镜像）。

> 更早版本的 README 曾使用 `cd nexent/docker && cp .env.example .env && bash deploy.sh`；
> 当前主分支统一为根目录 `bash deploy.sh docker`。以克隆下来的仓库内 `README_CN.md` 为准。

## 访问
部署完成后浏览器打开：

```
http://localhost:3000
```

启动的容器包括 `nexent-web`、`nexent-config`、`nexent-mcp`、`nexent-runtime` 以及 PostgreSQL、Redis、Elasticsearch、MinIO 等基础设施。

## 卸载
```bash
bash uninstall.sh docker
```
