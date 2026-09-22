"""Provision the scheduler through the M2M API; never print credentials.

Run after deployment. Secret Manager owns the one-time issued credential;
ordinary redeployment reuses it. Revoked/expired credentials require an explicit
operator rotation and are never silently replaced or reactivated.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect must never carry the deployment root credential to another endpoint.
        return None


def management_request(base: str, root: str, method: str, path: str, body: dict | None = None):
    request = Request(
        base.rstrip("/") + "/api/v1" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Root-API-Key": root, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Machine management API returned HTTP {exc.code}") from None


def provision(api, load, save, name: str) -> dict:
    def listing(path):
        offset = 0
        while True:
            page = api("GET", f"{path}?offset={offset}&limit=200")
            yield from page
            if len(page) < 200:
                return
            offset += len(page)

    saved = load()
    machine = next((m for m in listing("/machines") if m["name"] == name), None)
    if machine is None:
        if saved:
            raise RuntimeError("Stored scheduler credential has no machine; reconcile it explicitly")
        machine = api("POST", "/machines", {"name": name, "scopes": ["autohub:dispatch"]})
    if not machine["is_active"] or set(machine["scopes"]) != {"autohub:dispatch"}:
        raise RuntimeError("Scheduler machine is inactive or has unexpected scopes; refusing to change it")
    path = f"/machines/{machine['id']}/keys"
    keys = list(listing(path))
    if saved:
        key = next((k for k in keys if k["id"] == saved.get("key_id")), None)
        if (
            saved.get("machine_id") != machine["id"]
            or key is None
            or key["revoked_at"]
            or (key["expires_at"] and datetime.fromisoformat(key["expires_at"]) <= datetime.now(UTC))
        ):
            raise RuntimeError("Stored scheduler key is invalid, expired, or revoked; rotate it explicitly")
        if not isinstance(saved.get("key"), str) or not saved["key"].startswith(f"ak_{key['id'].replace('-', '')}_"):
            raise RuntimeError("Stored scheduler secret does not match its key ID")
        return saved
    if keys:
        raise RuntimeError(
            "Scheduler key history exists without a saved secret; reconcile orphaned keys and explicitly provision a replacement"
        )
    issued = api("POST", path, {"label": "cloud-scheduler"})
    credential = {"machine_id": machine["id"], "key_id": issued["id"], "key": issued["key"]}
    try:
        save(credential)
    except Exception:
        try:
            api("DELETE", f"{path}/{issued['id']}")
        except Exception:
            raise RuntimeError(f"Secret save and cleanup failed; revoke key {issued['id']} manually") from None
        raise RuntimeError("Could not save scheduler secret; the newly issued key was revoked") from None
    return credential


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=None, help="GCP project ID (default: gcloud config or GCP_PROJECT_ID)")
    parser.add_argument("--region", default=None, help="GCP region (default: us-west1 or GCP_REGION)")
    parser.add_argument("--service", default="autohub", help="Cloud Run service name (default: autohub)")
    parser.add_argument("--url", default=None, help="Cloud Run service URL (default: auto-detected from Cloud Run)")
    parser.add_argument("--schedule", default="* * * * *", help="Cloud Scheduler cron schedule (default: every minute)")
    args = parser.parse_args()

    project = args.project or os.environ.get("PROJECT_ID") or os.environ.get("GCP_PROJECT_ID")
    if not project:
        proc = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
        project = proc.stdout.strip() if proc.returncode == 0 else ""
    if not project:
        raise RuntimeError("--project is required or must be configured in gcloud/environment")
    args.project = project

    region = args.region or os.environ.get("REGION") or os.environ.get("GCP_REGION") or "us-west1"
    args.region = region

    def gcloud(*command: str, data: str | None = None) -> str:
        result = subprocess.run(
            ["gcloud", *command, f"--project={args.project}", "--quiet"], input=data, capture_output=True, text=True
        )
        if result.returncode:
            # gcloud errors may echo argv, which includes a scheduler header. Never forward them.
            raise RuntimeError(f"gcloud {command[0]} {command[1]} failed; inspect permissions and resource state")
        return result.stdout

    url = args.url
    if not url:
        url = gcloud(
            "run", "services", "describe", args.service, f"--region={args.region}", "--format=value(status.url)"
        ).strip()
        if not url:
            project_number = gcloud("projects", "describe", args.project, "--format=value(projectNumber)").strip()
            url = f"https://{args.service}-{project_number}.{args.region}.run.app"
    if not url.startswith("https://"):
        raise RuntimeError("A deployed HTTPS service URL is required")
    args.url = url

    bundle = json.loads(gcloud("secrets", "versions", "access", "latest", "--secret=autohub-secrets"))
    root = bundle.get("APP_API_KEY_ROOT_KEY")
    if not root:
        raise RuntimeError("The secret bundle needs APP_API_KEY_ROOT_KEY; run just setup-secrets and redeploy")

    def api(method: str, path: str, body: dict | None = None):
        return management_request(args.url, root, method, path, body)

    secret = f"{args.service}-scheduler-credential"
    resources = json.loads(gcloud("secrets", "list", f"--filter=name:{secret}", "--format=json"))
    exists = any(resource["name"].endswith("/" + secret) for resource in resources)

    def load():
        if not exists:
            return None
        return json.loads(gcloud("secrets", "versions", "access", "latest", f"--secret={secret}"))

    def save(value):
        if exists:
            gcloud("secrets", "versions", "add", secret, "--data-file=-", data=json.dumps(value))
        else:
            gcloud(
                "secrets", "create", secret, "--replication-policy=automatic", "--data-file=-", data=json.dumps(value)
            )

    credential = provision(api, load, save, f"{args.service}-scheduler")
    job = f"{args.service}-dispatcher-tick"
    jobs = json.loads(gcloud("scheduler", "jobs", "list", f"--location={args.region}", "--format=json"))
    updating = any(item["name"].endswith("/" + job) for item in jobs)
    headers = "--update-headers" if updating else "--headers"
    command = [
        "scheduler",
        "jobs",
        "update" if updating else "create",
        "http",
        job,
        f"--location={args.region}",
        f"--schedule={args.schedule}",
        "--http-method=POST",
        f"--uri={args.url.rstrip('/')}/api/v1/dispatchers/trigger",
        f"{headers}=X-API-Key={credential['key']}",
        "--time-zone=UTC",
        "--attempt-deadline=300s",
    ]
    if updating:
        command.append("--remove-headers=X-Scheduler-Key,X-Root-API-Key,Authorization")
    gcloud(*command)
    print(f"Scheduler configured with machine {credential['machine_id']}; credential saved in {secret}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Only our explicit, sanitized failures are displayed. Do not print transport/JSON exceptions.
        raise SystemExit(
            str(exc) if type(exc) is RuntimeError else "Scheduler provisioning failed; inspect deployment state"
        ) from None
