"""
飞书文档写入器
block_type=2 的字段名是 "text"，不是 "paragraph"
"""
import datetime
import requests


def _el(text, url="", bold=False):
    style = {}
    if url:
        style["link"] = {"url": url}
    if bold:
        style["bold"] = True
    return {"text_run": {"content": text, "text_element_style": style}}


def _text_blk(elements):
    return {"block_type": 2, "text": {"elements": elements, "style": {"align": 1}}}


def _h1(elements):
    return {"block_type": 3, "heading1": {"elements": elements, "style": {"align": 1}}}


def _h2(elements):
    return {"block_type": 4, "heading2": {"elements": elements, "style": {"align": 1}}}


def _bullet(elements, sub_text=""):
    blk = {"block_type": 12, "bullet": {"elements": elements, "style": {"align": 1}}}
    if sub_text:
        blk["children"] = [
            {"block_type": 12, "bullet": {"elements": [_el(sub_text)], "style": {"align": 1}}}
        ]
    return blk


def _analysis_blocks(summary_text):
    """将多段分析文本拆成多个段落块，每段独立成块"""
    blocks = [_h2([_el("🧠 本周深度分析")])]
    paragraphs = [p.strip() for p in summary_text.split("\n\n") if p.strip()]
    for para in paragraphs:
        blocks.append(_text_blk([_el(para)]))
    return blocks


class FeishuDocWriter:
    def __init__(self, app_id, app_secret, doc_token):
        self.app_id = app_id
        self.app_secret = app_secret
        self.doc_token = doc_token
        self._tok = None

    def _token(self):
        if self._tok:
            return self._tok
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        d = r.json()
        if d.get("code") != 0:
            raise RuntimeError(f"token 失败: {d}")
        self._tok = d["tenant_access_token"]
        return self._tok

    def _headers(self):
        return {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}

    def _post_children(self, parent_id, blocks, index=None):
        payload = {"children": blocks}
        if index is not None:
            payload["index"] = index
        r = requests.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}"
            f"/blocks/{parent_id}/children",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        d = r.json()
        if d.get("code") != 0:
            raise RuntimeError(f"写入失败: {d}")
        return d.get("data", {}).get("children", [])

    def _push(self, blocks):
        for blk in reversed(blocks):
            children = blk.pop("children", None)
            created = self._post_children(self.doc_token, [blk], index=0)
            if children and created:
                self._push_to(created[0]["block_id"], children)

    def _push_to(self, parent_id, blocks):
        pending_children = {}
        clean_blocks = []
        for j, blk in enumerate(blocks):
            children = blk.pop("children", None)
            clean_blocks.append(blk)
            if children:
                pending_children[j] = children
        created = self._post_children(parent_id, clean_blocks)
        for j, children in pending_children.items():
            if j < len(created):
                self._push_to(created[j]["block_id"], children)

    def write_weekly_report(self, official_items, github_items, reading_items, weekly_summary=""):
        now_bj = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        week_end = now_bj.strftime("%m.%d")
        week_start = (now_bj - datetime.timedelta(days=6)).strftime("%m.%d")
        B = []

        # 日期标题（周报范围）
        B.append(_h1([_el(f"🗞️ {week_start} - {week_end} 周报")]))

        # 本周深度分析
        if weekly_summary:
            B.extend(_analysis_blocks(weekly_summary))
        else:
            parts = []
            if official_items:
                parts.append(f"官方动态 {len(official_items)} 条")
            if github_items:
                parts.append(f"GitHub 热门 {len(github_items)} 个")
            if reading_items:
                parts.append(f"精读 {len(reading_items)} 篇")
            B.append(_h2([_el("🧠 本周深度分析")]))
            B.append(_text_blk([_el("本周收录：" + "、".join(parts) + "。")]))

        # 官方动态
        B.append(_h2([_el("🏛️ 本周官方动态")]))
        for source in ["Anthropic", "OpenAI", "DeepMind"]:
            items = [i for i in official_items if i.get("source") == source]
            if not items:
                B.append(_bullet([_el(f"{source} 今日无更新")]))
            else:
                for item in items:
                    B.append(_bullet(
                        elements=[_el(f"[{source}] {item['title']}", url=item["url"])],
                        sub_text=item.get("summary", ""),
                    ))

        # GitHub 热门
        B.append(_h2([_el("🔥 本周 GitHub 热门（AI）")]))
        if not github_items:
            B.append(_bullet([_el("今日无 AI 相关热门仓库")]))
        else:
            for g in github_items:
                stars = g.get("stars_today", "")
                B.append(_bullet(
                    elements=[
                        _el(g["title"], url=g["url"]),
                        _el(f"  {stars}"),
                    ],
                    sub_text=g.get("summary", ""),
                ))

        # 每周精读
        B.append(_h2([_el("📖 本周精读")]))
        for source in ["Simon Willison", "宝玉"]:
            items = [i for i in reading_items if i.get("source") == source]
            if not items:
                B.append(_bullet([_el(f"{source} 今日无更新")]))
            else:
                for item in items:
                    B.append(_bullet(
                        elements=[_el(item["title"], url=item["url"])],
                        sub_text=item.get("summary", ""),
                    ))

        B.append({"block_type": 22, "divider": {}})

        self._push(B)
        print(f"  ✅ 成功写入 {len(B)} 个块到飞书文档")
