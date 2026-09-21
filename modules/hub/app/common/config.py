from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerDefaults(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    GLOBAL_TIMEOUT_SECONDS: int = Field(300, description="Default global timeout for scheduled tasks in seconds")
    GLOBAL_TIMEOUT_BUFFER: int = Field(
        30,
        description="Buffer time to subtract from the global timeout to ensure tasks complete within limits in seconds",
    )
    MAX_CONCURRENT_TASKS: int = Field(10, description="Maximum number of concurrent tasks that can be scheduled")
    MAX_RETRY_ATTEMPTS: int = Field(3, description="Maximum number of retry attempts for failed tasks")
    MAX_DISPATCH_LIMIT: int = Field(
        200, description="Maximum number of schedules or retry jobs to fetch in a single tick"
    )

    @property
    def effective_timeout(self) -> int:
        """Calculate the effective timeout by subtracting the buffer from the global timeout."""
        if self.GLOBAL_TIMEOUT_BUFFER >= self.GLOBAL_TIMEOUT_SECONDS:
            raise ValueError("GLOBAL_TIMEOUT_BUFFER must be less than GLOBAL_TIMEOUT_SECONDS")
        return self.GLOBAL_TIMEOUT_SECONDS - self.GLOBAL_TIMEOUT_BUFFER


class SchedulerAuthConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SCHEDULER_KEY: SecretStr | None = Field(
        default=None,
        description="Random key the external scheduler sends as X-Scheduler-Key. It opens the dispatcher trigger "
        "only. Unset: only a signed-in user can trigger a tick",
    )


class GitHubWebhookConfig(BaseSettings):
    """Deployment-owned secret shared with GitHub's webhook configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    GITHUB_WEBHOOK_SECRET: SecretStr | None = Field(
        default=None, description="GitHub webhook HMAC secret; webhook delivery is disabled when unset"
    )


@lru_cache
def get_scheduler_defaults() -> SchedulerDefaults:
    """Get an instance of SchedulerDefaults with values loaded from environment variables or defaults."""
    return SchedulerDefaults(**{})


@lru_cache
def get_scheduler_auth_config() -> SchedulerAuthConfig:
    return SchedulerAuthConfig(**{})


@lru_cache
def get_github_webhook_config() -> GitHubWebhookConfig:
    return GitHubWebhookConfig(**{})
