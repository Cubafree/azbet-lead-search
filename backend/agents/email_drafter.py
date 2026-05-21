"""
Генерация персонализированного черновика письма для аффилиат аутрич.
Вызывается только для high/medium приоритетных лидов.
"""
import json
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM_PROMPT = (
    "You are a partnership outreach specialist for AzimutBet — a licensed online "
    "sports betting and casino operator targeting MENA markets (Egypt, Morocco, Algeria, "
    "Tunisia, Libya). AzimutBet offers: up to 45% RevShare, dedicated Arabic-language "
    "support, fast local payouts, and country-specific bonuses. "
    "Write short, professional, non-spammy outreach emails in English."
)


async def draft_email(channel: dict) -> str | None:
    """
    Returns formatted email string "Subject: ...\\n\\n{body}" or None.
    Only drafts for high/medium priority channels.
    """
    priority = (channel.get("priority") or "").lower()
    if priority not in ("high", "medium"):
        return None

    name = channel.get("name") or channel.get("handle") or "there"
    platform = channel.get("platform") or ""
    niche = channel.get("niche") or ""
    geo_focus = channel.get("geo_focus") or ""
    followers = channel.get("followers")
    ai_summary = channel.get("ai_summary") or ""
    competitors = channel.get("mentioned_competitors") or ""
    monthly_visits = channel.get("estimated_monthly_visits")

    # Build context lines
    ctx = []
    if niche:
        ctx.append(f"Niche: {niche}")
    if geo_focus:
        ctx.append(f"Region: {geo_focus}")
    if followers:
        ctx.append(f"Followers: {followers:,}")
    if monthly_visits:
        ctx.append(f"Est. monthly visits: {monthly_visits:,}")
    if ai_summary:
        ctx.append(f"About: {ai_summary}")
    if competitors:
        ctx.append(f"Mentions competitors: {competitors}")

    ctx_str = "\n".join(ctx) if ctx else "General betting/casino content."

    prompt = (
        f"Write a partnership outreach email for:\n"
        f"Name: {name}\nPlatform: {platform}\n{ctx_str}\n\n"
        f"Rules:\n"
        f"- Body max 120 words\n"
        f"- Greet by name/handle\n"
        f"- Reference their niche/region if known\n"
        f"- Mention AzimutBet's 45% RevShare + MENA localisation briefly\n"
        f"- End with CTA to reply and discuss terms\n"
        f"- No spammy superlatives\n\n"
        f'Return JSON: {{"subject": "...", "body": "Hi {name},\\n\\n..."}}'
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        data = json.loads(resp.choices[0].message.content)
        subject = (data.get("subject") or "").strip()
        body = (data.get("body") or "").strip()
        if subject and body:
            return f"Subject: {subject}\n\n{body}"
    except Exception as exc:
        logger.warning("email_drafter failed for %s: %s", name, exc)

    return None
