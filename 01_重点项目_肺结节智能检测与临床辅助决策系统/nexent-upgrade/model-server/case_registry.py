"""Resolve opaque case IDs to local DICOM directories through an explicit catalog."""

import json
import ntpath
import os
import re


CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class CaseLookupError(ValueError):
    """The requested case is absent or its configured path is unsafe."""


def resolve_case(case_id, root, catalog_path):
    if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
        raise CaseLookupError("无效的病例 ID")
    if not root or not catalog_path:
        raise CaseLookupError("病例目录尚未配置")

    try:
        with open(catalog_path, "r", encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaseLookupError("病例清单不可读取") from exc
    if not isinstance(catalog, dict):
        raise CaseLookupError("病例清单格式无效")

    relative = catalog.get(case_id)
    if not isinstance(relative, str) or not relative:
        raise CaseLookupError("病例 ID 不在授权清单中")
    if ntpath.isabs(relative) or os.path.isabs(relative) or ":" in relative:
        raise CaseLookupError("病例清单包含绝对路径")
    parts = re.split(r"[/\\]", relative)
    if any(part in ("", ".", "..") for part in parts):
        raise CaseLookupError("病例清单包含无效路径段")

    root_real = os.path.realpath(root)
    candidate_real = os.path.realpath(os.path.join(root_real, *parts))
    try:
        inside = os.path.normcase(os.path.commonpath((root_real, candidate_real))) == os.path.normcase(root_real)
    except ValueError:
        inside = False
    if not inside:
        raise CaseLookupError("病例路径超出授权目录")
    if not os.path.isdir(candidate_real):
        raise CaseLookupError("病例影像目录不存在")
    return candidate_real
