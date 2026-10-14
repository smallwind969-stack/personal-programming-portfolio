import json
import os
from tempfile import TemporaryDirectory

import pytest

from case_registry import CaseLookupError, resolve_case


def _catalog(temp_dir, entries):
    path = os.path.join(temp_dir, "catalog.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle)
    return path


def test_resolves_allowlisted_case_beneath_root():
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        root = os.path.join(temp_dir, "dicom")
        case_dir = os.path.join(root, "demo", "case-001")
        os.makedirs(case_dir)
        catalog = _catalog(temp_dir, {"case-001": "demo/case-001"})

        assert resolve_case("case-001", root, catalog) == os.path.realpath(case_dir)


@pytest.mark.parametrize("case_id", ["../case", "C:\\CT", "", "a/b", "a\\b"])
def test_rejects_path_like_case_ids(case_id):
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        catalog = _catalog(temp_dir, {})
        with pytest.raises(CaseLookupError):
            resolve_case(case_id, temp_dir, catalog)


@pytest.mark.parametrize("entry", ["../outside", "C:\\outside", "/outside", "a/../b"])
def test_rejects_non_relative_or_traversing_catalog_entries(entry):
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        root = os.path.join(temp_dir, "dicom")
        os.makedirs(root)
        catalog = _catalog(temp_dir, {"case-001": entry})
        with pytest.raises(CaseLookupError):
            resolve_case("case-001", root, catalog)


def test_rejects_unknown_or_missing_cases():
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        root = os.path.join(temp_dir, "dicom")
        os.makedirs(root)
        catalog = _catalog(temp_dir, {"case-001": "missing"})

        with pytest.raises(CaseLookupError):
            resolve_case("other", root, catalog)
        with pytest.raises(CaseLookupError):
            resolve_case("case-001", root, catalog)


def test_rejects_malformed_catalog():
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        catalog = _catalog(temp_dir, ["not", "a", "mapping"])
        with pytest.raises(CaseLookupError):
            resolve_case("case-001", temp_dir, catalog)


def test_rejects_catalog_symlink_that_escapes_root():
    with TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        root = os.path.join(temp_dir, "dicom")
        outside = os.path.join(temp_dir, "outside")
        os.makedirs(root)
        os.makedirs(outside)
        link = os.path.join(root, "linked")
        try:
            os.symlink(outside, link, target_is_directory=True)
        except OSError:
            pytest.skip("当前 Windows 权限不允许创建测试用目录符号链接")
        catalog = _catalog(temp_dir, {"case-001": "linked"})
        with pytest.raises(CaseLookupError):
            resolve_case("case-001", root, catalog)
