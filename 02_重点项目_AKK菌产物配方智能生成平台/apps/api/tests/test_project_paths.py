from pathlib import Path

from app.paths import project_path


def test_project_path_is_independent_of_process_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    resolved = project_path("data/decision/knowledge-v1.json")

    assert resolved.is_absolute()
    assert resolved.name == "knowledge-v1.json"
    assert resolved.parts[-3:] == ("data", "decision", "knowledge-v1.json")
    assert resolved.exists()


def test_project_path_preserves_explicit_absolute_path(tmp_path):
    explicit = tmp_path / "runtime.db"

    assert project_path(explicit) == explicit
