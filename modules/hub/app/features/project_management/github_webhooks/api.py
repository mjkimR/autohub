from typing import Annotated

from app.common.config import get_github_webhook_config
from app.features.execution.dispatchers.usecases.housekeeping import TickHousekeepingUseCase
from app.features.project_management.github_webhooks import tasks
from app.features.project_management.github_webhooks.repos import GitHubWebhookRepository
from app.features.project_management.github_webhooks.usecases import GitHubWebhookUseCase
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

router = APIRouter(prefix="/github/webhooks", tags=["GitHub Webhook"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    lifecycle: Annotated[PipelineRunUseCase, Depends()],
    housekeeping: Annotated[TickHousekeepingUseCase, Depends()],
    x_github_delivery: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
):
    config = get_github_webhook_config()
    secret = config.GITHUB_WEBHOOK_SECRET
    if secret is None:
        raise HTTPException(status_code=503, detail="GitHub webhooks are not configured")
    if not x_github_delivery or not x_github_event:
        raise HTTPException(status_code=400, detail="Missing GitHub delivery headers")
    raw_body = await request.body()
    use_case = GitHubWebhookUseCase(GitHubWebhookRepository(), PipelineRunRepository(), lifecycle)
    if not use_case.verify_signature(secret.get_secret_value(), raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload")
    if not await use_case.receive(x_github_delivery, x_github_event, raw_body, payload):
        return {"status": "duplicate"}
    # A queued task processes the delivery in a request of its own, where Cloud Run allocates CPU.
    if not await tasks.enqueue(config, x_github_delivery):
        background_tasks.add_task(use_case.process, x_github_delivery, payload, x_github_event)
    # Webhooks keep arriving when the scheduler trigger has stopped, which nothing else would notice.
    background_tasks.add_task(housekeeping.report_stopped_trigger)
    return {"status": "accepted"}


@router.post("/deliveries/{delivery_id}/process", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def process_queued_delivery(
    delivery_id: str,
    lifecycle: Annotated[PipelineRunUseCase, Depends()],
    x_autohub_task_expires: Annotated[str | None, Header()] = None,
    x_autohub_task_signature: Annotated[str | None, Header()] = None,
):
    """Cloud Tasks callback. Failures are recorded on the delivery and replayed by the tick, so it always succeeds."""
    secret = get_github_webhook_config().GITHUB_WEBHOOK_SECRET
    if secret is None or not tasks.verify(
        secret.get_secret_value(), delivery_id, x_autohub_task_expires, x_autohub_task_signature
    ):
        raise HTTPException(status_code=401, detail="Invalid task signature")
    await GitHubWebhookUseCase(GitHubWebhookRepository(), PipelineRunRepository(), lifecycle).process_queued(
        delivery_id
    )
