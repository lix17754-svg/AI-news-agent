"""
Simon Willison 博客爬虫 - 通过 RSS 抓取
simonwillison.net 每日更新 AI 动态，有标准 RSS feed
"""
import datetime
import feedparser

RSS_URLS = [
    "https://simonwillison.net/atom/entries/",
    "https://simonwillison.net/rss/",
]


def get_simon_willison_posts(limit: int = 5, hours_back: int = 72) -> list[dict]:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    feed = None

    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                break
        except Exception:
            continue

    if not feed or not feed.entries:
        print("  ⚠️  Simon Willison RSS 抓取失败")
        return []

    results = []
    for entry in feed.entries:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            pub_dt = datetime.datetime(*published[:6])
            if pub_dt < cutoff:
                continue

        title = entry.get("title", "").strip()
        url = entry.get("link", "")
        description = entry.get("summary", "")
        if description:
            from bs4 import BeautifulSoup
            description = BeautifulSoup(description, "html.parser").get_text()[:200].strip()

        if not title or not url:
            continue

        results.append({
            "source": "Simon Willison",
            "title": title,
            "url": url,
            "description": description,
            "summary": "",
        })
        if len(results) >= limit:
            break

    print(f"  ✅ Simon Willison {len(results)} 条")
    return results
