"""
AI 摘要生成器 - 使用 OpenAI GPT-5.5
一次 API 调用批量生成所有摘要 + 今日速览
"""
import json
import time
import os
from openai import OpenAI


def generate_summaries(official_items, github_items, reading_items):
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://ops-ai-gateway.yc345.tv/v1",
    )

    all_items = official_items + github_items + reading_items
    if not all_items:
        return {"daily_summary": "", "summaries": []}

    lines = []
    for i, item in enumerate(all_items, 1):
        source = item.get("source", "")
        title = item["title"]
        desc = item.get("description", "")
        stars = item.get("stars_today", "")

        if stars:
            entry = f"{i}. [GitHub] {title} - {desc} ({stars})"
        elif desc:
            entry = f"{i}. [{source}] {title} | {desc[:150]}"
        else:
            entry = f"{i}. [{source}] {title}"
        lines.append(entry)

    prompt = f"""你是一个 AI 科技资讯周报助手。以下是本周 AI 领域的最新内容（共 {len(all_items)} 条）：

{chr(10).join(lines)}

请生成：
1. weekly_summary：3-5 句话，叙述体，有观点。说清楚本周最重要的 1-2 件事、为什么重要、对行业意味着什么。
   【严格禁止使用以下模糊词汇】：提升、加速、进一步、前沿、新阶段、竞争加剧、持续发展。
   【必须做到】：出现具体产品名、功能名或数字，让不知情的人看完就知道发生了什么。
2. summaries：长度恰好为 {len(all_items)} 的数组，按顺序一一对应每条内容，每条 1 句话（20-40 字），说清楚"是什么 + 为什么值得关注"，同样禁止模糊词。

严格按以下 JSON 格式输出，不要有任何其他内容：
{{
  "weekly_summary": "...",
  "summaries": [{", ".join(['"摘要"'] * len(all_items))}]
}}"""

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="gpt-5.5",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content.strip())
        except Exception as e:
            if attempt < 2:
                wait = 10 * (attempt + 1)
                print(f"  OpenAI 调用失败（{e}），{wait} 秒后重试...")
                time.sleep(wait)
            else:
                raise


def enrich_with_summaries(official_items, github_items, reading_items):
    """调用 AI 摘要，将 summary 写回各条目，返回 daily_summary。"""
    all_items = official_items + github_items + reading_items
    try:
        result = generate_summaries(official_items, github_items, reading_items)
    except Exception as e:
        print(f"  ⚠️  AI 摘要生成失败，跳过摘要: {e}")
        for item in all_items:
            item.setdefault("summary", "")
        return ""

    summaries = result.get("summaries", [])
    for i, item in enumerate(all_items):
        item["summary"] = summaries[i] if i < len(summaries) else ""

    return result.get("weekly_summary", "") or result.get("daily_summary", "")
