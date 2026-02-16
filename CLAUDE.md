## Project Context
This is a DeFi research agent that generates due diligence reports.
Phase 1-4 are complete. Phase 5 is wiring up real web research data.

## Key Files
- web_research.py — THIS IS THE FILE BEING REWRITTEN. Currently returns placeholder data.
- defillama.py — API client. Working. Don't modify unless adding new endpoints.
- report.py — Report builder. May need minor updates for new data shapes.
- markdown_report.py — Markdown renderer. May need updates for new sections.
- main.py — Orchestrator. Minimal changes expected.

## Rules for Phase 5
- Every data source must have error handling — never crash if a source is down
- Every function in web_research.py must still return the same dict structure
- Keep "data_source" field but change value from "placeholder" to the actual source name
- If a real source fails, fall back to returning empty data — NOT placeholder data
- Add retry logic (3 attempts with backoff) for all HTTP requests
- Respect rate limits — add delays between requests to the same domain
