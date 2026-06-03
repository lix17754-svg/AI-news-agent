"""
飞书文档写入器 - 正确版
关键：block_type=2 的字段名是 "text"，不是 "paragraph"
"""
import datetime, requests

def _el(text, url=""):
    """构造文本元素"""
    style = {}
    if url:
        style["link"] = {"url": url}
    return {"text_run": {"content": text, "text_element_style": style}}

def _blk(btype, elements):
    """构造块，不同 block_type 对应不同字段名"""
    names = {2: "text", 3: "heading1", 4: "heading2", 12: "bullet"}
    return {"block_type": btype, names[btype]: {"elements": elements, "style": {"align": 1}}}

class FeishuDocWriter:
    def __init__(self, app_id, app_secret, doc_token):
        self.app_id = app_id
        self.app_secret = app_secret
        self.doc_token = doc_token
        self._tok = None

    def _token(self):
        if self._tok: return self._tok
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret}, timeout=10)
        d = r.json()
        if d.get("code") != 0:
            raise RuntimeError(f"token 失败: {d}")
        self._tok = d["tenant_access_token"]
        return self._tok

    def _h(self):
        return {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}

    def _push(self, blocks):
        for i in range(0, len(blocks), 50):
            batch = blocks[i:i+50]
            r = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}"
                f"/blocks/{self.doc_token}/children",
                headers=self._h(), json={"children": batch}, timeout=20)
            d = r.json()
            if d.get("code") != 0:
                raise RuntimeError(f"写入失败: {d}")

    def write_daily_report(self, youtube_items, github_items, anthropic_items):
        today = datetime.date.today().strftime("%Y年%m月%d日")
        total = len(youtube_items) + len(github_items) + len(anthropic_items)
        B = []

        B.append(_blk(3, [_el(f"📰 {today} AI 资讯日报")]))
        B.append(_blk(2, [_el(
            f"YouTube {len(youtube_items)} | GitHub {len(github_items)} | "
            f"Anthropic {len(anthropic_items)} | 共 {total} 条")]))

        if youtube_items:
            B.append(_blk(4, [_el("🎬 YouTube 新视频")]))
            for v in youtube_items:
                B.append(_blk(12, [
                    _el(f"【{v['channel']}】"),
                    _el(v["title"], url=v["url"]),
                    _el(f"  ({v['published_at']})"),
                ]))
                if v.get("description"):
                    B.append(_blk(2, [_el(v["description"][:150])]))

        if github_items:
            B.append(_blk(4, [_el("🔥 GitHub 今日热门")]))
            for g in github_items:
                lang = f"[{g['language']}] " if g.get("language") else ""
                B.append(_blk(12, [
                    _el(g["title"], url=g["url"]),
                    _el(f"  {lang}{g.get('stars_today','')}"),
                ]))
                if g.get("description"):
                    B.append(_blk(2, [_el(g["description"])]))

        if anthropic_items:
            B.append(_blk(4, [_el("🤖 Anthropic 动态")]))
            for a in anthropic_items:
                B.append(_blk(12, [
                    _el(f"[{a['source']}] "),
                    _el(a["title"], url=a["url"]),
                ]))
                if a.get("note"):
                    B.append(_blk(2, [_el(a["note"])]))

        B.append({"block_type": 22, "divider": {}})

        self._push(B)
        print(f"  ✅ 成功写入 {len(B)} 个块到飞书文档")
