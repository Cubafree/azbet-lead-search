"""
Competitor intelligence scraper.
Searches Serper for affiliates promoting each competitor across MENA geos.
Returns list of channel dicts + detected promo codes.
"""
import re
import logging
from scrapers import serper
from scrapers import telegram as tg_scraper
from scrapers import youtube as yt_scraper

logger = logging.getLogger(__name__)

MENA_GEOS = ["egypt", "morocco", "algeria", "tunisia", "libya"]

# Promo code patterns per competitor
PROMO_PATTERNS = {
    "1xbet":     re.compile(r"\b(AZ\w{2,8})\b", re.I),
    "melbet":    re.compile(r"\b(MB\w{2,8}|MELBET\w{0,6})\b", re.I),
    "mostbet":   re.compile(r"\b(MSB\w{2,8}|MOSTBET\w{0,6})\b", re.I),
    "1win":      re.compile(r"\b(1W\w{2,8})\b", re.I),
    "betwinner": re.compile(r"\b(BW\w{2,8}|BETWINNER\w{0,6})\b", re.I),
    "22bet":     re.compile(r"\b(22B\w{2,8})\b", re.I),
}


async def scan_competitor(competitor: dict, geo: str = "all") -> dict:
    """
    Scans for affiliates promoting `competitor` in `geo`.
    Returns:
      {
        "tg_channels": [...],
        "yt_channels": [...],
        "promo_codes": [...],
        "affiliate_count": int,
      }
    """
    name = competitor["name"]
    geos = MENA_GEOS if geo == "all" else [geo]
    pattern = PROMO_PATTERNS.get(name)

    tg_results: list[dict] = []
    yt_results: list[dict] = []
    promo_codes: set[str] = set()

    seen_tg: set[str] = set()
    seen_yt: set[str] = set()

    for g in geos:
        for lang in ["en", "ar"]:
            try:
                # Telegram affiliates
                tg_query = f'"{name}" promo code site:t.me {g}'
                data = await serper.search(tg_query, "telegram", g, lang)
                for ch in tg_scraper.parse_serper_results(data, lang, g):
                    if ch["handle"] not in seen_tg:
                        seen_tg.add(ch["handle"])
                        ch["promoting"] = name
                        tg_results.append(ch)
                    # Extract promo codes from snippets
                    if pattern:
                        for item in data.get("organic", []):
                            txt = item.get("snippet", "") + " " + item.get("title", "")
                            for m in pattern.finditer(txt):
                                promo_codes.add(m.group(1).upper())

            except Exception as e:
                logger.debug("TG scan error %s/%s/%s: %s", name, g, lang, e)

            try:
                # YouTube affiliates
                yt_query = f'"{name}" review promo code {g} youtube.com/@'
                data = await serper.search(yt_query, "youtube", g, lang)
                for ch in yt_scraper.parse_serper_results(data, lang, g):
                    if ch["handle"] not in seen_yt:
                        seen_yt.add(ch["handle"])
                        ch["promoting"] = name
                        yt_results.append(ch)

            except Exception as e:
                logger.debug("YT scan error %s/%s/%s: %s", name, g, lang, e)

    return {
        "tg_channels": tg_results,
        "yt_channels": yt_results,
        "promo_codes": sorted(promo_codes),
        "affiliate_count": len(tg_results) + len(yt_results),
    }


async def scan_all_competitors(pool, geo: str = "all") -> list[dict]:
    """
    Runs scan_competitor for every competitor in DB.
    Returns list of scan result dicts with competitor name attached.
    """
    rows = await pool.fetch("SELECT * FROM competitors ORDER BY name")
    results = []
    for row in rows:
        comp = dict(row)
        try:
            result = await scan_competitor(comp, geo)
            result["competitor"] = comp
            results.append(result)
            logger.info(
                "Competitor scan %s: %d affiliates, %d promo codes",
                comp["name"], result["affiliate_count"], len(result["promo_codes"])
            )
        except Exception as e:
            logger.error("scan_all_competitors error for %s: %s", comp["name"], e)
    return results
