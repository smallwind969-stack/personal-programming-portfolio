# STEP094：优化结果血缘检查

## 目标

演示链路不能只验证页面返回 200 或运行状态为 completed，还要验证优化结果确实来源于已完成的仿真运行，并生成参数版本和预测结果版本。

## 检查增强

`scripts/check-demo-flow.ps1` 现在额外验证：

- `officialParameterVersion` 存在；
- `newResultVersion` 存在；
- `baseSimulationRunId` 与已完成仿真运行 ID 一致；
- 优化结果摘要存在。

## 实测结果

- 仿真运行：`simulation-run-2f57891358`；
- 工艺参数版本：`demo-process-parameters-v1-f3eae9`；
- 预测结果版本：`demo-predicted-result-v1-51e0b8`；
- 检查脚本：通过。

这保证演示界面中的优化版本不是孤立生成的字符串，而是能回溯到父模型、仿真结果和当前实验。
