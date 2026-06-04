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
_最后更新：2026-06-03_

### ✅ 已完成
- 完整 Agent 搭建：YouTube / GitHub Trending / Anthropic 三路爬虫 + 飞书文档写入
- GitHub Actions 每日自动触发（UTC 01:00 = 北京时间 09:00）
- 飞书 Block API 基础用法已打通，常见坑已归档

### 🔜 下一步（按优先级）
- **优化飞书文档排版美观度**：按用户定义的逻辑重新组织每次写入的版式
  - 需先与用户确认具体排版逻辑（层级结构、标题样式、分割线使用规则、emoji 装饰等）
  - 然后改写 `src/feishu_writer.py`，统一封装排版函数
  - 验证：本地 `python main.py` 后人工检查飞书文档视觉效果

### ⚠️ 注意事项 / 踩过的坑
- 排版改动只改 `feishu_writer.py`，不要动爬虫逻辑；数据结构保持向后兼容
- 飞书 block 写入是追加模式，每次运行会在文档末尾插入新内容，排版需整体考虑"每日一节"的分隔方式
