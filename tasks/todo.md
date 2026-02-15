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

## Phase 4: Bitcoineo Branding, Web UI, and Project Documentation
- [x] Rebrand `web_research.py` — data_source → `bitcoineo_placeholder`, URLs → `bitcoineo.com/research/*`, sources → Bitcoineo Research/Insights
- [x] Update `markdown_report.py` — sentinel checks, confidence reason, footer to Bitcoineo branding
- [x] Create `web.py` — stdlib HTTP server, glassmorphism UI, `/api/report` endpoint, marked.js rendering
- [x] Create `.gitignore` — exclude `.claude/`, `__pycache__/`, `reports/`, `.env`, `.DS_Store`
- [x] Create `README.md` — project overview, CLI/web usage, API structure, tech stack, file tree
- [x] Verify: CLI report footer says "Bitcoineo", no `example.com` in output
- [x] Verify: Web UI serves on localhost:8000, generates reports, handles errors, returns proper JSON
- [x] Verify: `.gitignore` has all required entries

## Phase 5: Mobbin-inspired Hero Landing Page Redesign
- [x] Replace HTML_PAGE with hero layout: full-viewport hero section + state container
- [x] Add Playfair Display 700 serif for hero headline (64px)
- [x] Near-white gradient background (`#fafafa → #f5f3f0 → #f7f8fc`)
- [x] Top-bar centered search input with magnifying glass SVG + "Enter" kbd badge
- [x] Announcement pills ("Live DeFiLlama Data", "500+ Protocols")
- [x] Dual CTAs: dark fill "Generate Report" + outlined "Start Exploring"
- [x] 6 floating protocol cards with letter-icons, color-coded, `@keyframes float` animation
- [x] Trust bar ("Powered by DeFiLlama · Bitcoineo Research")
- [x] Updated `showView()` to toggle hero-section vs state-container
- [x] Responsive: 3 breakpoints (desktop/960px/640px), floating cards hidden on mobile
- [x] Python server code untouched, syntax verified

## Phase 6: Hero Simplification — Search-Focused, Logos, Social Buttons
- [x] Remove decorative clutter: pills, floating cards, trust bar, subtitle, dual CTAs, kbd badge
- [x] Oversized search bar (56px) with integrated Generate button
- [x] Protocol cards with inline SVG logos (Aave, Lido, Ethena, Uniswap, Maker)
- [x] Rounded floating social buttons (X/Twitter, GitHub) — fixed bottom-right
- [x] Entrance animations: staggered fadeUp, generate pulse, subtle bg gradient shift
- [x] Simplified footer: "Powered by DeFiLlama · Bitcoineo Research"
- [x] Responsive breakpoint (≤640px): smaller title, full-width search, compact cards
- [x] Update README.md with new UI description
- [ ] Verify: all flows work (generate, download, new report, error handling, responsive)
