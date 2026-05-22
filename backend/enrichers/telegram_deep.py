"""
Telethon (MTProto) глубокое обогащение Telegram-каналов.
Находит @usernames администраторов, контакты в последних постах, linked group.

Требует: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION в env.
Сессия генерируется один раз: python scripts/gen_tg_session.py
"""
import re
import logging
from config import settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
_TG_RE = re.compile(r"(?:t\.me/|@)([a-zA-Z0-9_]{4,})")
_WA_RE = re.compile(r"(?:wa\.me/|whatsapp\.com/send\?phone=)[\d+]+")

_client = None


async def _get_client():
    global _client
    if not settings.telegram_api_id or not settings.telegram_session:
        return None
    if _client is None:
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            _client = TelegramClient(
                StringSession(settings.telegram_session),
                settings.telegram_api_id,
                settings.telegram_api_hash,
            )
            await _client.start()
        except Exception as e:
            logger.warning("Telethon init failed: %s", e)
            _client = None
    return _client


async def enrich_channel(handle: str) -> dict:
    """
    Returns dict with any of: contact_telegram, contact_email, contact_other, description.
    handle: Telegram @username without @
    """
    result: dict = {}
    client = await _get_client()
    if not client:
        return result

    try:
        from telethon.tl.functions.channels import GetFullChannelRequest
        from telethon.tl.types import ChannelParticipantsAdmins

        entity = await client.get_entity(handle)

        # Full channel info
        full = await client(GetFullChannelRequest(entity))
        about = full.full_chat.about or ""
        if about:
            result["description"] = about[:1000]

        # Extract email from about
        email_match = _EMAIL_RE.search(about)
        if email_match:
            result["contact_email"] = email_match.group(0)

        # Extract WhatsApp
        wa_match = _WA_RE.search(about)
        if wa_match:
            result["contact_other"] = wa_match.group(0)

        # Admins' @usernames
        admin_handles = []
        try:
            async for admin in client.iter_participants(entity, filter=ChannelParticipantsAdmins, limit=10):
                if hasattr(admin, "username") and admin.username:
                    admin_handles.append(admin.username)
        except Exception:
            pass

        if admin_handles and "contact_telegram" not in result:
            result["contact_telegram"] = admin_handles[0]

        # Scan last 50 messages for contact mentions if still no contact
        if "contact_email" not in result and "contact_telegram" not in result:
            try:
                async for msg in client.iter_messages(entity, limit=50):
                    text = getattr(msg, "text", "") or ""
                    if not text:
                        continue
                    m = _EMAIL_RE.search(text)
                    if m:
                        result["contact_email"] = m.group(0)
                        break
                    m = _TG_RE.search(text)
                    if m and m.group(1).lower() != handle.lower():
                        result["contact_telegram"] = m.group(1)
                        break
            except Exception:
                pass

    except Exception as e:
        logger.debug("Telethon enrich failed for %s: %s", handle, e)

    return result
