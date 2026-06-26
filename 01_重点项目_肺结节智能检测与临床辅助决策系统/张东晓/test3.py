"""
@BelongsProject: AgentProject
@BelongsPackage: 
@Author: 蔡张君逸
@CreateTime: 2026-05-14 16:06
@Description: TODO
@Version: 1.
"""

import base64
from pathlib import Path

def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

path=Path("data/曾xx")

files = list(file for file in path.iterdir())
image_b64_total=[]
for file in files:
    print(file.__fspath__())
    # image_b64 = image_to_base64(file.as_uri())