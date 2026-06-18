# scoutlet

A minimalist local search aggregation tool for AI agents — no API keys, no heavy dependencies, compatible with SearXNG's 200+ search engine ecosystem, delivering powerful search capabilities to local agents.

Based on [SearXNG](https://github.com/searxng/searxng)'s engine system and result aggregation algorithm, retaining only the core engine loading, concurrent requests, scoring, deduplication, merging, and sorting logic.

## Features

- Only 3 core dependencies: `httpx`, `lxml`, `babel`
- Reuses SearXNG's result aggregation algorithm (weighted scoring, hash dedup, merge, group sorting)
- Compatible with SearXNG engine code patterns — copy and change imports to use
- Python API and CLI interfaces
- 108 built-in engines (general, news, images, videos, code, music, files, science, movies, social media, and more)
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

## Built-in Engines (108)

Engines grouped by primary category. The "also in" column lists additional categories the engine belongs to. Engines with `categories = []` (emojipedia, wikipedia) are listed at the end — they are not picked up by default searches and must be invoked with `-e <name>`.

### general (12) — default category

| Engine | also in | Description |
|--------|---------|-------------|
| google |  | Google Web Search |
| bing | web | Bing Web Search |
| brave | web | Brave Search |
| duckduckgo |  | DuckDuckGo HTML (no-JS) |
| yahoo | web | Yahoo Search |
| qwant | web | Qwant Search |
| baidu |  | Baidu Search |
| sogou |  | Sogou Search |
| quark |  | Quark/Shenma Search |
| seznam |  | Seznam Search |
| marginalia |  | Marginalia Search |
| mwmbl |  | Mwmbl Search |

### images (24)

| Engine | also in | Description |
|--------|---------|-------------|
| google_images | web | Google Images |
| bing_images | web | Bing Images |
| duckduckgo_extra | videos, news | DuckDuckGo Extra (set `ddg_category=images`) |
| unsplash |  | Unsplash Photos (requires API key) |
| imgur |  | Imgur Images |
| wallhaven |  | Wallhaven Wallpapers (requires API key) |
| artic |  | Art Institute of Chicago |
| artstation |  | ArtStation Artworks |
| deviantart |  | DeviantArt |
| findthatmeme |  | FindThatMeme |
| flickr |  | Flickr (requires API key) |
| flickr_noapi |  | Flickr (no API key) |
| ipernity |  | Ipernity |
| loc |  | Library of Congress Photos |
| openclipart |  | OpenClipArt |
| openverse |  | Openverse CC Media |
| pexels |  | Pexels Photos |
| pinterest |  | Pinterest |
| pixabay |  | Pixabay Media |
| pixiv |  | Pixiv Illustrations |
| public_domain_image_archive |  | Public Domain Image Archive |
| sogou_images |  | Sogou Images |
| www1x |  | 1x Photography |
| frinkiac |  | Frinkiac Simpsons Screenshots |

### videos (24)

| Engine | also in | Description |
|--------|---------|-------------|
| google_videos | web | Google Videos |
| bing_videos | web | Bing Videos |
| youtube_noapi | music | YouTube (no API key) |
| youtube_api | music | YouTube Data API v3 (requires API key) |
| vimeo |  | Vimeo Videos |
| invidious |  | Invidious (YouTube front-end) |
| piped |  | Piped (YouTube front-end) |
| bilibili |  | Bilibili Videos |
| 360search_videos |  | 360Search Videos |
| acfun |  | Acfun Videos |
| bitchute |  | Bitchute Videos |
| ccc_media |  | media.ccc.de |
| dailymotion |  | Dailymotion Videos |
| digbt | music, files | DigBT Torrents |
| ina |  | INA (French) |
| iqiyi |  | iQiyi Videos |
| mediathekviewweb |  | MediathekViewWeb (German) |
| niconico |  | Niconico Videos |
| odysee |  | Odysee Videos |
| peertube |  | Peertube Federated Videos |
| rumble |  | Rumble Videos |
| sepiasearch |  | SepiaSearch Federated Videos |
| sogou_videos |  | Sogou Videos |
| tubearchivist |  | Tube Archivist (self-hosted, requires base_url+token) |

### music (8)

| Engine | also in | Description |
|--------|---------|-------------|
| deezer |  | Deezer Music |
| genius | lyrics | Genius Lyrics |
| bandcamp |  | Bandcamp Music |
| mixcloud |  | Mixcloud |
| radio_browser | radio | Radio Browser Stations |
| soundcloud |  | SoundCloud |
| spotify |  | Spotify (requires client credentials) |
| yandex_music |  | Yandex Music |

### news (7)

| Engine | also in | Description |
|--------|---------|-------------|
| google_news |  | Google News |
| bing_news |  | Bing News |
| yahoo_news |  | Yahoo News |
| sogou_wechat |  | Sogou WeChat Articles |
| ansa |  | Ansa (Italian) |
| il_post |  | Il Post (Italian) |
| reuters |  | Reuters |

### it (10)

| Engine | also in | Description |
|--------|---------|-------------|
| github | repos | GitHub Repos Search |
| gitlab | repos | GitLab Repos Search (requires base_url) |
| gitea | repos | Gitea/Forgejo Repos Search |
| sourcehut | repos | SourceHut Repos Search |
| npm | packages | NPM Packages |
| docker_hub | packages | Docker Hub Images |
| crates | packages | Rust crates |
| pypi | packages | PyPI Packages |
| stackexchange | q&a | Stack Exchange (StackOverflow) |
| hackernews | news | Hacker News |

### science (8)

| Engine | also in | Description |
|--------|---------|-------------|
| arxiv | scientific publications | arXiv Preprints |
| crossref | scientific publications | Crossref Scholarly Metadata |
| openalex | scientific publications | OpenAlex Works |
| semantic_scholar | scientific publications | Semantic Scholar Papers |
| pubmed | scientific publications | PubMed Biomedical Literature |
| pdbe |  | PDBe Protein Structures |
| astrophysics_data_system | scientific publications | NASA ADS (requires API key) |
| scanr_structures |  | ScanR French Research Structures |

### social media (6)

| Engine | also in | Description |
|--------|---------|-------------|
| reddit |  | Reddit Search |
| 9gag |  | 9GAG |
| lemmy |  | Lemmy (Communities/Users/Posts/Comments) |
| mastodon |  | Mastodon (accounts/hashtags) |
| mrs |  | Matrix Rooms Search (requires base_url) |
| tootfinder |  | Tootfinder (Mastodon posts) |

### movies (4)

| Engine | also in | Description |
|--------|---------|-------------|
| imdb |  | IMDB |
| moviepilot |  | Moviepilot (German) |
| rottentomatoes |  | Rotten Tomatoes |
| senscritique |  | SensCritique (French) |

### files (2)

| Engine | also in | Description |
|--------|---------|-------------|
| 1337x |  | 1337x Torrents |
| nyaa |  | Nyaa Anime Torrents |

### code (1)

| Engine | also in | Description |
|--------|---------|-------------|
| github_code | it | GitHub Code Search |

### No category (2) — must invoke with `-e <name>`

These engines have `categories = []`, matching SearXNG. Default searches skip them.

| Engine | Description |
|--------|-------------|
| emojipedia | Emojipedia Emoji Reference |
| wikipedia | Wikipedia Summary |

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

# Group engines by category
scoutlet --list-engines --by-category
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

The same behavior is available from CLI:

```bash
scoutlet "test" -e google --fallback-to-browser --auto-launch-browser
scoutlet "test" -e google --fallback-to-browser --auto-launch-browser --headful
scoutlet "test" -e google --fallback-to-browser --cdp-endpoint http://localhost:9333
```

`--auto-launch-browser` implicitly enables browser fallback. `--headful` uses a visible browser window instead of headless mode.

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

473 offline tests across three suites:

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
