from app_prebuilt_auth.user.config import AuthSettings, get_auth_settings


def get_hub_auth_settings() -> AuthSettings:
    """AutoHub always requires approval for external registrations."""
    return get_auth_settings().model_copy(update={"REGISTRATION_REQUIRE_APPROVAL": True})
