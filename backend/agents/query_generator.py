"""
AI-генерация поисковых запросов для MENA аффилиат лидов.
Вместо ручного ввода — OpenAI генерирует ~30 разнообразных запросов.
"""
import json
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

FALLBACK_QUERIES = [
    {"query_text": "مواقع رهانات رياضية مصر", "geo": "egypt"},
    {"query_text": "كازينو اونلاين مصر", "geo": "egypt"},
    {"query_text": "توقعات كرة القدم مصر site:t.me", "geo": "egypt"},
    {"query_text": "egypt sports betting tips telegram", "geo": "egypt"},
    {"query_text": "مراهنات المغرب site:t.me", "geo": "morocco"},
    {"query_text": "pronostic foot maroc site:t.me", "geo": "morocco"},
    {"query_text": "كود ترويجي كازينو المغرب", "geo": "morocco"},
    {"query_text": "morocco betting predictions youtube.com/@", "geo": "morocco"},
    {"query_text": "مراهنات الجزائر توقعات", "geo": "algeria"},
    {"query_text": "pronostic algérie paris sportifs site:t.me", "geo": "algeria"},
    {"query_text": "algeria casino review promo code", "geo": "algeria"},
    {"query_text": "توقعات كرة القدم الجزائر youtube.com/@", "geo": "algeria"},
    {"query_text": "رهانات تونس توقعات site:t.me", "geo": "tunisia"},
    {"query_text": "paris sportifs tunisie site:t.me", "geo": "tunisia"},
    {"query_text": "tunisia betting tips promo code", "geo": "tunisia"},
    {"query_text": "كازينو اونلاين تونس مراجعة", "geo": "tunisia"},
    {"query_text": "رهانات ليبيا site:t.me", "geo": "libya"},
    {"query_text": "libya sports betting tips telegram", "geo": "libya"},
    {"query_text": "توقعات المنطقة العربية كرة القدم", "geo": "all"},
    {"query_text": "mena betting affiliate partner casino", "geo": "all"},
    {"query_text": "arab tipster channel betting predictions", "geo": "all"},
    {"query_text": "قنوات تيليجرام رهانات عربية", "geo": "all"},
    {"query_text": "maghreb pronostic football affilié", "geo": "all"},
    {"query_text": "best arabic sports betting channel youtube", "geo": "all"},
    {"query_text": "كود بونص مراهنات عربي 2024", "geo": "all"},
    {"query_text": "arabic casino review promo code 2024", "geo": "all"},
    {"query_text": "مراجعة موقع مراهنات مصر المغرب", "geo": "all"},
    {"query_text": "north africa betting tipster site:t.me", "geo": "all"},
    {"query_text": "شركاء تسويق كازينو عرب", "geo": "all"},
    {"query_text": "affiliate betting arabic youtube.com/@", "geo": "all"},
]

_GEO_PROMPT = {
    "egypt":   "Focus exclusively on Egypt (مصر).",
    "morocco": "Focus exclusively on Morocco (المغرب / Maroc).",
    "algeria": "Focus exclusively on Algeria (الجزائر / Algérie).",
    "tunisia": "Focus exclusively on Tunisia (تونس / Tunisie).",
    "libya":   "Focus exclusively on Libya (ليبيا).",
    "all":     "Cover all MENA countries: Egypt, Morocco, Algeria, Tunisia, Libya.",
}


async def generate_queries(geo: str = "all") -> list[dict]:
    """Return [{query_text, geo}, ...] of MENA-focused search queries."""
    geo = geo.lower().strip()
    geo_instruction = _GEO_PROMPT.get(geo, _GEO_PROMPT["all"])

    prompt = f"""You are a search query expert for finding betting/casino affiliate partners.
{geo_instruction}

Generate exactly 30 diverse search queries to find:
- Telegram tipster channels (use site:t.me)
- YouTube prediction channels (use youtube.com/@)
- Betting/casino affiliate websites and blogs
- Promo code review pages

Mix Arabic and English. Cover: sports predictions, casino reviews, promo codes, betting tips.

Return JSON: {{"queries": [{{"query_text": "...", "geo": "egypt|morocco|algeria|tunisia|libya|all"}}]}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2000,
        )
        data = json.loads(response.choices[0].message.content)
        queries = data.get("queries", [])
        if queries and isinstance(queries, list):
            valid = [
                {"query_text": str(q.get("query_text", "")), "geo": str(q.get("geo", geo))}
                for q in queries if q.get("query_text")
            ]
            if valid:
                logger.info("Generated %d queries via OpenAI for geo=%s", len(valid), geo)
                return valid
    except Exception as exc:
        logger.warning("query_generator OpenAI failed, using fallback: %s", exc)

    # Fallback
    if geo == "all":
        return FALLBACK_QUERIES
    return [q for q in FALLBACK_QUERIES if q["geo"] in (geo, "all")]
