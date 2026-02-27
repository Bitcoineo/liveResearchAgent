# DeFi Research Agent v2

Automated DeFi protocol due diligence with fully live data. Pulls TVL history, audit reports, red flags, governance activity, and community sentiment in real time, then synthesizes everything into a structured markdown report with a 0-10 risk score.

**Stack:** `Python 3 · DeFiLlama API · GitHub API · Snapshot GraphQL · Etherscan · requests · marked.js`

---

## Why I built this

The first version of this agent used static template data for the web research sections. That made the reports feel hollow. This version replaces every placeholder with live API calls: audit reports sourced from known audit firm GitHub orgs, red flags derived from actual DeFiLlama hack history and Etherscan contract verification, governance data from Snapshot, and developer activity from GitHub. The reports are now genuinely useful for due diligence.

## What a report contains

1. **Executive Summary** Verdict, global score (0-10), top, positive signals
2. **On-Chain Findings** TVL, multi-chain deployment, funding history, security incidents, key events
3. **Third-Party Intelligence** Live audit reports, bug bounty info, community sentiment
4. **Red Flags Register** Severity-ranked risk indicators derived from live data
5. **Data Limitations** Gaps and areas needing further investigation

## Live Data Sources

| Section | Source |
|---------|--------|
| TVL, chains, funding, hacks | DeFiLlama API |
| Audit reports | GitHub API (Trail of Bits, OpenZeppelin, Certora, Sherlock, Code4rena, and more) |
| Bug bounty | Immunefi (best-effort, degrades gracefully) |
| Red flags | DeFiLlama hack history + Etherscan contract verification |
| Governance | Snapshot GraphQL (proposal counts, voter participation) |
| Developer activity | GitHub API (commit frequency, open issues, contributors) |

## Usage

### CLI

    pip install -r requirements.txt

    python3 main.py aave
    python3 main.py aave --days 90
    python3 main.py uniswap --json

Reports are saved to reports/<slug>-<date>.md.

### Web UI

    python3 web.py

Open http://localhost:8000. Type any protocol name or use the quick-pick cards (Aave, Lido, Ethena, Uniswap, Maker). Reports render inline and can be downloaded as .md files.

## Project Structure

    main.py              CLI entry point
    web.py               Web UI server (port 8000)
    defillama.py         DeFiLlama API client with caching and fuzzy resolution
    report.py            Structured report builder
    markdown_report.py   Markdown renderer
    web_research.py      Live web research module
    requirements.txt     Dependencies
    reports/             Generated reports (gitignored)

## Status

- DeFiLlama data: Live
- Web research: Live (audit reports, red flags, governance, developer activity)
- Global Score: Synthesizes TVL, security, audits, and funding into a 0-10 rating

## GitHub Topics

`defi` `python` `due-diligence` `defillama` `tvl` `risk-assessment` `agent` `crypto` `github-api` `snapshot`
