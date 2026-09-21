from app_layer_base.base.exceptions.base import Actor, CustomException, Retry


class ProjectError(CustomException):
    def __init__(
        self,
        status: int,
        detail: str,
        *,
        actor: Actor | None = None,
        retry: Retry | None = None,
        code: str = "PROJECT_ERROR",
        fix: str | None = None,
    ):
        self.status = status
        self.detail = detail
        super().__init__(
            message=detail,
            status_code=status,
            title="Project Error",
            code=code,
            actor=actor or (Actor.USER if status < 500 else Actor.DEVELOPER),
            retry=retry or (Retry.UNSAFE if status in (404, 422) else Retry.SAFE),
            fix=fix,
        )
