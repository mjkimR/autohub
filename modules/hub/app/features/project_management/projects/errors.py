from app_layer_base.base.exceptions.base import Actor, CustomException, Retry

# Status-derived defaults let clients branch on the error kind without parsing messages.
STATUS_CODES = {
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "INVALID_REQUEST",
    501: "NOT_IMPLEMENTED",
    502: "UPSTREAM_ERROR",
    504: "UPSTREAM_TIMEOUT",
}


class ProjectError(CustomException):
    def __init__(
        self,
        status: int,
        detail: str,
        *,
        actor: Actor | None = None,
        retry: Retry | None = None,
        code: str | None = None,
        fix: str | None = None,
    ):
        self.status = status
        self.detail = detail
        super().__init__(
            message=detail,
            status_code=status,
            title="Project Error",
            code=code or STATUS_CODES.get(status, "PROJECT_ERROR"),
            actor=actor or (Actor.USER if status < 500 else Actor.DEVELOPER),
            retry=retry or (Retry.UNSAFE if status in (404, 422) else Retry.SAFE),
            fix=fix,
        )
