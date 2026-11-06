import httpx
from app.features.notifications.telegram import TELEGRAM_API_BASE_URL


async def send_decision_message(client, token, chat_id, text):
    """Classify only a proven refusal; exceptions and ambiguous bodies remain unknown."""
    if not token or not chat_id:
        return "failed", "missing-destination"
    try:
        response = await client.post(
            f"{TELEGRAM_API_BASE_URL}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=10,
            follow_redirects=False,
        )
        body = response.json()
    except (httpx.RequestError, ValueError):
        return "unknown", "transport-unconfirmed"
    if response.status_code == 200 and isinstance(body, dict) and body.get("ok") is True:
        return "accepted", None
    if isinstance(body, dict) and body.get("ok") is False and 400 <= response.status_code < 500:
        return "failed", "telegram-refused"
    return "unknown", "transport-unconfirmed"
