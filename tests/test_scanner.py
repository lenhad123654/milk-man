import sys
from pathlib import Path
from discover import scanner
from milk_man import work_path


def test_find_target_file_ignores_virtualenvs(tmp_path, monkeypatch):
    monkeypatch.setattr(work_path, "path", str(tmp_path))

    # Virtualenv file should be ignored
    venv_dir = tmp_path / ".venv" / "lib" / "site-packages"
    venv_dir.mkdir(parents=True)
    (venv_dir / "urls.py").write_text("# inside venv", encoding="utf-8")

    # Project file outside venv
    proj_dir = tmp_path / "myapp"
    proj_dir.mkdir()
    real_urls = proj_dir / "urls.py"
    real_urls.write_text("# real urls", encoding="utf-8")

    found = scanner._find_target_file("urls.py")
    assert found == real_urls


def test_flask_scan_handles_list_args(tmp_path, monkeypatch):
    monkeypatch.setattr(work_path, "path", str(tmp_path))

    app_py = tmp_path / "app.py"
    app_py.write_text(
        "from flask import Flask\napp = Flask(__name__)\n@app.route('/hello')\ndef h(): pass\n",
        encoding="utf-8",
    )

    # Calling flask_scan with a list argument as passed by commands dispatcher: ['app.py']
    result = scanner.flask_scan(["app.py"])
    assert result == ["/hello"]


def test_fastapi_scan_handles_list_args(tmp_path, monkeypatch):
    monkeypatch.setattr(work_path, "path", str(tmp_path))

    main_py = tmp_path / "main.py"
    main_py.write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/items')\ndef it(): pass\n",
        encoding="utf-8",
    )

    result = scanner.fastapi_scan(["main.py"])
    assert result == [{"route": "/items", "method": "GET"}]
