import argparse
import csv
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path


ZENODO_RECORD = "https://zenodo.org/api/records/3723295"
ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "luna16"
DOC_ROOT = ROOT / "docs" / "world_frontier" / "luna16"


SMALL_DEFAULT_FILES = {"annotations.csv", "sampleSubmission.csv"}
OPTIONAL_MEDIUM_FILES = {"candidates_V2.zip", "evaluationScript.zip"}


def fetch_record():
    with urllib.request.urlopen(ZENODO_RECORD, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def file_manifest(record):
    rows = []
    for item in record.get("files", []):
        key = item["key"]
        rows.append({
            "key": key,
            "size": int(item.get("size", 0)),
            "download_url": item.get("links", {}).get("self", ""),
            "checksum": item.get("checksum", ""),
            "default_download": key in SMALL_DEFAULT_FILES,
            "optional_medium": key in OPTIONAL_MEDIUM_FILES,
            "large_image_subset": key.startswith("subset") and key.endswith(".zip"),
        })
    return sorted(rows, key=lambda row: row["key"])


def write_manifest(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "key",
                "size",
                "download_url",
                "checksum",
                "default_download",
                "optional_medium",
                "large_image_subset",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def md5(path):
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(row, out_dir, overwrite=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / row["key"]
    if dest.exists() and not overwrite:
        return dest
    with urllib.request.urlopen(row["download_url"], timeout=120) as resp, dest.open("wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return dest


def partial_download_path(dest):
    return dest.with_name(dest.name + ".part")


def build_download_request(url, partial_path, overwrite=False):
    start = 0
    if partial_path.exists() and not overwrite:
        start = partial_path.stat().st_size
    headers = {"Range": f"bytes={start}-"} if start else {}
    return urllib.request.Request(url, headers=headers), start


def validate_download_size(path, expected_size):
    if expected_size and Path(path).stat().st_size != int(expected_size):
        raise RuntimeError(
            f"Incomplete download for {path}: observed={Path(path).stat().st_size} expected={expected_size}"
        )


def download_file_resumable(row, out_dir, overwrite=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / row["key"]
    if dest.exists() and not overwrite:
        return dest
    part = partial_download_path(dest)
    if overwrite:
        if dest.exists():
            dest.unlink()
        if part.exists():
            part.unlink()
    request, start = build_download_request(row["download_url"], part, overwrite=overwrite)
    with urllib.request.urlopen(request, timeout=120) as resp:
        if start and getattr(resp, "status", resp.getcode()) != 206:
            start = 0
            part.unlink(missing_ok=True)
        mode = "ab" if start else "wb"
        with part.open(mode + "") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    validate_download_size(part, row.get("size", 0))
    part.replace(dest)
    return dest


def ensure_free_space(out_dir, required_bytes, reserve_bytes):
    out_dir.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(out_dir).free
    needed = required_bytes + reserve_bytes
    if free < needed:
        raise RuntimeError(
            f"Not enough disk space. free={free} bytes, required={required_bytes}, reserve={reserve_bytes}"
        )
    return free


def verify_checksum(path, checksum):
    if not checksum:
        return {"checked": False, "passed": None, "reason": "missing checksum"}
    algo, _, expected = checksum.partition(":")
    if algo.lower() != "md5":
        return {"checked": False, "passed": None, "reason": f"unsupported checksum {algo}"}
    observed = md5(path)
    return {"checked": True, "passed": observed == expected, "expected": expected, "observed": observed}


def validate_annotations(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    required = {"seriesuid", "coordX", "coordY", "coordZ", "diameter_mm"}
    missing = sorted(required - set(reader.fieldnames or []))
    series = {row["seriesuid"] for row in rows if row.get("seriesuid")}
    return {
        "row_count": len(rows),
        "series_count": len(series),
        "missing_columns": missing,
        "valid": not missing and len(rows) > 0,
    }


def validate_sample_submission(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    required = {"seriesuid", "coordX", "coordY", "coordZ", "probability"}
    missing = sorted(required - set(reader.fieldnames or []))
    return {"row_count": len(rows), "missing_columns": missing, "valid": not missing}


def maybe_extract(zip_path, extract_dir):
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
        return zf.namelist()


def maybe_extract_with_space_check(zip_path, extract_dir, reserve_bytes):
    with zipfile.ZipFile(zip_path) as zf:
        required = sum(info.file_size for info in zf.infolist())
    ensure_free_space(extract_dir.parent, required, reserve_bytes)
    return maybe_extract(zip_path, extract_dir)


def main():
    parser = argparse.ArgumentParser(description="Initialize LUNA16 metadata and manifest files.")
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--download-medium", action="store_true", help="Also download candidates_V2.zip and evaluationScript.zip.")
    parser.add_argument("--extract-medium", action="store_true")
    parser.add_argument("--download-subset", action="append", type=int, choices=range(10), metavar="N")
    parser.add_argument("--extract-subset", action="store_true")
    parser.add_argument("--delete-zip-after-extract", action="store_true")
    parser.add_argument("--resume-download", action="store_true", help="Download via .part files and HTTP Range resume.")
    parser.add_argument("--reserve-gb", type=float, default=5.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    record = fetch_record()
    rows = file_manifest(record)
    write_manifest(rows, DOC_ROOT / "zenodo_luna16_manifest.csv")

    selected = set(SMALL_DEFAULT_FILES)
    if args.download_medium:
        selected |= OPTIONAL_MEDIUM_FILES
    if args.download_subset:
        selected |= {f"subset{idx}.zip" for idx in args.download_subset}

    report = {
        "record": ZENODO_RECORD,
        "title": record.get("title"),
        "data_root": str(data_root),
        "downloaded": [],
        "skipped_large_subsets": [row["key"] for row in rows if row["large_image_subset"]],
    }

    for row in rows:
        if row["key"] not in selected:
            continue
        if row["large_image_subset"]:
            ensure_free_space(data_root, row["size"], int(args.reserve_gb * 1024 ** 3))
        if args.resume_download:
            path = download_file_resumable(row, data_root, overwrite=args.overwrite)
        else:
            path = download_file(row, data_root, overwrite=args.overwrite)
        item_report = {
            "key": row["key"],
            "path": str(path),
            "size": path.stat().st_size,
            "checksum": verify_checksum(path, row["checksum"]),
        }
        if row["key"] == "annotations.csv":
            item_report["validation"] = validate_annotations(path)
        elif row["key"] == "sampleSubmission.csv":
            item_report["validation"] = validate_sample_submission(path)
        elif args.extract_medium and row["key"] in OPTIONAL_MEDIUM_FILES:
            item_report["extracted_files"] = maybe_extract(path, data_root / row["key"].replace(".zip", ""))
        elif args.extract_subset and row["large_image_subset"]:
            item_report["extracted_files"] = maybe_extract_with_space_check(
                path,
                data_root / row["key"].replace(".zip", ""),
                int(args.reserve_gb * 1024 ** 3),
            )
            if args.delete_zip_after_extract:
                path.unlink()
                item_report["deleted_zip_after_extract"] = True
        report["downloaded"].append(item_report)

    report_path = DOC_ROOT / "luna16_data_init_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
