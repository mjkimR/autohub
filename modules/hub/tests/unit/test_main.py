from pathlib import Path
from unittest.mock import patch

from app.main import _resolve_ui_dist


def test_resolve_ui_dist_none(tmp_path: Path):
    with patch.dict("os.environ", {"UI_DIST_PATH": str(tmp_path / "non_existent")}):
        assert _resolve_ui_dist() is None


def test_resolve_ui_dist_custom(tmp_path: Path):
    index_file = tmp_path / "index.html"
    index_file.write_text("<!DOCTYPE html><html><body>Test SPA</body></html>")

    with patch.dict("os.environ", {"UI_DIST_PATH": str(tmp_path)}):
        resolved = _resolve_ui_dist()
        assert resolved == tmp_path
