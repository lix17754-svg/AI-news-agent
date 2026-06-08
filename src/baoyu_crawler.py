"""
宝玉翻译博客爬虫 - 近7天
优先 RSS，失败则网页抓取
"""
import datetime
import requests
from bs4 import BeautifulSoup
import feedparser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

RSS_URLS = [
    "https://baoyu.io/feed.xml",
    "https://baoyu.io/rss.xml",
    "https://baoyu.io/atom.xml",
    "https://baoyu.io/feed",
]


def _try_rss(limit: int, days_back: int) -> list[dict]:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            results = []
            for entry in feed.entries:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime.datetime(*published[:6])
                    if pub_dt < cutoff:
                        continue
                title = entry.get("title", "").strip()
                link  = entry.get("link", "")
                desc  = entry.get("summary", "")
                if desc:
                    desc = BeautifulSoup(desc, "html.parser").get_text()[:200].strip()
                if title and link:
                    results.append({
                        "source": "宝玉",
                        "title": title,
                        "url": link,
                        "description": desc,
                        "summary": "",
                    })
                if len(results) >= limit:
                    break
            if results:
                return results
        except Exception:
            continue
    return []


def _try_web(limit: int) -> list[dict]:
    try:
        resp = requests.get("https://baoyu.io", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href or href in seen or href in ("/", "#"):
                continue
            if not any(p in href for p in ["/blog/", "/translations/", "/posts/"]):
                continue
            seen.add(href)
            url = f"https://baoyu.io{href}" if href.startswith("/") else href
            title_el = a.find(["h2", "h3", "h4"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            desc = ""
            p_el = a.find("p")
            if p_el:
                desc = p_el.get_text(strip=True)[:200]
            results.append({
                "source": "宝玉",
                "title": title,
                "url": url,
                "description": desc,
                "summary": "",
            })
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []


def get_baoyu_posts(limit: int = 3, days_back: int = 7) -> list[dict]:
    results = _try_rss(limit, days_back) or _try_web(limit)
    print(f"  ✅ 宝玉 {len(results)} 条（近{days_back}天）")
    return results
