"""
AI 资讯日报 Agent 主入口
每天自动抓取官方博客 / GitHub Trending / 精读博客，AI 生成摘要，写入飞书文档
"""
import os
import sys

from anthropic_crawler      import get_anthropic_news
from openai_crawler         import get_openai_news
from deepmind_crawler       import get_deepmind_news
from github_crawler         import get_github_trending
from simon_willison_crawler import get_simon_willison_posts
from baoyu_crawler          import get_baoyu_posts
from ai_summarizer          import enrich_with_summaries
from feishu_writer          import FeishuDocWriter


def main():
    feishu_app_id     = os.environ["FEISHU_APP_ID"]
    feishu_app_secret = os.environ["FEISHU_APP_SECRET"]
    feishu_doc_token  = os.environ["FEISHU_DOC_TOKEN"]

    print("=" * 50)
    print("🚀  AI 资讯日报 Agent 启动")
    print("=" * 50)

    print("\n🏛️  抓取官方博客...")
    anthropic_items = get_anthropic_news(limit=5)
    openai_items    = get_openai_news(limit=5)
    deepmind_items  = get_deepmind_news(limit=5)
    official_items  = anthropic_items + openai_items + deepmind_items

    print("\n🔥  抓取 GitHub Trending（AI）...")
    github_items = get_github_trending(since="daily", limit=10)

    print("\n📖  抓取每日精读...")
    simon_items = get_simon_willison_posts(limit=5)
    baoyu_items = get_baoyu_posts(limit=3)
    reading_items = simon_items + baoyu_items

    if not any([official_items, github_items, reading_items]):
        print("⚠️  今日无新内容，跳过写入")
        return

    print("\n✨  AI 生成摘要...")
    daily_summary = enrich_with_summaries(official_items, github_items, reading_items)
    print("    摘要生成完毕\n")

    print("📝  写入飞书文档...")
    writer = FeishuDocWriter(feishu_app_id, feishu_app_secret, feishu_doc_token)
    writer.write_daily_report(official_items, github_items, reading_items,
                              daily_summary=daily_summary)

    print("\n🎉  完成！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌  运行出错: {e}")
        sys.exit(1)
