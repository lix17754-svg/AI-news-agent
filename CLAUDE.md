# AI 资讯日报 Agent

## 项目简介
每天北京时间 09:00 自动抓取 YouTube / GitHub Trending / Anthropic 最新动态，写入飞书文档。

## 文件结构
```
├── src/
│   ├── main.py               # 主入口，读取环境变量，串联所有爬虫和写入
│   ├── youtube_crawler.py    # YouTube 订阅频道新视频（YouTube Data API v3）
│   ├── github_crawler.py     # GitHub 每日 Trending Top 10（网页抓取）
│   ├── anthropic_crawler.py  # Anthropic 官网博客 + GitHub 动态（网页抓取）
│   └── feishu_writer.py      # 飞书文档写入（Feishu Docs v1 Block API）
├── .github/workflows/
│   └── daily.yml             # GitHub Actions 定时任务（每天 UTC 01:00）
├── requirements.txt
└── CLAUDE.md                 # 本文件
```

## 本地运行
```bash
pip install -r requirements.txt

export FEISHU_APP_ID=cli_aa9520784bfb1ce3
export FEISHU_APP_SECRET=你的新Secret
export FEISHU_DOC_TOKEN=MNyCdUNQ1oqKxXxdLe7csuXGnlh
export YOUTUBE_API_KEY=你的YouTubeKey

cd src && python main.py
```

## GitHub Secrets（GitHub Actions 用）
| 名字 | 说明 |
|------|------|
| `FEISHU_APP_ID` | 飞书自建应用 App ID |
| `FEISHU_APP_SECRET` | 飞书自建应用 App Secret |
| `FEISHU_DOC_TOKEN` | 飞书文档 Token（URL 最后一段） |
| `YOUTUBE_API_KEY` | Google Cloud Console 申请的 YouTube Data API v3 Key |

## 修改 YouTube 频道
编辑 `src/youtube_crawler.py` 的 `YOUTUBE_CHANNELS` 列表：
```python
{"name": "显示名", "handle": "频道handle（不含@）"}
```

## 飞书文档 API 关键知识（踩过的坑）

### ⚠️ block_type=2 的字段名是 "text"，不是 "paragraph"！
```python
# ✅ 正确
{"block_type": 2, "text": {"elements": [...], "style": {"align": 1}}}

# ❌ 错误（会报 1770001 invalid param）
{"block_type": 2, "paragraph": {"elements": [...]}}
```

### 块类型映射
| block_type | 字段名 | 说明 |
|------------|--------|------|
| 1 | page | 文档根块（不需要创建） |
| 2 | text | 普通段落 |
| 3 | heading1 | 一级标题 |
| 4 | heading2 | 二级标题 |
| 12 | bullet | 无序列表项 |
| 22 | divider | 分割线 `{"block_type": 22, "divider": {}}` |

### 文本元素格式
```python
# 普通文本
{"text_run": {"content": "文字", "text_element_style": {}}}

# 带超链接
{"text_run": {"content": "文字", "text_element_style": {"link": {"url": "https://..."}}}}
```

### 认证（tenant_access_token）
```python
r = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
)
token = r.json()["tenant_access_token"]
```

### 写入文档
```python
# doc_token 既是文档ID也是根块ID
requests.post(
    f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={"children": [block1, block2, ...]}
)
```

## 飞书应用配置
- 应用名：O.o爬虫
- App ID：cli_aa9520784bfb1ce3
- 所需权限：`docx:document:write_only`（应用身份）
- 文档权限：洋葱学园组织内所有人可搜索和编辑

## 常见问题
- **1770001 invalid param**：99% 是块字段名写错了，检查是否用了 `"paragraph"` 而不是 `"text"`
- **10014 app secret invalid**：App Secret 填错，去飞书开放平台重置后更新 GitHub Secrets
- **YouTube 找不到频道**：检查 handle 是否正确（不含 @），部分频道 handle 与显示名不同

## 当前进度
_最后更新：2026-06-04_

### ✅ 已完成
- 完整 Agent 搭建：YouTube / GitHub Trending / Anthropic 三路爬虫 + 飞书文档写入
- GitHub Actions 每日自动触发，**定时改为 UTC 23:50（北京时间 07:50）**，在 GitHub Trending 重置前抓完整日榜
- **新增 `src/ai_summarizer.py`**：接入 Google Gemini 2.0 Flash，一次 API 调用批量生成每条摘要 + 每日总结，写回各 item 的 `summary` 字段
- **重写 `src/feishu_writer.py`** 排版：
  - 版块顺序改为 Anthropic → GitHub → YouTube
  - 日期标题改为 `🗞️ MM.DD`（heading1，北京时间）
  - 顶部总结框用 quote 块（block_type=15）+ 💥 emoji 模拟
  - 每条内容：一级 bullet + 子级 bullet 放 AI 摘要
  - 新内容插入文档**顶部**（`index=0`），最新日期始终在最上面
- **更新 `src/anthropic_crawler.py`**：GitHub 仓库过滤为 7 天内有更新的，避免展示老仓库
- **更新 `src/main.py`**：串联 AI 摘要流程，爬取完成后调用 `enrich_with_summaries`
- **依赖替换**：`google-generativeai`（已废弃）→ `google-genai>=1.0.0`
- 所有 GitHub Secrets 已配置：`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_DOC_TOKEN` / `YOUTUBE_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`（备用）
- 代码已 push 到 https://github.com/lix17754-svg/AI-news-agent

### 🔜 下一步（按优先级）
- **明天早上 07:50 等待第一次完整自动运行**，去飞书文档验证：AI 摘要是否正常生成、排版是否符合预期
- **Anthropic 博客标题清洗**：部分条目标题格式混乱（如 `Jun 3, 2026AnnouncementsXXX`），需改进 `_get_anthropic_blog` 的 title 提取逻辑
- **飞书 callout 橙色框**：目前用 quote 块（竖线样式）代替，飞书 callout（block_type=34）API 参数未公开，后续可尝试研究或找飞书官方文档

### ⚠️ 注意事项 / 踩过的坑
- **飞书嵌套块不能内联创建**：`children` 字段放在块定义里会报 9499 错误。正确做法：先 POST 父块拿到 `block_id`，再 POST children 到该 `block_id`。已在 `_push` / `_push_to` 方法中实现
- **飞书 block_type=34（callout）不可用**：尝试多次均报 1770001，暂用 block_type=15（quote）替代
- **飞书 index=0 插入顶部**：在 `_post_children` 的 payload 加 `"index": 0` 即可将新内容插入文档最顶部；子块不需要加 index
- **倒序逐块插入**：因为每块都用 `index=0`，需要 `reversed(blocks)` 倒序插入，否则顺序会颠倒
- **google-generativeai 已废弃**：升级后会报 FutureWarning，且旧模型名（gemini-1.5-flash 等）在 v1beta 接口下 404。必须换用 `google-genai` 包，`from google import genai`，用 `client.models.generate_content(model="gemini-2.0-flash", ...)`
- **Gemini 免费 tier 每分钟限速**：本地多次测试会触发 429，重试间隔设为 35s/70s。生产环境每天只跑一次，不会触发
- **GitHub Actions push workflow 文件需要 workflow scope**：普通 PAT 无法 push `.github/workflows/` 下的文件，需在 GitHub 网页端直接编辑 daily.yml
- 排版改动只改 `feishu_writer.py`，不要动爬虫逻辑；数据结构保持向后兼容
- 飞书 block 写入改为插入顶部（index=0），每次新内容在最上面
