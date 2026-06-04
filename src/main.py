"""
AI News Agent 主入口
每天自动抓取 YouTube / GitHub / Anthropic 动态，AI 生成摘要，写入飞书文档
"""
import os
import sys

from youtube_crawler   import get_youtube_videos
from github_crawler    import get_github_trending
from anthropic_crawler import get_anthropic_news
from ai_summarizer     import enrich_with_summaries
from feishu_writer     import FeishuDocWriter


def main():
    feishu_app_id     = os.environ["FEISHU_APP_ID"]
    feishu_app_secret = os.environ["FEISHU_APP_SECRET"]
    feishu_doc_token  = os.environ["FEISHU_DOC_TOKEN"]
    youtube_api_key   = os.environ["YOUTUBE_API_KEY"]

    print("=" * 50)
    print("🚀  AI News Agent 启动")
    print("=" * 50)

    print("\n🤖  抓取 Anthropic 动态...")
    anthropic_items = get_anthropic_news(limit=5)
    print()

    print("🔥  抓取 GitHub Trending（今日）...")
    github_items = get_github_trending(since="daily", limit=10)
    print(f"    共 {len(github_items)} 个热门仓库\n")

    print("📺  抓取 YouTube（过去 24 小时）...")
    youtube_items = get_youtube_videos(youtube_api_key, hours_back=24)
    print(f"    共 {len(youtube_items)} 个新视频\n")

    if not any([youtube_items, github_items, anthropic_items]):
        print("⚠️  今日无新内容，跳过写入")
        return

    print("✨  AI 生成摘要...")
    daily_summary = enrich_with_summaries(youtube_items, github_items, anthropic_items)
    print("    摘要生成完毕\n")

    print("📝  写入飞书文档...")
    writer = FeishuDocWriter(feishu_app_id, feishu_app_secret, feishu_doc_token)
    writer.write_daily_report(youtube_items, github_items, anthropic_items,
                              daily_summary=daily_summary)

    print("\n🎉  完成！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌  运行出错: {e}")
        sys.exit(1)
