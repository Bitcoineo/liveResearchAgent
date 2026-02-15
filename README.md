# Bitcoineo DeFi Research Agent

Automated DeFi protocol due diligence reports powered by live DeFiLlama data. Generates comprehensive markdown reports with on-chain analysis, third-party intelligence, and risk assessment.

## Features

- **Live on-chain data** — TVL, multi-chain deployment, funding history, security incidents, key events
- **Third-party intelligence** — Analyst coverage, security audits, community sentiment, red flags
- **Structured reports** — Executive summary, risk scoring, global scoring, data limitations
- **Dual interface** — CLI for scripting, minimal web UI with protocol quick-picks
- **Markdown output** — Reports saved to `reports/` with timestamped filenames

## Tech Stack

- **Python 3** — stdlib HTTP server, no web framework
- **DeFiLlama API** — Protocol data, TVL history, hacks, funding rounds
- **requests** — HTTP client for API calls
- **marked.js** — Client-side markdown rendering (CDN)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Generate a report for Aave (default 30 days TVL history)
python3 main.py aave

# Custom TVL history window
python3 main.py aave --days 90

# Raw JSON output
python3 main.py uniswap --json
```

Reports are saved to `reports/<slug>-<date>.md` and JSON is printed to stdout.

### Web UI

```bash
python3 web.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser. Type a protocol name in the search bar and press Enter (or click Generate), or click one of the protocol cards (Aave, Lido, Ethena, Uniswap, Maker) for instant analysis. Reports render inline with markdown formatting and can be downloaded as `.md` files.

## Report Structure

1. **Executive Summary** — Verdict, global score (0–10), top risks, positive signals
2. **On-Chain Findings** — TVL, multi-chain deployment, funding history, security incidents, key events
3. **Third-Party Intelligence** — Analyst coverage, security audits, community sentiment
4. **Red Flags Register** — Severity-ranked risk indicators
5. **Data Limitations** — Data gaps and areas needing further investigation

## API Structure

The report pipeline produces a dict with these top-level keys:

| Key | Source | Description |
|-----|--------|-------------|
| `metadata` | DeFiLlama | Protocol name, slug, category, description, URL |
| `tvl` | DeFiLlama | Current TVL + historical time series |
| `chains` | DeFiLlama | Deployed chains with per-chain TVL |
| `funding` | DeFiLlama | Funding rounds, investors, total raised |
| `hacks` | DeFiLlama | Security incidents, losses, returned funds |
| `hallmarks` | DeFiLlama | Key protocol events timeline |
| `analyst_coverage` | Web Research | Articles and research reports |
| `audit_security` | Web Research | Audit reports and bug bounty info |
| `community_sentiment` | Web Research | Sentiment analysis and governance activity |
| `red_flags` | Web Research | Risk indicators and severity ratings |

## Project Files

```
4.defiAgent/
  main.py              CLI entry point
  web.py               Web UI server (port 8000)
  defillama.py         DeFiLlama API client with caching + fuzzy resolution
  report.py            Structured report builder
  markdown_report.py   Markdown renderer
  web_research.py      Web research module (template data)
  requirements.txt     Python dependencies
  reports/             Generated .md reports (gitignored)
```

## Current Status

- **DeFiLlama data**: Live — TVL, chains, funding, hacks, hallmarks
- **Web research**: Template data from Bitcoineo research — live source integration planned
- **Global Score**: Synthesizes TVL, security, risk, audits, and funding into a 0–10 rating

## Credits

Built by [Bitcoineo](https://bitcoineo.com). Protocol data from [DeFiLlama](https://defillama.com).
