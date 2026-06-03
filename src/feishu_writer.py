"""
飞书文档写入器 - 使用 Feishu Docs v1 Block API
"""
import datetime
import requests

BLOCK_TEXT     = 2
BLOCK_HEADING1 = 3
BLOCK_HEADING2 = 4
BLOCK_BULLET   = 12
BLOCK_DIVIDER  = 22

def _text_element(content: str, url: str = "") -> dict:
    style = {}
    if url:
        style["link"] = {"url": url}
    return {
        "type": "text_run",
        "text_run": {
            "content": content,
            "text_element_style": style
        }
    }

def _block(block_type: int, elements: list) -> dict:
    type_name_map = {
        BLOCK_TEXT:     "paragraph",
        BLOCK_HEADING1: "heading1",
        BLOCK_HEADING2: "heading2",
        BLOCK_BULLET:   "bullet",
    }
    type_name = type_name_map.get(block_type, "paragraph")
    return {
        "block_type": block_type,
        type_name: {"elements": elements, "style": {}}
    }

def _divider() -> dict:
    return {"block_type": BLOCK_DIVIDER}

class FeishuDocWriter:
    def __init__(self, app_id: str, app_secret: str, doc_token: str):
        self.app_id     = app_id
        self.app_secret = app_secret
        self.doc_token  = doc_token
        self._token     = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书 token 失败: {data}")
        self._token = data["tenant_access_token"]
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json"
        }

    def _get_root_block_id(self) -> str:
        """获取文档根块 ID"""
        resp = requests.get(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}/blocks",
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取文档块失败: {data}")
        # 第一个块就是根块（Page 类型）
        items = data.get("data", {}).get("items", [])
        if not items:
            raise RuntimeError("文档没有找到任何块")
        return items[0]["block_id"]

    def _append_blocks(self, parent_block_id: str, blocks: list) -> None:
        """向 parent_block_id 末尾追加子块（每次最多 50 个）"""
        batch_size = 50
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i: i + batch_size]
            resp = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}"
                f"/blocks/{parent_block_id}/children/batch_update",
                headers=self._headers(),
                json={"requests": [
                    {
                        "insert_children": {
                            "parent_block_id": parent_block_id,
                            "children": batch,
                        }
                    }
                ]},
                timeout=15,
            )
            data = resp.json()
            if data.get("code") != 0:
                # 回退到简单 append 方式
                resp2 = requests.post(
                    f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}"
                    f"/blocks/{parent_block_id}/children",
                    headers=self._headers(),
                    json={"children": batch},
                    timeout=15,
                )
                data2 = resp2.json()
                if data2.get("code") != 0:
                    raise RuntimeError(f"追加块失败: {data2}")

    def write_daily_report(self, youtube_items, github_items, anthropic_items) -> None:
        today = datetime.date.today().strftime("%Y年%m月%d日")
        total = len(youtube_items) + len(github_items) + len(anthropic_items)
        blocks = []

        blocks.append(_block(BLOCK_HEADING1, [_text_element(f"📰 {today} AI 资讯日报")]))
        blocks.append(_block(BLOCK_TEXT, [_text_element(
            f"自动抓取 | YouTube {len(youtube_items)} 条 | "
            f"GitHub {len(github_items)} 条 | Anthropic {len(anthropic_items)} 条 | 共 {total} 条"
        )]))

        if youtube_items:
            blocks.append(_block(BLOCK_HEADING2, [_text_element("🎬 YouTube 新视频")]))
            for item in youtube_items:
                blocks.append(_block(BLOCK_BULLET, [
                    _text_element(f"【{item['channel']}】"),
                    _text_element(item["title"], url=item["url"]),
                    _text_element(f"  ({item['published_at']})"),
                ]))
                if item.get("description"):
                    blocks.append(_block(BLOCK_TEXT, [
                        _text_element(f"    {item['description'][:150]}")
                    ]))

        if github_items:
            blocks.append(_block(BLOCK_HEADING2, [_text_element("🔥 GitHub 今日热门")]))
            for item in github_items:
                lang = f"[{item['language']}]" if item.get("language") else ""
                blocks.append(_block(BLOCK_BULLET, [
                    _text_element(item["title"], url=item["url"]),
                    _text_element(f"  {lang} {item.get('stars_today', '')}"),
                ]))
                if item.get("description"):
                    blocks.append(_block(BLOCK_TEXT, [
                        _text_element(f"    {item['description']}")
                    ]))

        if anthropic_items:
            blocks.append(_block(BLOCK_HEADING2, [_text_element("🤖 Anthropic 动态")]))
            for item in anthropic_items:
                blocks.append(_block(BLOCK_BULLET, [
                    _text_element(f"[{item['source']}] "),
                    _text_element(item["title"], url=item["url"]),
                ]))
                if item.get("note"):
                    blocks.append(_block(BLOCK_TEXT, [
                        _text_element(f"    {item['note']}")
                    ]))

        blocks.append(_divider())

        root_id = self._get_root_block_id()
        self._append_blocks(root_id, blocks)
        print(f"  ✅ 成功写入 {len(blocks)} 个块到飞书文档")
