"""
AI 摘要生成器 - 使用 Google Gemini（免费额度）
一次 API 调用批量生成所有摘要
"""
import json
import time
import os
from google import genai


def generate_summaries(youtube_items, github_items, anthropic_items):
    """
    一次性为所有条目生成摘要，返回结构：
    {
        "daily_summary": "...",
        "anthropic": ["摘要1", ...],
        "github":    ["摘要1", ...],
        "youtube":   ["摘要1", ...]
    }
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    lines = []

    if anthropic_items:
        lines.append("【Anthropic 动态】")
        for i, a in enumerate(anthropic_items, 1):
            extra = f" | {a['note']}" if a.get("note") else ""
            lines.append(f"{i}. {a['title']}{extra}")

    if github_items:
        lines.append("\n【GitHub 今日热门】")
        for i, g in enumerate(github_items, 1):
            desc = f" - {g['description']}" if g.get("description") else ""
            lines.append(f"{i}. {g['title']}{desc} | {g.get('stars_today', '')}")

    if youtube_items:
        lines.append("\n【YouTube 新视频】")
        for i, v in enumerate(youtube_items, 1):
            desc = f" | {v['description'][:120]}" if v.get("description") else ""
            lines.append(f"{i}. 【{v['channel']}】{v['title']}{desc}")

    prompt = f"""你是一个 AI 科技资讯日报助手。请为以下今日内容生成中文摘要。

{chr(10).join(lines)}

要求：
- daily_summary：2-3 句话，概括今日整体亮点，突出最重要的信息
- 每条摘要：1-2 句话，说清楚"是什么、有什么用/意义"，简洁明了
- 全部中文输出

请严格按以下 JSON 格式输出，不要有任何其他内容：
{{
  "daily_summary": "...",
  "anthropic": [{", ".join(['"摘要"'] * len(anthropic_items))}],
  "github":    [{", ".join(['"摘要"'] * len(github_items))}],
  "youtube":   [{", ".join(['"摘要"'] * len(youtube_items))}]
}}

注意：数组长度必须与条目数完全一致（anthropic={len(anthropic_items)}, github={len(github_items)}, youtube={len(youtube_items)}）"""

    # 限速自动重试，最多 3 次
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            text = resp.text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            if attempt < 2:
                wait = 35 * (attempt + 1)
                print(f"  Gemini 调用失败（{e}），{wait} 秒后重试...")
                time.sleep(wait)
            else:
                raise


def enrich_with_summaries(youtube_items, github_items, anthropic_items):
    """调用 AI 摘要并将结果写回各条目的 'summary' 字段，同时返回 daily_summary。"""
    try:
        result = generate_summaries(youtube_items, github_items, anthropic_items)
    except Exception as e:
        print(f"  ⚠️  AI 摘要生成失败，将跳过摘要: {e}")
        for lst in (anthropic_items, github_items, youtube_items):
            for item in lst:
                item.setdefault("summary", "")
        return ""

    for i, item in enumerate(anthropic_items):
        item["summary"] = result["anthropic"][i] if i < len(result["anthropic"]) else ""
    for i, item in enumerate(github_items):
        item["summary"] = result["github"][i] if i < len(result["github"]) else ""
    for i, item in enumerate(youtube_items):
        item["summary"] = result["youtube"][i] if i < len(result["youtube"]) else ""

    return result.get("daily_summary", "")
