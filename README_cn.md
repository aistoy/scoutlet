# scoutlet

面向AI agent的极简本地搜索聚合工具，无API Key，无复杂依赖，兼容SearXNG 的200+搜索引擎生态，为本地Agent提供极强搜索能力。

基于 [SearXNG](https://github.com/searxng/searxng) 的引擎体系和结果聚合算法实现，仅保留核心引擎加载、并发请求、评分去重合并排序逻辑。
## 特性

- 仅 3 个核心依赖：`httpx`、`lxml`、`babel`
- 复用 SearXNG 的结果聚合算法（加权评分、hash 去重、合并、分组排序）
- 兼容 SearXNG engine 代码模式，拷贝后改 import 即可使用
- 提供 Python API 和 CLI 两种使用方式
- 内置 108 个引擎（general、news、images、videos、code、music、files、science、movies、social media 等）
- 支持 CDP 浏览器 fallback（绕过反爬），可选自动启动 headless Chrome
- 可选 TLS 指纹后端（`primp`），模拟真实浏览器 TLS 指纹
- 引擎健康监控 + AI 自动修复流水线（快照 → LLM 修复 → 自动 PR）

## 为什么选择 scoutlet

### 方案对比

当前 AI Agent 获取搜索能力主要有以下几种路径：

| | scoutlet | 搜索 API 服务 | SearXNG | 搜索+LLM 框架 |
|---|---|---|---|---|
| **代表** | - | Tavily、Exa、SerpAPI | [SearXNG](https://github.com/searxng/searxng) | [OpenDeepSearch](https://github.com/sentient-agi/OpenDeepSearch)、[MindSearch](https://github.com/InternLM/MindSearch) |
| **运行方式** | Python 库，直接嵌入 | 调用付费 API | 需部署 Web 服务 | 框架级，绑定 LLM |
| **外部依赖** | 无 | 需要 API Key | Flask + Docker | 特定 LLM + 搜索 API |
| **核心依赖** | 3 个（httpx/lxml/babel） | SDK 或 HTTP | 数十个 | 视框架而定 |
| **反爬策略** | CDP 三级降级 | 服务商处理 | 无 | 依赖外部 API |
| **引擎生态** | 兼容 SearXNG 引擎 | 固定引擎 | 200+ 引擎 | 固定引擎 |
| **结果质量** | 多引擎聚合评分 | 单引擎 | 多引擎聚合评分 | 视实现而定 |
| **成本** | 免费，本地运行 | 付费/有配额 | 免费但需服务器 | 免费 + LLM 费用 |

**scoutlet 的定位**：SearXNG 的搜索能力，以纯 Python 库形式直接嵌入 Agent或通过CLI/MCP服务，零外部服务、零 API Key、零部署。

### 特性

**1. 本地无服务的搜索聚合库**

与 SearXNG 共享引擎生态和聚合算法（加权评分、hash 去重、合并排序），但从 Web 服务变成了可嵌入的 Python 库。Agent 不需要额外部署任何东西，`pip install` 即用。

**2. CDP 三级降级反爬机制**

```
HTTP 请求 → 成功 → 返回结果
          → 失败（CAPTCHA/403/429）
          → headless Chrome 重试
              → 成功 → 返回结果
              → 被反爬拦截
              → 自动降级 headful Chrome 重试
```

- HTTP 被拦截 → 自动启动 headless Chrome 导航
- headless 也被拦截 → 自动降级为 headful Chrome（真实浏览器窗口）重试
- 多层反爬检测结果：引擎特定（Google sorry、Bing block）+ 通用反爬（Cloudflare、Akamai、PerimeterX）+ 页面结构检查

**3. 极轻量，3 个核心依赖**

仅 `httpx`、`lxml`、`babel`。对比 SearXNG 数十个服务端依赖，scoutlet 可以真正零配置运行在任何 Python 环境中。

**4. SearXNG 引擎兼容**

直接复用 SearXNG 庞大的引擎生态（200+），从 SearXNG 拷贝 engine 文件后改 import 即可使用，其他方案不具备这种引擎复用能力。

## 已适配引擎（108 个）

| 引擎 | 分类 | 说明 |
|------|------|------|
| google | general | Google Web 搜索 |
| google_images | images | Google 图片搜索 |
| google_videos | videos | Google 视频搜索 |
| google_news | news | Google 新闻搜索 |
| bing | general | Bing Web 搜索 |
| bing_images | images | Bing 图片搜索 |
| bing_videos | videos | Bing 视频搜索 |
| bing_news | news | Bing 新闻搜索 |
| brave | general, news, images, videos | Brave 搜索 |
| duckduckgo | general | DuckDuckGo HTML (no-JS) |
| duckduckgo_extra | images, videos, news | DuckDuckGo Extra 搜索 |
| yahoo | general | Yahoo 搜索 |
| qwant | general | Qwant 搜索 |
| baidu | general, images, it | 百度搜索 |
| sogou | general | 搜狗搜索 |
| sogou_wechat | news | 搜狗微信公众号文章 |
| quark | general, images | 夸克/神马搜索 |
| mwmbl | general | Mwmbl 搜索 |
| marginalia | general | Marginalia 搜索 |
| seznam | general | Seznam 搜索 |
| reddit | social media | Reddit 搜索 |
| hackernews | it, news | Hacker News 搜索 |
| stackexchange | it, q&a | Stack Exchange (StackOverflow) |
| wikipedia | general | Wikipedia 摘要 |
| unsplash | images | Unsplash 图片 |
| imgur | images | Imgur 图片 |
| wallhaven | images | Wallhaven 壁纸 |
| deezer | music | Deezer 音乐 |
| genius | music, lyrics | Genius 歌词 |
| bandcamp | music | Bandcamp 音乐 |
| vimeo | videos | Vimeo 视频 |
| invidious | videos | Invidious (YouTube 前端) |
| piped | videos | Piped (YouTube 前端) |
| github | it, repos | GitHub 仓库搜索 |
| github_code | code | GitHub 代码搜索 |
| gitlab | it, repos | GitLab 仓库搜索 |
| gitea | it, repos | Gitea/Forgejo 仓库搜索 |
| sourcehut | it, repos | SourceHut 仓库搜索 |
| npm | it, packages | NPM 包搜索 |
| docker_hub | it, packages | Docker Hub 镜像搜索 |
| crates | it, packages | Rust crates 搜索 |
| 1337x | files | 1337x 种子搜索 |
| nyaa | files | Nyaa 动漫种子搜索 |
| arxiv | science | arXiv 预印本 |
| crossref | science | Crossref 学术元数据 |
| openalex | science | OpenAlex 学术作品 |
| semantic_scholar | science | Semantic Scholar 论文 |
| pubmed | science | PubMed 生物医学文献 |
| pdbe | science | PDBe 蛋白质结构 |
| astrophysics_data_system | science | NASA ADS（需 API key） |
| scanr_structures | science | ScanR 法国研究机构 |
| artic | images | 芝加哥艺术学院藏品 |
| artstation | images | ArtStation 作品 |
| deviantart | images | DeviantArt |
| findthatmeme | images | FindThatMeme 表情包 |
| flickr | images | Flickr（需 API key） |
| flickr_noapi | images | Flickr（无 API key） |
| ipernity | images | Ipernity |
| loc | images | 美国国会图书馆照片 |
| openclipart | images | OpenClipArt 矢量图 |
| openverse | images | Openverse CC 媒体 |
| pexels | images | Pexels 图片 |
| pinterest | images | Pinterest |
| pixabay | images | Pixabay 媒体 |
| pixiv | images | Pixiv 插画 |
| public_domain_image_archive | images | Public Domain Image Archive |
| sogou_images | images | 搜狗图片 |
| 1x | images | 1x 摄影 |
| frinkiac | images | Frinkiac 辛普森一家截图 |
| emojipedia | （无分类 — 按名调用） | Emojipedia Emoji 参考 |
| 360search_videos | videos | 360Search 视频 |
| acfun | videos | Acfun 视频 |
| bitchute | videos | Bitchute 视频 |
| ccc_media | videos | media.ccc.de |
| dailymotion | videos | Dailymotion 视频 |
| digbt | videos, music, files | DigBT 种子 |
| ina | videos | INA（法国） |
| iqiyi | videos | 爱奇艺视频 |
| mediathekviewweb | videos | MediathekViewWeb（德国） |
| niconico | videos | Niconico 视频 |
| odysee | videos | Odysee 视频 |
| peertube | videos | Peertube 联邦视频 |
| rumble | videos | Rumble 视频 |
| sepiasearch | videos | SepiaSearch 联邦视频 |
| sogou_videos | videos | 搜狗视频 |
| tubearchivist | videos | Tube Archivist（自托管，需 base_url+token） |
| youtube_api | videos, music | YouTube Data API v3（需 API key） |
| youtube_noapi | videos, music | YouTube（无 API key） |
| mixcloud | music | Mixcloud |
| radio_browser | music, radio | Radio Browser 电台 |
| soundcloud | music | SoundCloud |
| spotify | music | Spotify（需 client credentials） |
| yandex_music | music | Yandex Music |
| imdb | movies | IMDB |
| moviepilot | movies | Moviepilot（德国） |
| rottentomatoes | movies | Rotten Tomatoes |
| senscritique | movies | SensCritique（法国） |
| 9gag | social media | 9GAG |
| lemmy | social media | Lemmy（Communities/Users/Posts/Comments） |
| mastodon | social media | Mastodon（accounts/hashtags） |
| mrs | social media | Matrix Rooms Search（需 base_url） |
| tootfinder | social media | Tootfinder（Mastodon 帖子） |
| ansa | news | Ansa（意大利） |
| il_post | news | Il Post（意大利） |
| reuters | news | Reuters |
| yahoo_news | news | Yahoo News |
| bilibili | videos | B站视频搜索 |

## 安装

```bash
pip install -e .

# 如需 CDP 浏览器自动启动功能
pip install -e ".[browser]"
```

需要 Python >= 3.10。

## 使用

### Python API

```python
from scoutlet import search_sync, search

# 同步搜索（脚本推荐）
results = search_sync("python tutorial", engines=["google", "bing"])

for r in results:
    print(f"[{','.join(r.engines)}] {r.title}")
    print(f"  {r.url}")
    print(f"  {r.content[:100]}")
    print(f"  score: {r.score:.2f}")

# 异步搜索（用于 async 程序）
results = await search("python tutorial", engines=["google", "bing"])

# 按分类搜索
results = search_sync("AI", categories=["general", "news"])

# 指定语言和时间范围
results = search_sync("最新新闻", language="zh", time_range="day")
```

### CLI

```bash
# 搜索
scoutlet "python tutorial" -e google,bing

# JSON 输出
scoutlet "python tutorial" -e google,bing -f json

# 指定语言、时间范围
scoutlet "最新新闻" -l zh -t day -e baidu,sogou

# 列出可用引擎
scoutlet --list-engines

# 按分类列出引擎
scoutlet --list-engines --by-category
```

## 代理和浏览器 Fallback

### HTTP 代理

支持通过 `proxy` 参数为所有引擎指定 HTTP/SOCKS5 代理：

```python
# HTTP 代理
results = search_sync("test", engines=["google"], proxy="http://127.0.0.1:7890")

# SOCKS5 代理（需安装：pip install httpx[socks]）
results = search_sync("test", engines=["google"], proxy="socks5://127.0.0.1:1080")
```

```bash
scoutlet "test" -e google --proxy http://127.0.0.1:7890
# SOCKS5 需安装：pip install httpx[socks]
scoutlet "test" -e google --proxy socks5://127.0.0.1:1080
```

### CDP 浏览器 Fallback（绕过反爬）

当引擎被 Google/DuckDuckGo 等反爬机制拦截（CAPTCHA、AccessDenied、429）时，自动通过 Chrome 浏览器重试。

**优势**：
- 复用用户已登录的浏览器会话（无需登录）
- 使用真实浏览器指纹，无法被检测为 bot
- 适用于所有引擎

**方式一：自动启动浏览器（推荐）**

无需手动启动 Chrome，程序会自动启动 headless 模式 Chrome。被反爬拦截时自动降级为 headful 重试。

```python
load_engines(engine_configs={
    "google": {
        "fallback_to_browser": True,
        "auto_launch_browser": True,   # 自动启动 Chrome（默认 headless）
    },
})

results = search_sync("test", engines=["google"])
```

需要安装浏览器依赖：

```bash
pip install -e ".[browser]"
```

CLI 也支持同样能力：

```bash
scoutlet "test" -e google --fallback-to-browser --auto-launch-browser
scoutlet "test" -e google --fallback-to-browser --auto-launch-browser --headful
scoutlet "test" -e google --fallback-to-browser --cdp-endpoint http://localhost:9333
```

`--auto-launch-browser` 会隐式启用 browser fallback。`--headful` 会使用可见浏览器窗口，而不是 headless 模式。

**方式二：手动启动 Chrome**

提前启动 Chrome 并开启远程调试端口：

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-profile

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile
```

```python
load_engines(engine_configs={
    "google": {"fallback_to_browser": True},
})

# HTTP 成功时走正常路径；失败时自动降级到 CDP
results = search_sync("test", engines=["google"])
```

**配置项**：

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `fallback_to_browser` | `False` | 启用 CDP 浏览器 fallback |
| `auto_launch_browser` | `False` | 自动启动 Chrome（需安装 `pychrome`） |
| `headless` | `True` | 默认 headless 模式，被拦截时自动降级 headful |
| `block_resources` | `True` | 拦截图片/字体/CSS 等资源加速加载 |
| `browser_args` | `None` | 自定义 Chrome 启动参数 |
| `cdp_endpoint` | `http://localhost:9222` | CDP 调试端点地址 |

**工作流程**：

```
HTTP 请求 → 成功 → 返回结果
          → 失败（CAPTCHA/403/429）
          → CDP fallback
              → headless Chrome 导航
                  → 正常页面 → 返回结果
                  → 被拦截 → 自动降级 headful 重试
```

### Google 引擎的特殊说明

Google 搜索通过 **移动端 GSA User-Agent**（Android Chrome）绕过 JS-only 页面返回传统 HTML。随着 Google 反爬策略变化，可能需要：

```bash
# 更新 GSA User-Agent 列表
python scripts/update_gsa_useragents.py
```

如果 GSA UA 也被封堵，启用 `fallback_to_browser=True` 通过用户 Chrome 重试。

## TLS 指纹 HTTP 后端（可选）

部分引擎会在 TLS 层检测爬虫（JA3/JA4 指纹、HTTP/2 设置）。scoutlet 提供可选的 `primp` 适配器，随机模拟真实浏览器（Chrome/Firefox/Safari）——TLS 密码套件、ALPN、HTTP/2 帧顺序、请求头顺序全部对齐真实浏览器，让请求在 TLS 层无法被识别。

```bash
pip install -e ".[fingerprint]"   # 安装 primp>=1.2.3
```

**按引擎启用**（推荐，只对需要的引擎启用）：

```python
load_engines(engine_configs={
    "duckduckgo": {"http_client": "fingerprint"},
    "google": {"http_client": "fingerprint"},
})

results = search_sync("test", engines=["google"])
```

**全局启用**（对所有引擎生效）：

```python
from scoutlet.network import set_adapter_backend

set_adapter_backend("fingerprint")
```

留空 `http_client` 或不设置，则使用默认的 `httpx` 后端。自定义适配器可通过 `scoutlet.client_adapter.register_adapter(name, cls)` 注册。

## 引擎健康监控与自动修复（Auto-Heal）

scoutlet 内置 CI 流水线（`.github/workflows/engine-health.yml`），每 6 小时对全部引擎做端到端探活，对失败进行分类，并触发 LLM 驱动的自动修复流程，在解析器失效时自动开出修复 PR。

流水线阶段：

1. **健康检查**（`scripts/health_check.py --all`）—— 对每个引擎执行真实搜索，状态分类为 `healthy` / `empty` / `anti_bot` / `http_error` / `parser_error` / `timeout`，输出 JSON 报告并保存失败 HTML 快照。
2. **快照管理**（`scripts/snapshot.py`）—— 并排保存 `baseline_*` 与 `failed_*` HTML，并提供最小化器去除 `<script>`/`<style>` 和大块内容以降低 LLM 输入成本。
3. **AI 修复代理**（`scripts/auto_heal.py`）—— 对每个解析失败：读取当前引擎源码 + 失败 HTML + baseline HTML，调用 OpenAI 兼容 LLM 重写 `response()` 解析器，然后做四道校验：禁用模式扫描、`ast.parse` 语法检查、fixture 回放、live 复测。
4. **PR 提交** —— 修复成功的引擎会被提交到 `auto-fix/<timestamp>` 分支，CI 自动开一个带 `auto-fix` 标签的 PR 等待人工 review。

CI Secrets 配置：

| Secret | 用途 |
|--------|------|
| `OPENAI_API_KEY` | LLM 服务商密钥 |
| `OPENAI_API_BASE` | OpenAI 兼容接口的 base URL |
| `OPENAI_MODEL` | 模型名（默认 `gpt-4o`） |

本地运行：

```bash
# 探活全部引擎并保存快照
uv run python scripts/health_check.py --all --output health-report.json --snapshots-dir snapshots

# 基于最新报告尝试修复
uv run python scripts/auto_heal.py --report health-report.json --snapshots-dir snapshots --dry-run
```

详见 [设计文档](docs/auto_heal_design.md)。

## 测试

共 473 个离线测试，分三类：

```bash
uv run pytest tests/unit/        # 核心逻辑：result types、aggregation、engine_loader、network、browser、CDP fallback、client_adapter、CLI
uv run pytest tests/engines/     # P0/P1 引擎 parser fixture 测试（已保存 HTML/JSON，无网络）
uv run pytest tests/             # 全部离线测试
```

依赖网络的 live smoke 测试通过 `pytest.mark.live` 标记，需设置 `SCOUTLET_LIVE=1` 才运行：

```bash
SCOUTLET_LIVE=1 uv run pytest tests/live/ -m live
```

CI（`.github/workflows/engine-health.yml`）每 6 小时跑 `compileall` + 离线测试 + 健康检查/auto-heal 流水线。

## TODO

- [ ] 同步更多 SearXNG 引擎，完全全部200+引擎移植测试, 定期同步 SearXNG 上游引擎更新
- [ ] 持续跟进 SearXNG 的反爬对抗策略（UA 更新、请求参数调整、新引擎适配等）
- [x] **Engine Auto-Heal** — 引擎自动健康监控与 AI 自修复系统
  - [x] 健康监控：定时对所有引擎进行端到端测试（`scripts/health_check.py` + CI 每 6 小时）
  - [x] HTML 快照：保存成功和失败时的 HTML 响应（`scripts/snapshot.py`）
  - [x] AI 修复 Agent：解析失败时调用 LLM 分析 HTML 结构变化并重写引擎解析代码（`scripts/auto_heal.py`）
  - [ ] 自动测试：完整沙箱验证 AI 生成代码（当前 CI 做 compileall + fixture 回放 + live 复测，独立沙箱仍待补）
  - [x] 自动提交：验证通过的修复代码通过 PR 提交（CI `auto-heal` job）
  - 详见 [设计文档](docs/auto_heal_design.md)
