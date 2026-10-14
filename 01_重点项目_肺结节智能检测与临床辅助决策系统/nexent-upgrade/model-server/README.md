# 模型推理服务（model-server）

把原 FJJ System 的 `DiagnosisEngine`（VNet 检测 + ResNet 精筛 + DualBranch 良恶性分类）封装为无前端的 FastAPI 微服务，供 Nexent 的 MCP 工具调用。

## 目录

- `app.py` —— FastAPI 服务入口，`/health`、`/detect`、`/identify`、只读 `/runs/{case_id}/{run_id}`
- `engine.py` —— 从原项目复用的诊断引擎
- `models.py` —— 从原项目复用的模型定义（AttentionVNet_v6_7 / ResNet18_3D_CBAM / DualBranchResNet）
- `requirements.txt` —— 依赖

## 权重

默认复用 `../../FJJ System/models/` 下的三个 `.pth`，也可用环境变量覆盖：

| 环境变量 | 默认权重 |
|---|---|
| `VNET_W` | vnet_v6_7_sprint_recall_0.9648_epoch_41.pth |
| `RESNET_W` | fpr_v7_best_rec_0.9612.pth |
| `MALIG_W` | GOLDEN_Ep58_A0.923.pth |

## 启动

先把一例**脱敏演示影像**放到本机专用目录；病例清单只登记该目录下的相对路径。`case_catalog.example.json` 是格式示例，不能代替实际影像，也不能放患者姓名或身份证号。

```powershell
python -m pip install -r requirements.txt
$env:DICOM_ROOT = 'D:\demo-dicom'
$env:CASE_CATALOG_JSON = 'D:\demo-config\case_catalog.json'
$env:MODEL_SERVER_TOKEN = '<本机随机长令牌>'
python app.py
```

默认只监听 `127.0.0.1:8100`；如与 Nexent 分容器，需明确配置容器网络和访问控制。模型权重在**首次推理**时加载，`/health` 成功不代表已完成真实影像推理。三个检测阈值/参数由服务端控制，智能体无权修改。

## 接口

### GET /health
返回设备（CPU/CUDA）与权重信息。

### POST /detect
```json
{"case_id": "demo-001"}
```
请求头须含 `Authorization: Bearer <MODEL_SERVER_TOKEN>`。返回 `case_id`、`run_id`、待复核候选 `findings`（含 `candidate_id`、`review_status: pending`）与耗时。路径、患者身份和原始影像不会进入 MCP 参数。

### POST /identify
```json
{"case_id": "demo-001", "run_id": "检测接口返回的批次 ID", "candidate_ids": ["c001"]}
```
只接受当前批次已有候选，返回 `model_score` 和 `review_status: pending`。`model_score` 尚未做临床概率校准，不能写成“恶性概率”或诊断结论。医生确认应在独立复核流程中完成。

### GET /runs/{case_id}/{run_id}

请求头同样须含模型服务令牌。只读取当前进程中该病例的**有效批次**，返回服务端缓存的候选编号、检测评分、已完成的分类评分与 `review_status: pending`；未分类时没有 `model_score`。新一轮检测会使旧批次失效。这个接口用于医生工作台核验 Agent 所称的运行结果，不接受智能体提交的候选内容，也不产生医生确认。病例 ID 必须在白名单中。

当前候选缓存保存在单个服务进程内，重启后失效；此阶段面向本机单人演示，不适合作为多进程或正式临床部署。
