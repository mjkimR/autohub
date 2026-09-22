class ProviderRequestError(RuntimeError):
    """Sanitized provider failure shared by provider clients and orchestration."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.quota_exhausted = status_code == 429
        self.definitive_rejection = status_code in (400, 401, 403, 404, 422, 429)
