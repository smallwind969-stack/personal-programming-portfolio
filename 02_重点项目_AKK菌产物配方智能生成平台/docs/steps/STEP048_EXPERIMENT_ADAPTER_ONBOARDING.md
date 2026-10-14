# Step048：首次实验创建与设备适配接入

日期：2026-07-20

## 本步目标

解决“没有历史实验数据时如何第一次使用”的入口问题，并把 Step047 的企业设备适配资产真正接入实验数据分析流程。

## 已完成

- “新建实验”从页面 mock 改为真实 API 和 SQLite 持久化。
- 首次无数据也可创建实验，实验进入“待补充实验数据”状态。
- 创建信息包括：
  - 实验名称；
  - 批次；
  - 目标产品或实验对象；
  - 目标指标；
  - 实验目标。
- 可按企业、设备类型、版本选择设备适配包。
- 服务端重新验证适配包存在性与内容完整性，再将版本、包 ID、SHA-256 指纹锁定到实验血缘。
- 新实验自动进入数据分析页。
- 数据分析页新增“首次实验准备进程”：
  1. 设备规则锁定；
  2. 字段识别与单位换算；
  3. 人工确认。
- 无数据时明确显示四个等待节点，不启动虚构算法进程：
  - 原始数据接收；
  - 字段与单位识别；
  - 时间轴对齐；
  - 人工确认。
- 新建实验会立即出现在实验归档中，重启服务后仍可读取。
- 仿真模拟和工艺优化继续受阶段门禁限制。

## 接口与持久化

- 新增 `POST /experiments/workspaces`
- 新增 SQLite 表 `experiment_workspaces`
- 新增契约：
  - `ExperimentCreateRequest`
  - `ExperimentWorkspaceOverview.adapterPack`
  - `ExperimentWorkspaceOverview.targetProduct`
  - `ExperimentWorkspaceOverview.targetMetrics`

## 验证证据

- 新增领域/API 测试：`3 passed`
- 后端全量测试：`205 passed, 1 skipped`
- 前端 TypeScript：通过
- Next.js 生产构建：通过
- Worker 命令入口：通过
- Docker Compose 配置：通过
- `git diff --check`：通过，仅有 Windows 换行提醒
- 浏览器完整实测：
  - 填写无历史数据的新实验；
  - 调用真实 API 创建；
  - 自动跳转到新实验数据分析页；
  - 页面展示等待数据、字段单位识别和人工确认状态；
  - 返回归档后能看到新建实验。

## 运行地址

- 前端：`http://localhost:3001`
- 后端：`http://127.0.0.1:8000`

## 下一步

Step049 将文件上传与等待流程连接：上传首批 CSV/TXT 后自动启动数据收集定位智能体，应用锁定的适配包，生成逐字段转换证据，并在人工确认前禁止创建训练数据快照。
