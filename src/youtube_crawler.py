"""
YouTube 频道爬虫 - 抓取订阅频道最新视频
"""
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build

YOUTUBE_CHANNELS = [
    {"name": "Lenny's Podcast",    "handle": "LennysPodcast"},
    {"name": "Tina Huang",         "handle": "TinaHuang1"},
    {"name": "Jeff Su",            "handle": "JeffSu"},
    {"name": "3Blue1Brown",        "handle": "3blue1brown"},
    {"name": "Andrej Karpathy",    "handle": "AndrejKarpathy"},
    {"name": "Chief PaPa 張志雲",  "handle": "ChiefPaPa"},
]


def get_youtube_videos(api_key: str, hours_back: int = 24) -> list[dict]:
    youtube = build("youtube", "v3", developerKey=api_key)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    results = []

    for ch in YOUTUBE_CHANNELS:
        try:
            ch_resp = youtube.channels().list(
                part="contentDetails,snippet",
                forHandle=ch["handle"],
            ).execute()

            items = ch_resp.get("items", [])
            if not items:
                print(f"  ⚠️  找不到频道: {ch['name']} (@{ch['handle']})")
                continue

            ch_info    = items[0]
            uploads_id = ch_info["contentDetails"]["relatedPlaylists"]["uploads"]
            ch_title   = ch_info["snippet"]["title"]

            pl_resp = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_id,
                maxResults=5,
            ).execute()

            for item in pl_resp.get("items", []):
                pub = item["contentDetails"].get("videoPublishedAt", "")
                if pub < since:
                    continue
                video_id = item["contentDetails"]["videoId"]
                desc = item["snippet"].get("description", "")
                results.append({
                    "channel":      ch_title,
                    "title":        item["snippet"]["title"],
                    "url":          f"https://www.youtube.com/watch?v={video_id}",
                    "published_at": pub[:10],
                    "description":  desc[:200].replace("\n", " "),
                })

            print(f"  ✅ {ch_title}: 检查完毕")

        except Exception as e:
            print(f"  ❌ 抓取 {ch['name']} 失败: {e}")

    return results
