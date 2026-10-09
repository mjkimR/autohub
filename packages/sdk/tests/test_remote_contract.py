import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from autohub_sdk import (
    ApprovalStep,
    AutoHubClient,
    AutoHubError,
    FlowManifest,
    FlowSpec,
    InputRef,
    LiteralValue,
    PipelineSpec,
    ReleaseSpec,
    TaskBinding,
    TaskRef,
    TaskStep,
)
from pydantic import ValidationError


def flow() -> FlowSpec:
    return FlowSpec(
        key="example.flow",
        title="Example",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        steps=(
            TaskStep(id="first", task=TaskRef(key="example.echo"), inputs={"value": InputRef(source="run")}),
            ApprovalStep(id="approval", revise_to="first", max_revisions=1),
            TaskStep(
                id="last", task=TaskRef(key="example.echo"), inputs={"value": InputRef(source="step", step_id="first")}
            ),
        ),
        result_step="last",
    )


def release() -> ReleaseSpec:
    return ReleaseSpec(
        manifest=FlowManifest(
            tasks=(
                PipelineSpec(
                    key="example.echo",
                    contract_version=1,
                    title="Echo",
                    description="",
                    input_schema={},
                    output_schema={},
                ),
            ),
            flows=(flow(),),
        ),
        bindings=(TaskBinding(task=TaskRef(key="example.echo"), executor="native", target="echo"),),
    )


@pytest.mark.parametrize("mutation", ["duplicate", "future", "bad-result", "bad-return"])
def test_invalid_flow_graph_is_rejected(mutation):
    data = flow().model_dump(mode="json")
    if mutation == "duplicate":
        data["steps"][2]["id"] = "first"
    elif mutation == "future":
        data["steps"][0]["inputs"]["value"] = {"kind": "ref", "source": "step", "step_id": "last"}
    elif mutation == "bad-result":
        data["result_step"] = "approval"
    else:
        data["steps"][1]["revise_to"] = "last"
    with pytest.raises(ValidationError):
        FlowSpec.model_validate(data)


@pytest.mark.parametrize("mutation", ["duplicate", "unknown-task", "missing-binding", "extra-binding"])
def test_release_catalog_and_bindings_are_consistent(mutation):
    data = release().model_dump(mode="json")
    if mutation == "duplicate":
        data["manifest"]["tasks"] *= 2
    elif mutation == "unknown-task":
        data["manifest"]["flows"][0]["steps"][0]["task"]["key"] = "example.unknown"
    elif mutation == "missing-binding":
        data["bindings"] = []
    else:
        data["bindings"] *= 2
    with pytest.raises(ValidationError):
        ReleaseSpec.model_validate(data)


def test_release_digest_ignores_object_key_order_and_preserves_content_changes():
    first = release()
    data = first.model_dump(mode="json")
    second = ReleaseSpec.model_validate(json.loads(json.dumps(data, sort_keys=True)))
    assert first.digest() == second.digest()
    data["bindings"][0]["target"] = "other"
    assert ReleaseSpec.model_validate(data).digest() != first.digest()


@pytest.mark.parametrize(
    "data",
    [
        {"source": "run", "step_id": "unexpected"},
        {"source": "step"},
    ],
)
def test_input_references_require_the_right_source_identity(data):
    with pytest.raises(ValidationError):
        InputRef.model_validate(data)


def test_json_payload_rejects_nan():
    instance = release().model_copy(update={"bindings": release().bindings})
    instance.manifest.tasks[0].input_schema["default"] = float("nan")
    with pytest.raises(ValueError):
        instance.digest()


@pytest.mark.parametrize("url", ["file:///tmp/test", "https://user:password@example.com", "http://example.com?q=1"])
def test_client_rejects_ambiguous_base_urls(url):
    with pytest.raises(ValueError):
        AutoHubClient(url)


def test_client_does_not_follow_redirect_or_retry_and_normalizes_non_json_errors():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.path, self.headers.get("X-API-Key")))
            if self.path.endswith("redirect"):
                self.send_response(302)
                self.send_header("Location", "/secret")
            elif self.path.endswith("structured"):
                self.send_response(409)
                self.send_header("Content-Type", "application/json")
            else:
                self.send_response(503)
            self.end_headers()
            if self.path.endswith("structured"):
                self.wfile.write(b'{"code":"stale-revision","message":"changed"}')
            else:
                self.wfile.write(b"not JSON")

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = AutoHubClient(f"http://127.0.0.1:{server.server_port}", api_key="test-only")
        for identity, status, code in [
            ("redirect", 302, "http-error"),
            ("structured", 409, "stale-revision"),
            ("unavailable", 503, "http-error"),
        ]:
            with pytest.raises(AutoHubError) as exc:
                client.get_run(identity)
            assert (exc.value.status, exc.value.code) == (status, code)
        assert len(calls) == 3
        assert all(token == "test-only" for _, token in calls)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_literal_and_step_constraints_are_validated():
    assert LiteralValue(value={"nested": [1, 2]}).value == {"nested": [1, 2]}
    with pytest.raises(ValidationError):
        TaskStep(id="first", task=TaskRef(key="example.echo"), inputs={}, max_attempts=True)
    with pytest.raises(ValidationError):
        ApprovalStep(id="approval", revise_to="first")
