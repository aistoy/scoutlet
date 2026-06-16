# scoutlet

A minimalist local search aggregation tool for AI agents — no API keys, no heavy dependencies, compatible with SearXNG's 200+ search engine ecosystem, delivering powerful search capabilities to local agents.

Based on [SearXNG](https://github.com/searxng/searxng)'s engine system and result aggregation algorithm, retaining only the core engine loading, concurrent requests, scoring, deduplication, merging, and sorting logic.

## Features

- Only 3 core dependencies: `httpx`, `lxml`, `babel`
- Reuses SearXNG's result aggregation algorithm (weighted scoring, hash dedup, merge, group sorting)
- Compatible with SearXNG engine code patterns — copy and change imports to use
- Python API and CLI interfaces
- 106 built-in engines (general, news, images, videos, code, music, files, science, movies, social media, and more)
- CDP browser fallback (bypass anti-bot), with optional auto-launch headless Chrome
- Optional TLS fingerprint backend (`primp`) for browser-grade TLS impersonation
- Engine health monitoring + AI auto-heal pipeline (snapshots → LLM repair → PR)

## Why scoutlet

### Comparison

There are several approaches for AI agents to acquire search capabilities:

| | scoutlet | Search API Services | SearXNG | Search + LLM Frameworks |
|---|---|---|---|---|
| **Examples** | - | Tavily, Exa, SerpAPI | [SearXNG](https://github.com/searxng/searxng) | [OpenDeepSearch](https://github.com/sentient-agi/OpenDeepSearch), [MindSearch](https://github.com/InternLM/MindSearch) |
| **Runtime** | Python library, embed directly | Call paid APIs | Requires web service deployment | Framework-level, tied to LLM |
| **Dependencies** | None | Requires API Key | Flask + Docker | Specific LLM + search API |
| **Core deps** | 3 (httpx/lxml/babel) | SDK or HTTP | Dozens | Varies |
| **Anti-bot** | CDP 3-tier fallback | Handled by provider | None | Depends on external API |
| **Engine ecosystem** | Compatible with SearXNG engines | Fixed engines | 200+ engines | Fixed engines |
| **Result quality** | Multi-engine aggregated scoring | Single engine | Multi-engine aggregated scoring | Varies |
| **Cost** | Free, runs locally | Paid / rate-limited | Free but requires server | Free + LLM costs |

**scoutlet's positioning**: SearXNG's search capabilities, delivered as a pure Python library that embeds directly into agents or via CLI/MCP service — zero external services, zero API keys, zero deployment.

### Highlights

**1. Local, service-free search aggregation library**

Shares SearXNG's engine ecosystem and aggregation algorithm (weighted scoring, hash dedup, merge/sort), but transforms from a web service into an embeddable Python library. No deployment needed — `pip install` and go.

**2. CDP 3-tier anti-bot fallback**

```
HTTP request → success → return results
             → failed (CAPTCHA/403/429)
             → headless Chrome retry
                 → success → return results
                 → blocked by anti-bot
                 → auto-downgrade to headful Chrome retry
```

- HTTP blocked → auto-launch headless Chrome for navigation
- Headless also blocked → auto-downgrade to headful Chrome (real browser window) retry
- Multi-layer anti-bot detection: engine-specific (Google sorry, Bing block) + generic anti-bot (Cloudflare, Akamai, PerimeterX) + page structure checks

**3. Ultra-lightweight, 3 core dependencies**

Only `httpx`, `lxml`, `babel`. Compared to SearXNG's dozens of server-side dependencies, scoutlet runs truly zero-config in any Python environment.

**4. SearXNG engine compatibility**

Directly reuse SearXNG's massive engine ecosystem (200+). Copy engine files from SearXNG and change imports — no other solution offers this level of engine reuse.

## Built-in Engines (106)

| Engine | Categories | Description |
|--------|-----------|-------------|
| google | general | Google Web Search |
| google_images | images | Google Images |
| google_videos | videos | Google Videos |
| google_news | news | Google News |
| bing | general | Bing Web Search |
| bing_images | images | Bing Images |
| bing_videos | videos | Bing Videos |
| bing_news | news | Bing News |
| brave | general, news, images, videos | Brave Search |
| duckduckgo | general | DuckDuckGo HTML (no-JS) |
| duckduckgo_extra | images, videos, news | DuckDuckGo Extra |
| yahoo | general | Yahoo Search |
| qwant | general | Qwant Search |
| baidu | general, images, it | Baidu Search |
| sogou | general | Sogou Search |
| sogou_wechat | news | Sogou WeChat Articles |
| quark | general, images | Quark/Shenma Search |
| mwmbl | general | Mwmbl Search |
| marginalia | general | Marginalia Search |
| seznam | general | Seznam Search |
| reddit | social media | Reddit Search |
| hackernews | it, news | Hacker News |
| stackexchange | it, q&a | Stack Exchange (StackOverflow) |
| wikipedia | general | Wikipedia Summary |
| unsplash | images | Unsplash Photos |
| imgur | images | Imgur Images |
| wallhaven | images | Wallhaven Wallpapers |
| deezer | music | Deezer Music |
| genius | music, lyrics | Genius Lyrics |
| bandcamp | music | Bandcamp Music |
| vimeo | videos | Vimeo Videos |
| invidious | videos | Invidious (YouTube front-end) |
| piped | videos | Piped (YouTube front-end) |
| github | it, repos | GitHub Repos Search |
| github_code | code | GitHub Code Search |
| gitlab | it, repos | GitLab Repos Search |
| gitea | it, repos | Gitea/Forgejo Repos Search |
| sourcehut | it, repos | SourceHut Repos Search |
| npm | it, packages | NPM Packages |
| docker_hub | it, packages | Docker Hub Images |
| crates | it, packages | Rust crates |
| 1337x | files | 1337x Torrents |
| nyaa | files | Nyaa Anime Torrents |
| arxiv | science | arXiv Preprints |
| crossref | science | Crossref Scholarly Metadata |
| openalex | science | OpenAlex Works |
| semantic_scholar | science | Semantic Scholar Papers |
| pubmed | science | PubMed Biomedical Literature |
| pdbe | science | PDBe Protein Structures |
| astrophysics_data_system | science | NASA ADS (requires API key) |
| scanr_structures | science | ScanR French Research Structures |
| artic | images | Art Institute of Chicago |
| artstation | images | ArtStation Artworks |
| deviantart | images | DeviantArt |
| findthatmeme | images | FindThatMeme |
| flickr | images | Flickr (requires API key) |
| flickr_noapi | images | Flickr (no API key) |
| ipernity | images | Ipernity |
| loc | images | Library of Congress Photos |
| openclipart | images | OpenClipArt |
| openverse | images | Openverse CC Media |
| pexels | images | Pexels Photos |
| pinterest | images | Pinterest |
| pixabay | images | Pixabay Media |
| pixiv | images | Pixiv Illustrations |
| public_domain_image_archive | images | Public Domain Image Archive |
| sogou_images | images | Sogou Images |
| 1x | images | 1x Photography |
| 360search_videos | videos | 360Search Videos |
| acfun | videos | Acfun Videos |
| bitchute | videos | Bitchute Videos |
| ccc_media | videos | media.ccc.de |
| dailymotion | videos | Dailymotion Videos |
| digbt | videos, music, files | DigBT Torrents |
| ina | videos | INA (French) |
| iqiyi | videos | iQiyi Videos |
| mediathekviewweb | videos | MediathekViewWeb (German) |
| niconico | videos | Niconico Videos |
| odysee | videos | Odysee Videos |
| peertube | videos | Peertube Federated Videos |
| rumble | videos | Rumble Videos |
| sepiasearch | videos | SepiaSearch Federated Videos |
| sogou_videos | videos | Sogou Videos |
| tubearchivist | videos | Tube Archivist (self-hosted, requires base_url+token) |
| youtube_api | videos, music | YouTube Data API v3 (requires API key) |
| youtube_noapi | videos, music | YouTube (no API key) |
| mixcloud | music | Mixcloud |
| radio_browser | music, radio | Radio Browser Stations |
| soundcloud | music | SoundCloud |
| spotify | music | Spotify (requires client credentials) |
| yandex_music | music | Yandex Music |
| imdb | movies | IMDB |
| moviepilot | movies | Moviepilot (German) |
| rottentomatoes | movies | Rotten Tomatoes |
| senscritique | movies | SensCritique (French) |
| 9gag | social media | 9GAG |
| lemmy | social media | Lemmy (Communities/Users/Posts/Comments) |
| mastodon | social media | Mastodon (accounts/hashtags) |
| mrs | social media | Matrix Rooms Search (requires base_url) |
| tootfinder | social media | Tootfinder (Mastodon posts) |
| ansa | news | Ansa (Italian) |
| il_post | news | Il Post (Italian) |
| reuters | news | Reuters |
| yahoo_news | news | Yahoo News |
| bilibili | videos | Bilibili Videos |

## Installation

```bash
pip install -e .

# For CDP browser auto-launch feature
pip install -e ".[browser]"
```

Requires Python >= 3.10.

## Usage

### Python API

```python
from scoutlet import search_sync, search

# Synchronous search (recommended for scripts)
results = search_sync("python tutorial", engines=["google", "bing"])

for r in results:
    print(f"[{','.join(r.engines)}] {r.title}")
    print(f"  {r.url}")
    print(f"  {r.content[:100]}")
    print(f"  score: {r.score:.2f}")

# Async search (for use in async programs)
results = await search("python tutorial", engines=["google", "bing"])

# Search by category
results = search_sync("AI", categories=["general", "news"])

# Specify language and time range
results = search_sync("latest news", language="zh", time_range="day")
```

### CLI

```bash
# Search
scoutlet "python tutorial" -e google,bing

# JSON output
scoutlet "python tutorial" -e google,bing -f json

# Specify language, time range
scoutlet "latest news" -l zh -t day -e baidu,sogou

# List available engines
scoutlet --list-engines
```

## Proxy and Browser Fallback

### HTTP Proxy

Support HTTP/SOCKS5 proxy via the `proxy` parameter for all engines:

```python
# HTTP proxy
results = search("test", engines=["google"], proxy="http://127.0.0.1:7890")

# SOCKS5 proxy (requires: pip install httpx[socks])
results = search("test", engines=["google"], proxy="socks5://127.0.0.1:1080")
```

```bash
scoutlet "test" -e google --proxy http://127.0.0.1:7890
# SOCKS5 requires: pip install httpx[socks]
scoutlet "test" -e google --proxy socks5://127.0.0.1:1080
```

### CDP Browser Fallback (Bypass Anti-bot)

When engines are blocked by anti-bot mechanisms (CAPTCHA, AccessDenied, 429) from Google/DuckDuckGo etc., automatically retry via Chrome browser.

**Advantages**:
- Reuses user's logged-in browser session (no login required)
- Uses real browser fingerprints, undetectable as bot
- Works with all engines

**Option 1: Auto-launch browser (recommended)**

No need to manually start Chrome — the program auto-launches headless Chrome. When blocked by anti-bot, automatically downgrades to headful retry.

```python
load_engines(engine_configs={
    "google": {
        "fallback_to_browser": True,
        "auto_launch_browser": True,   # Auto-launch Chrome (headless by default)
    },
})

results = search_sync("test", engines=["google"])
```

Requires the browser dependency:

```bash
pip install -e ".[browser]"
```

**Option 2: Manually start Chrome**

Start Chrome with remote debugging port beforehand:

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

# HTTP succeeds → normal path; fails → auto-fallback to CDP
results = search_sync("test", engines=["google"])
```

**Configuration**:

| Config | Default | Description |
|--------|---------|-------------|
| `fallback_to_browser` | `False` | Enable CDP browser fallback |
| `auto_launch_browser` | `False` | Auto-launch Chrome (requires `pychrome`) |
| `headless` | `True` | Default headless mode; auto-downgrades to headful when blocked |
| `block_resources` | `True` | Block images/fonts/CSS etc. for faster loading |
| `browser_args` | `None` | Custom Chrome launch arguments |
| `cdp_endpoint` | `http://localhost:9222` | CDP debugging endpoint address |

**Workflow**:

```
HTTP request → success → return results
             → failed (CAPTCHA/403/429)
             → CDP fallback
                 → headless Chrome navigation
                     → normal page → return results
                     → blocked → auto-downgrade to headful retry
```

### Google Engine Notes

Google search uses a **mobile GSA User-Agent** (Android Chrome) to bypass JS-only pages and return traditional HTML. As Google's anti-bot strategies evolve, you may need to:

```bash
# Update GSA User-Agent list
python scripts/update_gsa_useragents.py
```

If the GSA UA is also blocked, enable `fallback_to_browser=True` to retry via user's Chrome.

## TLS Fingerprint HTTP Backend (Optional)

Some engines detect bot traffic at the TLS layer (JA3/JA4 fingerprint, HTTP/2 settings). scoutlet ships an optional `primp`-based adapter that impersonates a random real browser (Chrome/Firefox/Safari) — cipher suites, ALPN, HTTP/2 frames, and header order all match a real browser, so the request is indistinguishable at the TLS layer.

```bash
pip install -e ".[fingerprint]"   # installs primp>=1.2.3
```

**Per-engine** (recommended — only fingerprint the engines that need it):

```python
load_engines(engine_configs={
    "duckduckgo": {"http_client": "fingerprint"},
    "google": {"http_client": "fingerprint"},
})

results = search_sync("test", engines=["google"])
```

**Global** (applies to every engine):

```python
from scoutlet.network import set_adapter_backend

set_adapter_backend("fingerprint")
```

Leave `http_client` empty / unset to keep the default `httpx` backend. Custom adapters can be registered via `scoutlet.client_adapter.register_adapter(name, cls)`.

## Engine Health & Auto-Heal

scoutlet ships a CI pipeline (`.github/workflows/engine-health.yml`) that runs every 6 hours, performs an end-to-end probe of all engines, classifies failures, and triggers an LLM-driven auto-heal flow that opens a fix PR when a parser breaks.

Pipeline stages:

1. **Health check** (`scripts/health_check.py --all`) — runs a real search per engine, classifies status as `healthy` / `empty` / `anti_bot` / `http_error` / `parser_error` / `timeout`, dumps JSON report + saves failed HTML snapshots.
2. **Snapshot manager** (`scripts/snapshot.py`) — stores `baseline_*` and `failed_*` HTML side-by-side, with a minimizer that strips `<script>`/`<style>` and large blobs for cheaper LLM input.
3. **AI repair agent** (`scripts/auto_heal.py`) — for each parse failure, reads the current engine source, the failed HTML, and the baseline HTML, prompts an OpenAI-compatible LLM to rewrite the `response()` parser, then verifies the result with: forbidden-pattern scan, `ast.parse` syntax check, fixture replay, and a live re-probe.
4. **PR creation** — if any engine was successfully repaired, the workflow commits to an `auto-fix/<timestamp>` branch and opens a PR labeled `auto-fix` for human review.

Configuration (CI secrets):

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | LLM provider key |
| `OPENAI_API_BASE` | OpenAI-compatible base URL |
| `OPENAI_MODEL` | Model name (default `gpt-4o`) |

Run locally:

```bash
# Probe all engines, save snapshots
uv run python scripts/health_check.py --all --output health-report.json --snapshots-dir snapshots

# Attempt repairs from the latest report
uv run python scripts/auto_heal.py --report health-report.json --snapshots-dir snapshots --dry-run
```

See [design doc](docs/auto_heal_design.md) for the full architecture.

## Tests

463 offline tests across three suites:

```bash
uv run pytest tests/unit/        # core logic: result types, aggregation, engine_loader, network, browser, CDP fallback, client_adapter, CLI
uv run pytest tests/engines/     # P0/P1 engine parser fixtures (saved HTML/JSON, no network)
uv run pytest tests/             # all offline tests
```

Live smoke tests against real engines are gated by `pytest.mark.live` and require `SCOUTLET_LIVE=1`:

```bash
SCOUTLET_LIVE=1 uv run pytest tests/live/ -m live
```

CI (`.github/workflows/engine-health.yml`) runs `compileall` + offline tests + the health/auto-heal pipeline on every 6-hour schedule.

## TODO

- [ ] Sync more SearXNG engines, complete migration and testing of all 200+ engines, periodically sync upstream SearXNG engine updates
- [ ] Continuously follow SearXNG's anti-bot strategies (UA updates, request parameter adjustments, new engine adaptations, etc.)
- [x] **Engine Auto-Heal** — Automated engine health monitoring and AI-powered self-repair system
  - [x] Health Monitor: scheduled end-to-end testing of all engines (`scripts/health_check.py` + CI every 6h)
  - [x] HTML Snapshot: save baseline and failed HTML responses for comparison (`scripts/snapshot.py`)
  - [x] AI Repair Agent: when parsing fails, call LLM to analyze HTML structure changes and rewrite engine parsing code (`scripts/auto_heal.py`)
  - [ ] Auto-Tester: full sandbox validation of AI-generated code (currently CI does compileall + fixture replay + live re-probe; isolated sandbox still TODO)
  - [x] Auto-commit: verified fixes committed via PR for review (CI `auto-heal` job)
  - See [design doc](docs/auto_heal_design.md) for details
