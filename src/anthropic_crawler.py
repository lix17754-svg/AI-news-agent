"""
Anthropic 官方博客爬虫
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def get_anthropic_news(limit: int = 5) -> list[dict]:
    try:
        resp = requests.get("https://www.anthropic.com/news", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/news/" not in href or href in seen:
                continue
            seen.add(href)

            url = f"https://www.anthropic.com{href}" if href.startswith("/") else href
            title_el = a.find(["h2", "h3", "h4"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 6:
                continue

            # 清洗标题：去掉开头的日期/分类前缀（如 "Jun 3, 2026AnnouncementsXXX"）
            import re
            title = re.sub(r'^[A-Z][a-z]{2}\s+\d+,\s+\d{4}[A-Za-z]+', '', title).strip()

            description = ""
            p_el = a.find("p")
            if p_el:
                description = p_el.get_text(strip=True)[:200]

            results.append({
                "source": "Anthropic",
                "title": title,
                "url": url,
                "description": description,
                "summary": "",
            })
            if len(results) >= limit:
                break

        print(f"  ✅ Anthropic {len(results)} 条")
        return results
    except Exception as e:
        print(f"  ⚠️  Anthropic 抓取失败: {e}")
        return []
