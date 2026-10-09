"""Synchronous HTTP client without backend or additional runtime dependencies."""

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel

from .remote import (
    ActivationReceipt,
    ActivationRequest,
    ErrorResponse,
    ReleaseReceipt,
    ReleaseSpec,
    RunCommand,
    RunRequest,
    RunView,
)


class AutoHubError(Exception):
    def __init__(self, status: int, error: ErrorResponse):
        self.status = status
        self.code = error.code
        super().__init__(error.message)


class _NoRedirect(HTTPRedirectHandler):
    # Do not forward credentials to redirected hosts.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AutoHubClient:
    """Timeouts propagate. Callers explicitly reconcile/retry using stable IDs."""

    def __init__(self, base_url: str, *, api_key: str | None = None, timeout: float = 10):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.query or parsed.fragment:
            raise ValueError("base_url must be an HTTP(S) URL without query or fragment")
        if parsed.username or parsed.password or timeout <= 0:
            raise ValueError("URL credentials are forbidden and timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout
        self._opener = build_opener(_NoRedirect())

    def _request(self, method: str, path: str, body: BaseModel | None = None) -> Any:
        data = None if body is None else json.dumps(body.model_dump(mode="python"), allow_nan=False).encode()
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                error = ErrorResponse.model_validate(json.load(exc))
            except (ValueError, TypeError):
                error = ErrorResponse(code="http-error", message=f"Auto Hub returned HTTP {exc.code}")
            raise AutoHubError(exc.code, error) from exc

    @staticmethod
    def _release_path(provider: str, environment: str, release_id: str) -> str:
        parts = [quote(part, safe="") for part in (provider, environment, release_id)]
        return f"/api/v1/task-providers/{parts[0]}/environments/{parts[1]}/releases/{parts[2]}"

    def register_release(
        self, provider: str, environment: str, release_id: str, release: ReleaseSpec
    ) -> ReleaseReceipt:
        result = self._request("PUT", self._release_path(provider, environment, release_id), release)
        return ReleaseReceipt.model_validate(result)

    def activate_release(
        self, provider: str, environment: str, release_id: str, *, expected_revision: int
    ) -> ActivationReceipt:
        result = self._request(
            "POST",
            self._release_path(provider, environment, release_id) + "/activate",
            ActivationRequest(expected_revision=expected_revision),
        )
        return ActivationReceipt.model_validate(result)

    def start_run(self, request: RunRequest) -> RunView:
        return RunView.model_validate(self._request("POST", "/api/v1/task-runs", request))

    def get_run(self, run_id: str) -> RunView:
        return RunView.model_validate(self._request("GET", f"/api/v1/task-runs/{quote(run_id, safe='')}"))

    def command(self, run_id: str, command: RunCommand) -> RunView:
        result = self._request("POST", f"/api/v1/task-runs/{quote(run_id, safe='')}/commands", command)
        return RunView.model_validate(result)
