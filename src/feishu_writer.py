"""
飞书文档写入器 - 先查根块 ID 再写入
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
        return self._tok

    def _h(self):
        return {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}

    def _get_root_block_id(self):
        """查询文档所有块，取第一个（根块）的 block_id"""
        r = requests.get(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{self.doc_token}/blocks",
            headers=self._h(), params={"page_size": 10}, timeout=10)
        d = r.json()
        print(f"  📦 块列表: code={d.get('code')} msg={d.get('msg')}")
        if d.get("code") != 0:
            print(f"  🔍 完整响应: {json.dumps(d, ensure_ascii=False)[:500]}")
            # 回退：用 doc_token 本身
            return self.doc_token
        items = d.get("data", {}).get("items", [])
        if items:
            root_id = items[0]["block_id"]
            root_type = items[0].get("block_type")
            print(f"  🌳 根块 ID: {root_id}  类型: {root_type}")
            # 打印所有块 ID 帮助排查
            for blk in items[:5]:
                print(f"     block_id={blk['block_id']} type={blk.get('block_type')}")
            return root_id
        print("  ⚠️  没找到块，使用 doc_token")
        return self.doc_token

    def _push(self, parent_id, blocks):
        for i in range(0, len(blocks), 50):
            batch = blocks[i:i+50]
            url = (f"https://open.feishu.cn/open-apis/docx/v1/documents"
                   f"/{self.doc_token}/blocks/{parent_id}/children")
            print(f"  📤 POST {url}")
            r = requests.post(url, headers=self._h(), json={"children": batch}, timeout=20)
            d = r.json()
            if d.get("code") != 0:
                print(f"  ❌ 失败: {json.dumps(d, ensure_ascii=False)[:400]}")
                raise RuntimeError(f"追加块失败: {d.get('msg')}")
            print(f"  ✅ 批次 {i//50+1} 成功写入 {len(batch)} 块")

    def write_daily_report(self, youtube_items, github_items, anthropic_items):
        root_id = self._get_root_block_id()
        today = datetime.date.today().strftime("%Y年%m月%d日")
        total = len(youtube_items) + len(github_items) + len(anthropic_items)
        B = []

        B.append(_para([_run(f"AI {today} 日报")], 3))
        B.append(_para([_run(
            f"YouTube {len(youtube_items)} | GitHub {len(github_items)} | "
            f"Anthropic {len(anthropic_items)} | total {total}")]))

        if youtube_items:
            B.append(_para([_run("YouTube 新视频")], 4))
            for v in youtube_items:
                B.append(_para([
                    _run(f"{v['channel']}: "),
                    _run(v["title"], url=v["url"]),
                ], 12))

        if github_items:
            B.append(_para([_run("GitHub 今日热门")], 4))
            for g in github_items[:5]:
                B.append(_para([
                    _run(g["title"], url=g["url"]),
                    _run(f"  {g.get('stars_today','')}"),
                ], 12))

        if anthropic_items:
            B.append(_para([_run("Anthropic 动态")], 4))
            for a in anthropic_items[:5]:
                B.append(_para([
                    _run(f"{a['source']}: "),
                    _run(a["title"], url=a["url"]),
                ], 12))

        B.append({"block_type": 22, "divider": {}})
        self._push(root_id, B)
        print(f"  ✅ 写入 {len(B)} 块完成")
