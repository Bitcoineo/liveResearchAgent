# DeFi Agent — Task Tracker

## Phase 1: DeFiLlama Data Reports
- [x] DefiLlama API client (`defillama.py`)
- [x] Report builder (`report.py`)
- [x] CLI entrypoint (`main.py`)

## Phase 2: Web Research Module (Placeholder)
- [x] Create `web_research.py` with 4 placeholder functions
- [x] Update `report.py` — new `web_research` param + 4 section builders
- [x] Update `main.py` — import & call web_research, pass to build_report
- [x] Verify: `aave`, `lido --days 7`, `notarealprotocol` all behave correctly

## Phase 3: Markdown Report Generation
- [x] Create `markdown_report.py` — renderer with section builders + formatting helpers
- [x] Update `main.py` — save markdown to `reports/{slug}-{date}.md`, print path to stderr
- [x] Verify: `aave` report has all 5 sections, dollar formatting, placeholder flagging
- [x] Verify: `lido --days 7` generates correct report
- [x] Verify: `notarealprotocol` error exits cleanly, no file created
