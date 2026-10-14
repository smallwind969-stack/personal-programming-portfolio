"""大模型 API 配置。

使用方法：
在启动程序前通过环境变量 ``FJJ_LLM_API_KEY`` 提供密钥，避免把密钥
写进源码或提交到公共仓库。
"""

import os

API_BASE = "https://ai.rjyunk.com/v1"
MODEL = "gpt-5.3-codex-spark"
API_KEY = os.getenv("FJJ_LLM_API_KEY", "")
TIMEOUT = 60
TEMPERATURE = 0.2
