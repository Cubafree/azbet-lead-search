"""
AI-generated competitive intelligence insights.
Takes aggregated competitor metrics and returns actionable recommendations.
"""
import json
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_insights(competitors_data: list[dict], our_stats: dict) -> list[dict]:
    """
    competitors_data: list of {name, affiliate_count, top_geos, promo_codes, signals_count}
    our_stats: {total_leads, by_platform, top_geos}
    Returns list of {type, title, body, priority} insight dicts.
    """
    prompt = f"""You are a competitive intelligence analyst for AzimutBet, a betting operator expanding in MENA.

Competitor data (from last scan):
{json.dumps(competitors_data, indent=2)}

Our affiliate lead base stats:
{json.dumps(our_stats, indent=2)}

Generate 5 actionable competitive intelligence insights. Focus on:
1. Gaps our competitors have that we can exploit
2. Markets or platforms where competitors are growing fast
3. Promo code / campaign strategies worth copying or countering
4. Affiliates we should prioritize approaching before competitors lock them in
5. Any anomalies or interesting patterns

Return JSON:
{{
  "insights": [
    {{
      "type": "opportunity|threat|trend|action",
      "title": "short title (max 8 words)",
      "body": "2-3 sentence explanation with specific data points",
      "priority": "high|medium|low",
      "geo": "egypt|morocco|algeria|tunisia|libya|all"
    }}
  ]
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )
        data = json.loads(response.choices[0].message.content)
        insights = data.get("insights", [])
        logger.info("Generated %d competitor insights", len(insights))
        return insights
    except Exception as e:
        logger.warning("competitor_insights OpenAI failed: %s", e)
        return []


async def generate_overlap_insights(overlap_channels: list[dict]) -> str:
    """
    Takes list of our leads that also promote competitors.
    Returns a short strategic note.
    """
    if not overlap_channels:
        return ""

    summary = [
        f"@{ch.get('handle')} ({ch.get('platform')}, {ch.get('followers', '?')} followers) "
        f"→ promotes {ch.get('mentioned_competitors')}"
        for ch in overlap_channels[:20]
    ]

    prompt = f"""These are affiliate channels that are already promoting our competitors in MENA.
{chr(10).join(summary)}

In 2-3 sentences, give a strategic recommendation: which to prioritize approaching,
what angle to use, and what risk they represent if we don't move fast."""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("overlap_insights OpenAI failed: %s", e)
        return ""
