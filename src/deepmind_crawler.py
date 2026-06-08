"""
Google DeepMind 官方博客爬虫
页面标题在 <a> 外部，改用 slug 转标题 + data-event-nav-name 辅助
"""
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _slug_to_title(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.strip("/").split("-"))


def get_deepmind_news(limit: int = 5) -> list[dict]:
    try:
        resp = requests.get(
            "https://deepmind.google/discover/blog/", headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.match(r"^/blog/[a-z]", href):
                continue
            if href in seen:
                continue
            seen.add(href)

            url = f"https://deepmind.google{href}"
            slug = href.strip("/").split("/")[-1]

            # 优先用 data-event-nav-name 最后一段，次选 slug 转标题
            nav_name = a.get("data-event-nav-name", "")
            if nav_name and " - " in nav_name:
                short = nav_name.rsplit(" - ", 1)[-1].strip()
                # short 太短时（<10字）补全用 slug
                title = short if len(short) >= 10 else _slug_to_title(slug)
            else:
                title = _slug_to_title(slug)

            results.append({
                "source": "DeepMind",
                "title": title,
                "url": url,
                "description": "",
                "summary": "",
            })
            if len(results) >= limit:
                break

        print(f"  ✅ DeepMind {len(results)} 条")
        return results
    except Exception as e:
        print(f"  ⚠️  DeepMind 抓取失败: {e}")
        return []
