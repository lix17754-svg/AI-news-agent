"""
OpenAI 官方发布爬虫
OpenAI 网页全部 403，改用 sitemap 获取最新发布 URL + 日期
slug 转标题作为展示名
"""
import re
import datetime
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

SITEMAP_URLS = [
    "https://openai.com/sitemap.xml/product/",
    "https://openai.com/sitemap.xml/research/",
]


def _slug_to_title(slug: str) -> str:
    words = slug.strip("/").split("-")
    return " ".join(w.capitalize() for w in words)


def get_openai_news(limit: int = 5, days_back: int = 3) -> list[dict]:
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    seen = set()
    results = []

    for sitemap_url in SITEMAP_URLS:
        try:
            r = requests.get(sitemap_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            locs  = re.findall(r"<loc>(.*?)</loc>", r.text)
            mods  = re.findall(r"<lastmod>(.*?)</lastmod>", r.text)

            for loc, mod in zip(locs, mods):
                if mod[:10] < cutoff:
                    break  # sitemap 按时间倒序，遇到旧的直接停
                if loc in seen:
                    continue
                seen.add(loc)

                slug  = loc.rstrip("/").split("/")[-1]
                title = _slug_to_title(slug)

                results.append({
                    "source": "OpenAI",
                    "title": title,
                    "url": loc,
                    "description": "",
                    "summary": "",
                })
        except Exception as e:
            print(f"  ⚠️  OpenAI sitemap {sitemap_url} 失败: {e}")

    results = results[:limit]
    print(f"  ✅ OpenAI {len(results)} 条")
    return results
