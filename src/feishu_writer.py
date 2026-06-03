"""
飞书文档写入器 - Feishu Docs v1 Block API（简洁版）
"""
import datetime
import requests

BLOCK_TEXT     = 2
BLOCK_HEADING1 = 3
BLOCK_HEADING2 = 4
BLOCK_BULLET   = 12
BLOCK_DIVIDER  = 22

def _el(text: str, url: str = "") -> dict:
    style = {"link": {"url": url}} if url else {}
    return {"type": "text_run", "text_run": {"content": text, "text_element_style": style}}

def _blk(btype: int, elements: list) -> dict:
    names = {2: "paragraph", 3: "heading1", 4: "heading2", 12: "bullet"}
    name = names.get(btype, "paragraph")
    return {"block_type": btype, name: {"elements": elements, "style": {}}}

class FeishuDocWriter:
    def __init__(self, app_id, app_secret, doc_token):
        self.app_id = app_id
        self.app_secret = app_secret
        self.doc_token = doc_token
        self._token = None

    def _get_token(self):
        if self._token:
            return self._token
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret}, timeout=10
        )
        d = r.json()
        if d.get("code") != 0:
            raise RuntimeError(f"token 获取失败: {d}")
        self._token = d["tenant_access_token"]
        return self._token

    def _hdrs(self):
        return {"Authorization": f"Bearer {self._get_token()}", "Content-Type": "application/json"}

    def _append(self, blocks):
        """分批追加块到文档末尾（doc_token 就是根块 ID）"""
        for i in range(0, len(blocks), 50):
            batch = blocks[i:i+50]
            r = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}"
                f"/blocks/{self.doc_token}/children",
                headers=self._hdrs(),
                json={"children": batch},
                timeout=20
            )
            d = r.json()
            if d.get("code") != 0:
                raise RuntimeError(f"追加块失败: {d}")

    def write_daily_report(self, youtube_items, github_items, anthropic_items):
        today = datetime.date.today().strftime("%Y年%m月%d日")
        total = len(youtube_items) + len(github_items) + len(anthropic_items)
        blocks = []

        blocks.append(_blk(BLOCK_HEADING1, [_el(f"📰 {today} AI 资讯日报")]))
        blocks.append(_blk(BLOCK_TEXT, [_el(
            f"YouTube {len(youtube_items)} 条 | GitHub {len(github_items)} 条 | Anthropic {len(anthropic_items)} 条 | 共 {total} 条"
        )]))

        if youtube_items:
            blocks.append(_blk(BLOCK_HEADING2, [_el("🎬 YouTube 新视频")]))
            for item in youtube_items:
                blocks.append(_blk(BLOCK_BULLET, [
                    _el(f"【{item['channel']}】"),
                    _el(item["title"], url=item["url"]),
                    _el(f"  ({item['published_at']})"),
                ]))
                if item.get("description"):
                    blocks.append(_blk(BLOCK_TEXT, [_el(f"    {item['description'][:150]}")]))

        if github_items:
            blocks.append(_blk(BLOCK_HEADING2, [_el("🔥 GitHub 今日热门")]))
            for item in github_items:
                lang = f"[{item['language']}]" if item.get("language") else ""
                blocks.append(_blk(BLOCK_BULLET, [
                    _el(item["title"], url=item["url"]),
                    _el(f"  {lang} {item.get('stars_today', '')}"),
                ]))
                if item.get("description"):
                    blocks.append(_blk(BLOCK_TEXT, [_el(f"    {item['description']}")]))

        if anthropic_items:
            blocks.append(_blk(BLOCK_HEADING2, [_el("🤖 Anthropic 动态")]))
            for item in anthropic_items:
                blocks.append(_blk(BLOCK_BULLET, [
                    _el(f"[{item['source']}] "),
                    _el(item["title"], url=item["url"]),
                ]))
                if item.get("note"):
                    blocks.append(_blk(BLOCK_TEXT, [_el(f"    {item['note']}")]))

        blocks.append({"block_type": BLOCK_DIVIDER})

        self._append(blocks)
        print(f"  ✅ 成功写入 {len(blocks)} 个块到飞书文档")
