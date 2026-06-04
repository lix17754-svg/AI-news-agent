"""
飞书文档写入器 - 排版优化版
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
    """一级 bullet；sub_text 非空时带一个子级缩进 bullet"""
    blk = {"block_type": 12, "bullet": {"elements": elements, "style": {"align": 1}}}
    if sub_text:
        blk["children"] = [
            {"block_type": 12, "bullet": {"elements": [_el(sub_text)], "style": {"align": 1}}}
        ]
    return blk


def _callout(summary_text):
    """用 quote 块（block_type=15）模拟总结框，飞书 callout API 块类型未公开"""
    return {
        "block_type": 15,
        "quote": {
            "elements": [
                _el("💥 总结：", bold=True),
                _el("  " + summary_text),
            ],
            "style": {"align": 1},
        },
    }


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
        """向指定父块写入 blocks，返回创建后的块列表（含 block_id）"""
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
        """逐块写入文档顶部（index=0）；有 children 的块先创建父块，再递归写入子块"""
        # 倒序逐块插入到 index=0，保证最终顺序正确
        for blk in reversed(blocks):
            children = blk.pop("children", None)
            created = self._post_children(self.doc_token, [blk], index=0)
            if children and created:
                self._push_to(created[0]["block_id"], children)

    def _push_to(self, parent_id, blocks):
        """递归向任意父块写入子块（顺序追加）"""
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

    def write_daily_report(self, youtube_items, github_items, anthropic_items, daily_summary=""):
        # 用北京时间（UTC+8）作为报告日期
        today = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%m.%d")
        B = []

        # 日期标题
        B.append(_h1([_el(f"🗞️ {today}")]))

        # 总结 callout
        if not daily_summary:
            parts = []
            if anthropic_items:
                parts.append(f"Anthropic {len(anthropic_items)} 条动态")
            if github_items:
                parts.append(f"GitHub 热门 {len(github_items)} 个项目")
            if youtube_items:
                parts.append(f"YouTube {len(youtube_items)} 个新视频")
            daily_summary = "今日收录：" + "、".join(parts) + "。"
        B.append(_callout(daily_summary))

        # Anthropic 动态
        if anthropic_items:
            B.append(_h2([_el("🤖 Anthropic 动态")]))
            for a in anthropic_items:
                B.append(_bullet(
                    elements=[_el(a["title"], url=a["url"])],
                    sub_text=a.get("summary", ""),
                ))

        # GitHub 今日热门
        if github_items:
            B.append(_h2([_el("🔥 GitHub 今日热门")]))
            for g in github_items:
                stars = g.get("stars_today", "")
                B.append(_bullet(
                    elements=[
                        _el(g["title"], url=g["url"]),
                        _el(f"  {stars}"),
                    ],
                    sub_text=g.get("summary", ""),
                ))

        # YouTube 新视频
        if youtube_items:
            B.append(_h2([_el("🎬 YouTube 新视频")]))
            for v in youtube_items:
                date_str = v.get("published_at", "")[5:]  # YYYY-MM-DD → MM-DD
                B.append(_bullet(
                    elements=[
                        _el(f"【{v['channel']}】"),
                        _el(v["title"], url=v["url"]),
                        _el(f"  ({date_str})"),
                    ],
                    sub_text=v.get("summary", ""),
                ))

        B.append({"block_type": 22, "divider": {}})

        self._push(B)
        print(f"  ✅ 成功写入 {len(B)} 个块到飞书文档")
