"""
AI-квалификация канала через OpenAI.
Определяет: geo_focus, niche, priority, ai_summary.
"""
import json
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a lead qualification agent for AzimutBet — an online sports betting and casino operator targeting the MENA region (Egypt, Morocco, Algeria, Tunisia, Libya).

Analyze the provided channel/website and classify it as a potential affiliate partner.

Respond ONLY with a valid JSON object (no markdown, no explanation):
{
  "geo_focus": "<egypt|morocco|algeria|tunisia|libya|maghreb|mena|global|null>",
  "niche": "<tipster|sports_betting|casino|mixed|sports_news|lifestyle|null>",
  "priority": "<high|medium|low>",
  "ai_summary": "<why this channel is relevant for us, max 120 chars, in English>"
}

Priority rules:
- high: betting/casino content + 10k+ followers + mentions competitor OR promo code
- high: betting/casino content + 50k+ followers (any)
- medium: betting/casino content but low followers OR unclear niche
- low: not relevant (streaming, fixtures only, official competitor channel, politics, unrelated)
"""


async def qualify(channel: dict) -> dict:
    """
    channel: dict с полями name, description, followers, platform,
             mentioned_competitors, competitor_promo, language, geo_focus
    Возвращает: {geo_focus, niche, priority, ai_summary}
    """
    user_msg = f"""Platform: {channel.get('platform')}
Name: {channel.get('name')}
Handle: {channel.get('handle')}
Description: {channel.get('description') or 'N/A'}
Followers: {channel.get('followers') or 'unknown'}
Mentioned competitors: {channel.get('mentioned_competitors') or 'none'}
Competitor promo code: {channel.get('competitor_promo') or 'none'}
Language: {channel.get('language') or 'unknown'}
Geo focus: {channel.get('geo_focus') or 'unknown'}"""

    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        # Нормализуем поля
        return {
            "geo_focus": result.get("geo_focus"),
            "niche": result.get("niche"),
            "priority": result.get("priority", "low"),
            "ai_summary": result.get("ai_summary"),
        }
    except Exception as e:
        return {"geo_focus": None, "niche": None, "priority": "low", "ai_summary": f"error: {e}"}
