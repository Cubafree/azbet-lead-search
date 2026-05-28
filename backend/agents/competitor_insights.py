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
    prompt = f"""You are a competitive intelligence analyst for AzimutBet, a betting operator that is NEW to the MENA market and actively building its affiliate network from scratch.

IMPORTANT CONTEXT:
- AzimutBet has NO existing affiliate partners yet — we are just entering this market
- The "leads" in our database are DISCOVERED CANDIDATES scraped from the internet, NOT active partners
- We have not yet contacted or signed deals with any of these channels
- Our goal is to identify and approach the best affiliates BEFORE competitors lock them in

Competitor data (from last scan):
{json.dumps(competitors_data, indent=2)}

Our discovered lead candidates (scraped, not yet partners):
{json.dumps(our_stats, indent=2)}

Generate 5 actionable competitive intelligence insights for a new entrant. Focus on:
1. Which platforms/geos competitors are weakest in — our best entry points
2. Markets or platforms where competitors are growing fast and we need to move quickly
3. Promo code / campaign strategies worth copying or countering as a new player
4. Which lead candidates we should prioritize approaching first, before competitors lock them in
5. Any anomalies or interesting patterns a new entrant can exploit

Return JSON:
{{
  "insights": [
    {{
      "type": "opportunity|threat|trend|action",
      "title": "short title (max 8 words)",
      "body": "2-3 sentence explanation with specific data points, framed for a new market entrant",
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

    prompt = f"""AzimutBet is a NEW entrant to the MENA betting market with no existing affiliate partners yet.
These are discovered affiliate channels that are ALREADY promoting competitors — we have NOT contacted them.
{chr(10).join(summary)}

In 2-3 sentences, give a strategic recommendation for a new entrant: which channels to prioritize approaching first,
what angle/offer to use to pull them away from or alongside competitors, and the urgency level."""

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
