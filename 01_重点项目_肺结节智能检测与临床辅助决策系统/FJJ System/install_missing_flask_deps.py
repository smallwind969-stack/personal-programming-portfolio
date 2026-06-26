import json
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


PACKAGES = ["itsdangerous", "blinker", "flask", "flask-cors"]


def pick_wheel(package):
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        info = json.loads(resp.read().decode("utf-8"))

    version = info["info"]["version"]
    files = info["releases"][version]
    wheels = [
        item for item in files
        if item["filename"].endswith(".whl")
        and ("py3-none-any" in item["filename"] or "py2.py3-none-any" in item["filename"])
    ]
    if not wheels:
        raise RuntimeError(f"No pure Python wheel found for {package} {version}")
    return version, wheels[0]["url"]


def install_wheel(package, target):
    version, url = pick_wheel(package)
    print(f"Installing {package} {version}")
    with tempfile.NamedTemporaryFile(suffix=".whl", delete=False) as tmp:
        with urllib.request.urlopen(url, timeout=120) as resp:
            tmp.write(resp.read())
        wheel_path = Path(tmp.name)

    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(target)
    wheel_path.unlink(missing_ok=True)


def main():
    target = Path(__file__).resolve().parent / "vendor"
    target.mkdir(parents=True, exist_ok=True)
    print(f"Target: {target}")
    for package in PACKAGES:
        install_wheel(package, target)
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
