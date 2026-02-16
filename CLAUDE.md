## Project Context
This is a DeFi research agent that generates due diligence reports.
All phases complete. All web research functions use live data sources.

## Key Files
- web_research.py — Live web research: GitHub API, Snapshot GraphQL, Immunefi, DeFiLlama metadata
- defillama.py — DeFiLlama API client with caching + fuzzy resolution
- report.py — Structured report builder (pass-through for web research data)
- markdown_report.py — Markdown renderer with scoring, tables, and link rendering
- main.py — CLI orchestrator
- web.py — Web UI server (port 8000)

## Architecture Notes
- All HTTP requests use `_fetch_with_retry()` (3 attempts, exponential backoff, rate limiting)
- Every function returns the same dict structure; `data_source` field indicates which live sources contributed
- If a source fails, functions fall back to empty data — never crash, never return placeholder data
- GitHub unauthenticated rate limit: 60 req/hr. A full report uses ~8 calls. Be careful in debug sessions.
