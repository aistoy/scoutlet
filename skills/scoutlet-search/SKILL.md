---
name: scoutlet-search
description: Use scoutlet to search the web with multiple SearXNG-compatible engines (108 engines across general, code, science, news, packages, reference, discussion) aggregated locally — no API keys, no cloud service. Trigger this skill whenever the user asks to "search", "look up", "find online", "google", "查一下", "搜一下", "搜一下 X", or otherwise retrieve fresh information from the web.Prefer scoutlet when multi-engine aggregation, structured output with provenance, or domain-specific engines (arxiv, github, pubmed, etc.) are wanted.
---

# scoutlet-search

## What is scoutlet

scoutlet is a local search aggregator that reuses SearXNG's engine
architecture (108 engines across 11 categories) and result-aggregation
algorithm (weighted scoring, hash-based dedup, category-grouped sort).
It runs as a CLI or Python library — no web service, no Docker, no API
keys for the default engine set.

Designed as a "SearXNG-lite" embeddable core for AI agents.

## When to use

Trigger scoutlet when the user wants information from the web and any
of these apply:

- They need fresh / current info beyond your knowledge cutoff
- They ask for multi-source verification ("search a few engines", "corroborate across sources")
- They want domain-specific engines (academic papers, code repos, package registries, discussions)
- They want structured JSON output with provenance (`source_engines`, `corroboration_count`)
- They want to compare / cross-reference independent sources on the same query

## When NOT to use

Skip scoutlet when:

- The answer is in your existing knowledge and the user doesn't ask for fresh sources
- The user asks for reasoning, analysis, or computation (not info retrieval)
- The user explicitly says "don't search" / "不用搜"
- The user asks about their own codebase or local files (just read them directly)

## Installation

```bash
pip install scoutlet
# Optional: TLS fingerprint backend for engines that CAPTCHA easily
pip install scoutlet[fingerprint]
```

Verify it works:

```bash
scoutlet --list-engines | head
scoutlet "python tutorial" 
```

If `scoutlet` is not on PATH after install, use `python -m scoutlet.cli`
as an equivalent.

## Engine selection strategy

**This is the most important section.** scoutlet has 108 engines;
picking wrong ones wastes time and triggers CAPTCHAs.

### Stable pool — DEFAULT for agent use

API-driven engines with no CAPTCHA risk and predictable output.
**Always pass `-e <stable engines>` explicitly** rather than relying
on language-aware defaults (which silently include high-risk engines).

| Task | Recommended engines |
|------|---------------------|
| Code & repos | `github`, `gitlab`, `sourcehut`, `stackexchange` |
| Academic papers | `arxiv`, `semantic_scholar`, `pubmed`, `crossref`, `openalex` |
| Packages | `pypi`, `npm`, `crates`, `docker_hub` |
| Reference | `wikipedia` (note: `categories=[]`, MUST pass `-e wikipedia`) |
| Discussion | `hackernews`, `reddit` |

### High-risk pool — only when user explicitly wants general web

General web engines with high anti-bot risk. They work, but expect
intermittent CAPTCHAs and silent-empty results.

- **English**: `google`, `bing`, `brave`, `duckduckgo`, `yahoo`, `qwant`
- **Chinese**: `baidu`, `sogou`, `quark`
- **Others**: `seznam`, `marginalia`, `mwmbl`

### Decision rule

1. **Default**: pass `-e <stable engines>` explicitly (e.g., `-e github,arxiv,stackexchange`).
2. **Combine** stable engines for cross-domain queries (e.g., `-e github,crates,arxiv` for "rust async ecosystem").
3. **Only use high-risk pool** when the user explicitly asks for general web search ("google for X", "search the web", "在网上搜").
4. **Never rely on language-aware defaults** (`scoutlet "query"` without `-e`) for agent use — they auto-add `baidu`/`sogou` for Chinese queries and `google`/`bing` for English, which frequently CAPTCHA.

## CLI usage

```bash
# Default engine set (language-aware) — NOT recommended for agents
scoutlet "python tutorial"

# Explicit stable engines (RECOMMENDED for agents)
scoutlet "async rust runtime" -e github,crates,stackexchange
scoutlet "transformer architecture paper" -e arxiv,semantic_scholar
scoutlet "what is X" -e wikipedia,github

# JSON output for programmatic consumption
scoutlet "rust async runtime" -e crates,github -f json

# Filter by category
scoutlet "climate change" -c general,news
scoutlet "rust logo" -c images

# Specify language and time range
scoutlet "最新 AI 新闻" -l zh -t week -e hackernews,reddit

# List all engines (use --by-category to see groupings)
scoutlet --list-engines
scoutlet --list-engines --by-category
```

## Interpreting JSON output

Always use `-f json` when you intend to parse results programmatically.
Top-level shape:

```json
{
  "query": "...",
  "status": "success",            // success | partial | failed
  "results": [
    {
      "url": "...",
      "title": "...",
      "snippet": "...",           // null = no usable preview text
      "source_engines": ["github"],  // which engines contributed this URL
      "corroboration_count": 1,   // = len(source_engines)
      "engine_positions": {"github": 1},
      "is_https": true,
      "netloc": "example.com",
      "is_pdf": false,
      "discovery_score": 1.5
    }
  ],
  "engines": [...],               // per-engine run info
  "skipped": [...],               // engines in cooldown / not loaded
  "warnings": [...]               // e.g., "5/10 results have no snippet"
}
```

Key fields to act on:

- **`status`**:
  - `success` — every engine returned results or cleanly empty (EMPTY is OK)
  - `partial` — at least one engine succeeded AND at least one failed/skipped; consider retrying the failed ones with alternatives
  - `failed` — no engine produced anything; retry with a different `-e` combination
- **`warnings`** — soft signals. `"N/M results have no snippet"` means you must fetch those URLs to evaluate them.
- **`snippet`** — `null` means the engine returned no preview text; treat as unverified until fetched.
- **`corroboration_count`** — how many independent engines returned the same URL. Higher = more canonical.
- **`source_engines`** — provenance. Cite these when telling the user where info came from.

## Common pitfalls

- **Silent empty results on HTTP 200**: some engines return 200 with an empty page when CAPTCHA'd. scoutlet's block-page classifier catches most, but if `status=partial` and a high-risk engine returned 0 results, assume CAPTCHA.
- **Chinese queries auto-add high-risk engines**: language-aware default for `language="zh"` includes `baidu`/`sogou`/`quark`. Always pass `-e` explicitly for stable results.
- **EMPTY ≠ failure**: an engine returning 0 results for an obscure query is normal and does NOT trigger cooldown. Don't retry — the engine genuinely has no results.
- **`wikipedia` requires explicit `-e`**: it has `categories=[]` and is skipped by default searches.
- **`hackernews` engine is under `it` category, not `news`**: counterintuitive but real.

## Failure handling

If `status=failed` or all engines in your `-e` list returned errors:

1. Inspect `engines[]` in JSON — each entry has `status` and `error`:
   - `anti_bot` — engine is in 5-min cooldown; switch engines
   - `rate_limit` — 30-sec cooldown; wait or switch
   - `parser_error` — engine's HTML parser likely broken upstream; report and switch
   - `timeout` — transient; retry once
2. Switch to a different combination from the **stable pool** (table above).
3. If stable pool also fails, the query itself may be too obscure — try reformulating or use `categories` to widen.
4. Avoid hammering a single failing engine — health registry cooldowns exist to prevent this.
