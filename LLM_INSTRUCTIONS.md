# LLM Integration Guide: Notion Context Service

This guide instructs an LLM on which API endpoint to use, how to call it, and how to interpret the results. The API delivers Notion context for analysis in LLM-friendly formats.

Base URL: `http://localhost:8000`

## Quick Decision Matrix (use these two by default)

- Primary (content): `GET /api/v1/search/pages` — when you need readable content about a topic
- Primary (listing DB items): `GET /api/v1/search/databases` — when you need to find DBs and list their items
- Optional (full dump of known DB): `GET /api/v1/databases/{database_id}/export`
- Optional (broad orchestrated search): `GET /api/v1/query`

## Common Parameters (defaults for LLM)

- `q` (string): Search query
- `max_results` (int): Limit matches (1..50; default 10)
- `per_database_page_limit` (int): Limit pages expanded from each DB (1..50; default 10)
- `include_blocks` (bool): Fetch and parse recursive blocks into content
- `format` (string): `text` | `elements` | `both`
  - `text`: flattened, cleaned multi-line text
  - `elements`: structured JSON array (headings, paragraphs, lists, etc.)
- `minimal` (bool): Compact outputs (LLM-friendly) — default: true
- `minimal_mode` (string): `string` | `lines` — default: lines
  - `string`: a single cleaned text blob
  - `lines`: array of lines split at `\n`

The API normalizes text by replacing non-breaking spaces, standardizing line breaks, trimming trailing spaces, and collapsing excessive blank lines.

## Endpoint Details

### 1) Search Databases (primary)
`GET /api/v1/search/databases`

Use when: You need to discover databases related to a topic and list pages within.

Parameters:
- `q` (required)
- `max_results` (default 10)
- `per_database_page_limit` (default 10)
- `include_blocks` (default false) – set true to fetch page content
- `format` – `text` recommended for LLMs
- `minimal` – true for compact shape
- `minimal_mode` – `string` or `lines`

Recommended LLM call for overview (no content):
```
GET /api/v1/search/databases?q=<topic>&per_database_page_limit=5&include_blocks=false&minimal=true
```

Recommended LLM call for content (LLM-ready, per-line; default choice):
```
GET /api/v1/search/databases?q=<topic>&per_database_page_limit=50&include_blocks=true&format=text&minimal=true&minimal_mode=lines
```

Response (minimal, with content lines):
```
{
  "query": "<topic>",
  "results": [
    {
      "database": "<db title>",
      "items": [ { "title": "<page title>", "content_lines": ["...", "..."] }, ... ]
    }
  ]
}
```

### 2) Search Pages (primary)
`GET /api/v1/search/pages`

Use when: You need readable content about a topic (paragraphs, lists, headings).

Parameters: `q`, `max_results`, `include_blocks`, `format`, `minimal`, `minimal_mode`

Recommended (per-line LLM format):
```
GET /api/v1/search/pages?q=<topic>&include_blocks=true&format=text&minimal=true&minimal_mode=lines&max_results=5
```

Response (minimal, lines):
```
{
  "query": "<topic>",
  "results": [
    {
      "title": "<page title>",
      "content_lines": ["line 1", "line 2", ...]
    }
  ]
}
```

### 3) Export Entire Database
`GET /api/v1/databases/{database_id}/export`

Use when: You need a full export of all pages in a known database.

Parameters:
- `include_blocks` (default true)
- `format` – `text`, `elements`, or `both`

Recommended:
```
GET /api/v1/databases/{database_id}/export?include_blocks=true&format=both
```

Response (non-minimal, per page):
```
{
  "database_id": "...",
  "results": [
    {
      "id": "...",
      "title": "...",
      "url": "...",
      "created_time": "...",
      "last_edited_time": "...",
      "total_blocks": 13,
      "content_text": "...",           // when format includes text
      "elements": [ {"type":"paragraph","text":"..."}, ... ] // when format includes elements
    }
  ]
}
```

### 4) Integrated Query
`GET /api/v1/query`

Use when: Starting point is ambiguous; you want both pages and databases, with optional DB expansion.

Parameters:
- `q`, `max_results`
- `expand_databases` (default true)
- `per_database_page_limit` (default 10)
- `include_blocks` (default true)
- `format` – `text`, `elements`, or `both`

Example:
```
GET /api/v1/query?q=<topic>&expand_databases=true&per_database_page_limit=5&include_blocks=true&format=both
```

Response: mixed `results` with `object_type` equal to `database` or `page`.

## LLM Usage Guidance (defaults)

1) Use `minimal=true` and `minimal_mode=lines` by default.

2) If `content` or `content_lines` is empty:
   - Many Notion DB entries are records with properties only (no blocks). Acknowledge emptiness.
   - Optionally ask the caller to enable a properties fallback mode (not default) or switch to database export for deeper coverage.

3) Scale wisely:
   - Default to `max_results=5` and `per_database_page_limit=20`.
   - Increase only when the user explicitly requests more detail.

4) Choose `format=both` when you need both a narrative form (`content_text`) and a structured form (`elements`) for precise parsing.

5) Newline handling:
   - API returns clean `\n` line breaks in text.
   - Use `minimal_mode=lines` to receive `content_lines` (array), avoiding ambiguity.

## Example Playbooks

- Summarize content about a known topic:
  1) `GET /api/v1/search/pages?q=<topic>&include_blocks=true&format=text&minimal=true&minimal_mode=lines&max_results=5`
  2) Concatenate or reason over `content_lines` across results.

- Enumerate items in a relevant database, then deep-dive:
  1) `GET /api/v1/search/databases?q=<topic>&per_database_page_limit=10&include_blocks=false&minimal=true`
  2) Select pages of interest, then re-fetch with `include_blocks=true&format=text&minimal=true`.

- Full ingestion for vectorization/indexing:
  1) `GET /api/v1/databases/{db_id}/export?include_blocks=true&format=both`
  2) Store both `content_text` and `elements` in your pipeline.

## Failure/Retry Strategies & Fallbacks

- 400 (bad params): correct bounds or parameter value.
- 503 (Notion upstream): wait and retry.
- Mixed success: the API already continues after per-item failures and returns partial results with `error` fields—proceed with available items.
- Properties fallback (blockless pages): If `content` or `content_lines` is empty and the user permits, summarize from available metadata (e.g., title, tags, dates) or ask to enable a properties fallback mode.

---
This file is intended to be provided verbatim to an LLM as a system or tool instruction to ensure correct endpoint usage and reliable, LLM-friendly outputs.
