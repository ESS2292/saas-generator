import pytest

from engine.file_writer import GeneratedProjectError, save_project_files


def test_save_project_rejects_missing_required_files(tmp_path):
    files = [("backend/main.py", 'print("hello")\n')]

    with pytest.raises(GeneratedProjectError, match="missing required files"):
        save_project_files(files, app_root=str(tmp_path))


def test_save_project_rejects_path_traversal(tmp_path):
    files = [
        ("backend/main.py", 'print("ok")\n'),
        ("frontend/package.json", '{"name": "demo"}\n'),
        ("../../main.py", 'print("escape")\n'),
    ]

    with pytest.raises(GeneratedProjectError, match="Unsafe output path rejected|escapes project root"):
        save_project_files(files, app_root=str(tmp_path))


def test_save_project_writes_expected_files(tmp_path):
    files = [
        ("backend/main.py", "from fastapi import FastAPI\napp = FastAPI()\n"),
        ("frontend/package.json", '{"name": "demo"}\n'),
    ]

    saved_files = save_project_files(files, app_root=str(tmp_path))

    assert saved_files == ["backend/main.py", "frontend/package.json"]
    assert (tmp_path / "backend" / "main.py").exists()
    assert (tmp_path / "frontend" / "package.json").exists()
