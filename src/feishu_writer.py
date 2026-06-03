"""
飞书文档写入器
"""
import datetime, requests

def _run(text, url=""):
    """构造 text_run 元素"""
    tr = {"content": text}
    if url:
        tr["text_element_style"] = {"link": {"url": url}}
    return {"type": "text_run", "text_run": tr}

def _para(elements, btype=2):
    """构造段落/标题/列表块，不带任何 style"""
    names = {2: "paragraph", 3: "heading1", 4: "heading2", 12: "bullet"}
    return {"block_type": btype, names[btype]: {"elements": elements}}

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
        """分批写入，每批 ≤ 50 块"""
        for i in range(0, len(blocks), 50):
            batch = blocks[i:i+50]
            url = (f"https://open.feishu.cn/open-apis/docx/v1/documents"
                   f"/{self.doc_token}/blocks/{self.doc_token}/children")
            r = requests.post(url, headers=self._h(), json={"children": batch}, timeout=20)
            d = r.json()
            if d.get("code") != 0:
                # 打印完整错误帮助调试
                print(f"  ⚠️  批次 {i//50+1} 失败 code={d.get('code')}: {d.get('msg')}")
                print(f"  发送的第一块: {json.dumps(batch[0], ensure_ascii=False)}")
                raise RuntimeError(f"追加块失败: {d}")

    def write_daily_report(self, youtube_items, github_items, anthropic_items):
        today = datetime.date.today().strftime("%Y年%m月%d日")
        total = len(youtube_items) + len(github_items) + len(anthropic_items)
        B = []

        # 标题
        B.append(_para([_run(f"📰 {today} AI 资讯日报")], 3))
        B.append(_para([_run(
            f"YouTube {len(youtube_items)} | GitHub {len(github_items)} | "
            f"Anthropic {len(anthropic_items)} | 共 {total} 条")]))

        # YouTube
        if youtube_items:
            B.append(_para([_run("🎬 YouTube 新视频")], 4))
            for v in youtube_items:
                B.append(_para([
                    _run(f"【{v['channel']}】"),
                    _run(v["title"], url=v["url"]),
                    _run(f"  {v['published_at']}"),
                ], 12))
                if v.get("description"):
                    B.append(_para([_run(v["description"][:120])]))

        # GitHub
        if github_items:
            B.append(_para([_run("🔥 GitHub 今日热门")], 4))
            for g in github_items:
                lang = f"[{g['language']}] " if g.get("language") else ""
                B.append(_para([
                    _run(g["title"], url=g["url"]),
                    _run(f"  {lang}{g.get('stars_today','')}"),
                ], 12))
                if g.get("description"):
                    B.append(_para([_run(g["description"])]))

        # Anthropic
        if anthropic_items:
            B.append(_para([_run("🤖 Anthropic 动态")], 4))
            for a in anthropic_items:
                B.append(_para([
                    _run(f"[{a['source']}] "),
                    _run(a["title"], url=a["url"]),
                ], 12))
                if a.get("note"):
                    B.append(_para([_run(a["note"])]))

        # 分割线
        B.append({"block_type": 22, "divider": {}})

        self._push(B)
        print(f"  ✅ 写入 {len(B)} 个块完成")
