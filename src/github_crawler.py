"""
GitHub 热门仓库爬虫 - 抓取每日 Trending
"""
import requests
from bs4 import BeautifulSoup


def get_github_trending(since: str = "daily", limit: int = 10) -> list[dict]:
    url = f"https://github.com/trending?since={since}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ❌ 请求 GitHub Trending 失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for repo in soup.select("article.Box-row")[:limit]:
        name_tag = repo.select_one("h2 a")
        if not name_tag:
            continue
        repo_path  = name_tag.get("href", "").strip("/")
        repo_url   = f"https://github.com/{repo_path}"
        repo_title = repo_path.replace("/", " / ")

        desc_tag    = repo.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else "暂无描述"

        lang_tag  = repo.select_one("[itemprop='programmingLanguage']")
        language  = lang_tag.get_text(strip=True) if lang_tag else ""

        stars_today_tag = repo.select_one("span.d-inline-block.float-sm-right")
        stars_today     = stars_today_tag.get_text(strip=True) if stars_today_tag else ""

        results.append({
            "title":       repo_title,
            "url":         repo_url,
            "description": description,
            "language":    language,
            "stars_today": stars_today,
        })

    return results
