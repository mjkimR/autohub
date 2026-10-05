from pathlib import Path
from unittest.mock import patch

from app.main import create_app
from starlette.testclient import TestClient


def test_openapi_independent_of_ui_build(tmp_path: Path):
    (tmp_path / "index.html").write_text("<!DOCTYPE html><html><body>Test SPA</body></html>")
    with patch.dict("os.environ", {"UI_DIST_PATH": str(tmp_path)}):
        with_ui = create_app().openapi()
    with patch.dict("os.environ", {"UI_DIST_PATH": str(tmp_path / "missing")}):
        without_ui = create_app().openapi()

    assert with_ui == without_ui
    assert "/" not in with_ui["paths"]
    assert "/{full_path:path}" not in with_ui["paths"]
    assert with_ui["paths"]["/api/health"]["get"]["tags"] == ["health"]


def test_root_redirect_when_no_ui(tmp_path: Path):
    with patch.dict("os.environ", {"UI_DIST_PATH": str(tmp_path / "non_existent")}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/docs"


def test_spa_served_when_ui_present(tmp_path: Path):
    index_file = tmp_path / "index.html"
    index_file.write_text("<!DOCTYPE html><html><body>Test SPA</body></html>")
    app_dir = tmp_path / "_app"
    app_dir.mkdir()
    asset_file = app_dir / "style.css"
    asset_file.write_text("body { color: red; }")

    with patch.dict("os.environ", {"UI_DIST_PATH": str(tmp_path)}):
        app = create_app()
        client = TestClient(app)

        # Root returns index.html
        root_res = client.get("/")
        assert root_res.status_code == 200
        assert "Test SPA" in root_res.text

        # The MCP endpoint stays protected ahead of the SPA catch-all, with either spelling.
        for endpoint in ("/mcp", "/mcp/", "/ops/mcp", "/ops/mcp/"):
            mcp_res = client.post(endpoint, json={})
            assert mcp_res.status_code == 401
            assert mcp_res.headers["content-type"].startswith("application/json")

        # Well-known discovery paths are not served by the SPA fallback.
        well_known_res = client.get("/.well-known/oauth-protected-resource")
        assert well_known_res.status_code == 404
        assert well_known_res.headers["content-type"].startswith("application/json")

        # Client-side route fallback returns index.html
        route_res = client.get("/projects/runs")
        assert route_res.status_code == 200
        assert "Test SPA" in route_res.text

        # Static asset returns asset content
        asset_res = client.get("/_app/style.css")
        assert asset_res.status_code == 200
        assert "color: red" in asset_res.text
