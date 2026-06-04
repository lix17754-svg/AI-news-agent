"""
Anthropic 动态爬虫
- anthropic.com/news  官方博客/公告
- github.com/anthropics  开源项目最新动态
"""
import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

def _get_anthropic_blog(limit: int = 5) -> list[dict]:
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
                title_el = a
            title = title_el.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            results.append({"source": "Anthropic 官网", "title": title, "url": url, "note": ""})
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        print(f"  ⚠️  Anthropic 博客抓取失败: {e}")
        return []

def _get_anthropic_github(limit: int = 5) -> list[dict]:
    try:
        resp = requests.get(
            "https://api.github.com/orgs/anthropics/repos",
            params={"sort": "updated", "per_page": 30},   # 多拉一些再过滤
            headers={"User-Agent": "AI-News-Agent/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        results = []
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        for repo in resp.json():
            if repo["updated_at"][:10] < cutoff:
                continue
            desc = repo.get("description") or "暂无描述"
            results.append({
                "source": "Anthropic GitHub",
                "title":  repo["name"],
                "url":    repo["html_url"],
                "note":   f"⭐{repo['stargazers_count']}  更新于 {repo['updated_at'][:10]}  {desc}",
            })
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        print(f"  ⚠️  Anthropic GitHub 抓取失败: {e}")
        return []

def get_anthropic_news(limit: int = 5) -> list[dict]:
    blog   = _get_anthropic_blog(limit)
    github = _get_anthropic_github(limit)
    print(f"  ✅ Anthropic 博客 {len(blog)} 条 | GitHub {len(github)} 条")
    return blog + github
