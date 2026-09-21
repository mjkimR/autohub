import httpx

TELEGRAM_API_BASE_URL = "https://api.telegram.org"
# Telegram rejects a longer message outright; a cut notice still reaches the operator.
TELEGRAM_MESSAGE_LIMIT = 4096


class TelegramError(Exception):
    pass


def create_telegram_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=TELEGRAM_API_BASE_URL, timeout=10)


async def send_telegram_message(client: httpx.AsyncClient, bot_token: str, chat_id: str, text: str) -> None:
    """Post one plain-text message. The error never carries the URL, which holds the bot token."""
    try:
        response = await client.post(
            f"/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:TELEGRAM_MESSAGE_LIMIT], "disable_web_page_preview": True},
        )
    except httpx.RequestError:
        raise TelegramError("Telegram request failed") from None
    if response.status_code != 200:
        description = None
        try:
            body = response.json()
            description = body.get("description") if isinstance(body, dict) else None
        except ValueError:
            pass
        detail = f": {description}" if isinstance(description, str) else ""
        raise TelegramError(f"Telegram returned HTTP {response.status_code}{detail}")
