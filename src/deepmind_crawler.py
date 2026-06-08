"""
Google DeepMind 官方博客爬虫 - 近7天
日期精度为月份，过滤当月+上月
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
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def _parse_month_year(text: str):
    """'May 2026' → (2026, 5)，失败返回 None"""
    m = re.match(r"(\w+)\s+(\d{4})", text.strip())
    if m and m.group(1) in MONTHS:
        return int(m.group(2)), MONTHS[m.group(1)]
    return None


def _is_recent(month_year_text: str, weeks_back: int = 5) -> bool:
    """判断月份是否在最近 N 周内（月粒度）"""
    parsed = _parse_month_year(month_year_text)
    if not parsed:
        return False  # 无法判断时跳过，避免旧文章漏进来
    year, month = parsed
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(weeks=weeks_back)
    article_date = datetime.datetime(year, month, 28)  # 取月末保守估计
    return article_date >= cutoff


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

            # 找最近的 time 标签（月粒度）
            month_text = ""
            p = a.parent
            for _ in range(8):
                t = p.find("time")
                if t:
                    month_text = t.get_text(strip=True)
                    break
                p = p.parent

            if not month_text or not _is_recent(month_text):
                continue

            url = f"https://deepmind.google{href}"
            slug = href.strip("/").split("/")[-1]

            nav_name = a.get("data-event-nav-name", "")
            if nav_name and " - " in nav_name:
                short = nav_name.rsplit(" - ", 1)[-1].strip()
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

        print(f"  ✅ DeepMind {len(results)} 条（近5周）")
        return results
    except Exception as e:
        print(f"  ⚠️  DeepMind 抓取失败: {e}")
        return []
