# STEP117：版本化报告数据包导出

实验报告现在提供两种交付格式：Markdown 用于阅读与论文整理，JSON 用于企业归档、二次分析和后续系统对接。JSON 导出保留报告版本、输入指纹、来源版本、分层陈述、证据引用、待确认事项和审核状态，不绕过人工审核。

接口：`GET /experiments/{experiment_id}/research-reports/{report_id}/json`

