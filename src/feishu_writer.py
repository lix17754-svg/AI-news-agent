"""
飞书文档写入器 - 带完整诊断输出
"""
import datetime, json, requests

def _run(text, url=""):
    tr = {"content": text}
    if url:
        tr["text_element_style"] = {"link": {"url": url}}
    return {"type": "text_run", "text_run": tr}

def _para(elements, btype=2):
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
        print(f"  ✅ Token 获取成功")
        return self._tok

    def _h(self):
        return {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}

    def _diagnose(self):
        """诊断：检查文档是否可访问，并获取根块 ID"""
        # 1. 获取文档信息
        r = requests.get(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}",
            headers=self._h(), timeout=10)
        d = r.json()
        print(f"  📄 文档信息: code={d.get('code')} msg={d.get('msg')}")
        if d.get("code") != 0:
            raise RuntimeError(f"无法访问文档: {d}")

        # 2. 尝试写入最简单的一个块
        test = {"block_type": 2, "paragraph": {"elements": [
            {"type": "text_run", "text_run": {"content": "🤖 AI 日报测试"}}
        ]}}
        print(f"  🧪 测试块内容: {json.dumps(test, ensure_ascii=False)}")
        url = (f"https://open.feishu.cn/open-apis/docx/v1/documents"
               f"/{self.doc_token}/blocks/{self.doc_token}/children")
        r2 = requests.post(url, headers=self._h(), json={"children": [test]}, timeout=10)
        d2 = r2.json()
        print(f"  🧪 测试块结果: code={d2.get('code')} msg={d2.get('msg')}")
        if d2.get("code") != 0:
            print(f"  🔍 完整错误: {json.dumps(d2, ensure_ascii=False)[:500]}")
            raise RuntimeError(f"测试块失败: {d2.get('msg')}")
        print(f"  ✅ 测试块写入成功！")

    def _push(self, blocks):
        for i in range(0, len(blocks), 50):
            batch = blocks[i:i+50]
            url = (f"https://open.feishu.cn/open-apis/docx/v1/documents"
                   f"/{self.doc_token}/blocks/{self.doc_token}/children")
            r = requests.post(url, headers=self._h(), json={"children": batch}, timeout=20)
            d = r.json()
            if d.get("code") != 0:
                print(f"  ❌ 批次失败: {json.dumps(d, ensure_ascii=False)[:300]}")
                raise RuntimeError(f"追加块失败: {d.get('msg')}")

    def write_daily_report(self, youtube_items, github_items, anthropic_items):
        # 先跑诊断
        self._diagnose()

        today = datetime.date.today().strftime("%Y年%m月%d日")
        total = len(youtube_items) + len(github_items) + len(anthropic_items)
        B = []

        B.append(_para([_run(f"📰 {today} AI 资讯日报")], 3))
        B.append(_para([_run(
            f"YouTube {len(youtube_items)} | GitHub {len(github_items)} | "
            f"Anthropic {len(anthropic_items)} | 共 {total} 条")]))

        if youtube_items:
            B.append(_para([_run("🎬 YouTube 新视频")], 4))
            for v in youtube_items:
                B.append(_para([
                    _run(f"【{v['channel']}】"),
                    _run(v["title"], url=v["url"]),
                    _run(f"  {v['published_at']}"),
                ], 12))

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

        if anthropic_items:
            B.append(_para([_run("🤖 Anthropic 动态")], 4))
            for a in anthropic_items:
                B.append(_para([
                    _run(f"[{a['source']}] "),
                    _run(a["title"], url=a["url"]),
                ], 12))

        B.append({"block_type": 22, "divider": {}})

        self._push(B)
        print(f"  ✅ 完整日报写入 {len(B)} 块")
