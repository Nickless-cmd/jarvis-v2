# web_scrape Tool — Design Spec
Date: 2026-04-23

## Problem

Jarvis has `web_fetch` (raw regex-stripped HTML) and `browser_*` (manual step-by-step navigation), but nothing that intelligently scrapes a page and returns structured content. `web_fetch` fails on JS-rendered pages and returns unsorted noise. `web_scrape` fills that gap.

## Approach

Hybrid urllib fast-path → Playwright fallback:

1. Try urllib + readability extraction (fast, no session dependency)
2. If extracted content < 200 chars, retry via existing Playwright session (handles JS-rendered SPAs)
3. Apply mode-handler to structure the result
4. Cache and return

## Files

- **`core/tools/web_scrape_tool.py`** — all scraper logic (fetch, extract, mode-handlers, cache)
- **`core/tools/simple_tools.py`** — tool definition, `_exec_web_scrape`, dispatch entry

## Tool Interface

### Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | required | URL to scrape |
| `mode` | enum | `auto` | `article` \| `listing` \| `product` \| `social` \| `auto` |
| `extract` | string | `""` | Free-text hint: what to extract ("prices", "contact info") |
| `include_links` | bool | `false` | Include extracted links in output |

### Output

```json
{
  "title": "Page title",
  "url": "https://...",
  "domain": "example.com",
  "content": "Cleaned main body text",
  "metadata": {
    "author": "...",
    "date": "...",
    "language": "da"
  },
  "items": [],
  "links": [],
  "mode_used": "article",
  "source": "urllib|playwright",
  "from_cache": false,
  "chars": 1234,
  "status": "ok"
}
```

`items` — only populated for `listing`/`product` modes. Array of dicts with extracted elements from `<li>`, `<article>`, `<tr>` patterns, guided by `extract` hint.

`links` — only populated if `include_links=true`. Array of `{text, href}` dicts, internal and external.

## Extraction Pipeline

```
url
 │
 ├─ cache hit? ──► return cached result
 │
 ▼ miss
urllib GET (15s timeout, desktop UA)
 │
 ├─ content >= 200 chars after extraction ──► proceed to mode-handler
 │
 ▼ sparse (JS-rendered suspected)
Playwright: navigate → page.content() → extraction
 │
 ▼
readability-lxml (if available)
 │ ImportError
 ▼
BeautifulSoup heuristic (remove nav/footer/aside/script/style → longest <article>/<main>/<div>)
 │
 ▼
mode-handler
 │
 ▼
cache store → return
```

## Mode Handlers

| Mode | Strategy |
|------|----------|
| `article` | readability main content, extract author from byline/meta, date from time/meta |
| `listing` | find repeating elements (`<li>`, `<article>`, `<tr>`), return as `items` array |
| `product` | extract title, price (€/$/kr patterns), description, availability |
| `social` | extract post text, username, timestamp, like/share counts if present |
| `auto` | detect from HTML semantics: `<article>` → article, `<ul>/<ol>` dominance → listing, price patterns → product, else article |

The `extract` hint is appended to the mode logic — it filters which fields to include and guides which patterns to prioritise. No LLM call for extraction (too expensive, heuristics are sufficient).

## Caching

URL-keyed (SHA256 of normalised URL). Uses existing `web_cache_store`/`web_cache_lookup`.

| Mode | TTL |
|------|-----|
| `article` / `auto` | 24 hours |
| `listing` / `product` | 2 hours (prices change) |
| `social` | 30 minutes |

## Dependencies

- `readability-lxml` — soft dependency, try/except on import, falls back to BS4
- `beautifulsoup4` — already used elsewhere in project
- `playwright` — existing session via `run_in_playwright()`, only invoked on sparse fallback

## Error Handling

- Network timeout / DNS failure → `{"status": "error", "error": "..."}`
- Playwright session not running → log warning, do not raise, return urllib result even if sparse
- Unparseable HTML → return raw stripped text with `mode_used: "fallback"`
- Cache write failure → log, continue (non-fatal)

## Out of Scope

- LLM post-processing of extracted content
- Pagination / multi-page crawling
- Login / authenticated scraping
- PDF or binary content
