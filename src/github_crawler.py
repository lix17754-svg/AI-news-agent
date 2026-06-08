"""
GitHub 热门仓库爬虫 - 只保留 AI 相关仓库
"""
import requests
from bs4 import BeautifulSoup

AI_KEYWORDS = {
    "ai", "llm", "agent", "model", "gpt", "claude", "embedding",
    "inference", "transformer", "diffusion", "rag", "multimodal",
    "chatbot", "fine-tun", "finetun", "openai", "anthropic", "gemini",
    "mistral", "llama", "neural", "deepseek", "copilot",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _is_ai_related(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    return any(kw in text for kw in AI_KEYWORDS)


def get_github_trending(since: str = "daily", limit: int = 10) -> list[dict]:
    url = f"https://github.com/trending?since={since}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ❌ GitHub Trending 请求失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for repo in soup.select("article.Box-row"):
        name_tag = repo.select_one("h2 a")
        if not name_tag:
            continue
        repo_path  = name_tag.get("href", "").strip("/")
        repo_url   = f"https://github.com/{repo_path}"
        repo_title = repo_path.replace("/", " / ")

        desc_tag    = repo.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        if not _is_ai_related(repo_title, description):
            continue

        stars_today_tag = repo.select_one("span.d-inline-block.float-sm-right")
        stars_today     = stars_today_tag.get_text(strip=True) if stars_today_tag else ""

        lang_tag = repo.select_one("[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else ""

        results.append({
            "source": "GitHub",
            "title": repo_title,
            "url": repo_url,
            "description": description,
            "language": language,
            "stars_today": stars_today,
            "summary": "",
        })
        if len(results) >= limit:
            break

    print(f"  ✅ GitHub Trending（AI）{len(results)} 个")
    return results
