"""
Anthropic 官方博客爬虫 - 近7天
"""
import re
import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_date(text: str) -> str:
    """'May 28, 2026' → '2026-05-28'，失败返回 ''"""
    m = re.match(r"(\w{3})\s+(\d+),\s+(\d{4})", text.strip())
    if m:
        mon, day, year = m.group(1), int(m.group(2)), int(m.group(3))
        if mon in MONTHS:
            return f"{year}-{MONTHS[mon]:02d}-{day:02d}"
    return ""


def get_anthropic_news(limit: int = 5, days_back: int = 7) -> list[dict]:
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        resp = requests.get("https://www.anthropic.com/news", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()

        for a in soup.find_all("a", href=lambda h: h and "/news/" in h):
            href = a["href"]
            if href in seen:
                continue
            title_el = a.find(["h2", "h3", "h4"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            title = re.sub(r'^[A-Z][a-z]{2}\s+\d+,\s+\d{4}[A-Za-z]+', '', title).strip()
            if not title or len(title) < 6:
                continue
            seen.add(href)

            # 向上找最近的 time 标签
            date_str = ""
            p = a.parent
            for _ in range(8):
                t = p.find("time")
                if t:
                    date_str = _parse_date(t.get_text(strip=True))
                    break
                p = p.parent

            # 有日期的严格过滤；无日期的保留（无法判断就放行）
            if date_str and date_str < cutoff:
                continue

            url = f"https://www.anthropic.com{href}" if href.startswith("/") else href
            description = ""
            p_el = a.find("p")
            if p_el:
                description = p_el.get_text(strip=True)[:200]

            results.append({
                "source": "Anthropic",
                "title": title,
                "url": url,
                "description": description,
                "date": date_str,
                "summary": "",
            })
            if len(results) >= limit:
                break

        print(f"  ✅ Anthropic {len(results)} 条（近{days_back}天）")
        return results
    except Exception as e:
        print(f"  ⚠️  Anthropic 抓取失败: {e}")
        return []
