"""Markdown report renderer — transforms a structured report dict into a .md file."""

from datetime import datetime


def render_markdown(report: dict) -> str:
    """Render a full report dict as a formatted markdown string."""
    sections = [
        _render_header(report["metadata"]),
        _render_executive_summary(report),
        _render_onchain_findings(report),
        _render_third_party_intel(report),
        _render_red_flags(report.get("red_flags")),
        _render_unresolved_questions(report),
        _render_footer(report["metadata"]),
    ]
    return "\n".join(s for s in sections if s)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _fmt_usd(amount: float) -> str:
    """Format dollar amounts: $27.7B, $45.3M, $8.5K, $750."""
    if amount is None or amount == 0:
        return "$0"
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    if abs_amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if abs_amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:,.0f}"


def _fmt_date(iso_date: str) -> str:
    """Convert 'YYYY-MM-DD' to 'Mon DD, YYYY'. Pass through on failure."""
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return iso_date or "N/A"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_header(metadata: dict) -> str:
    name = metadata["protocol_name"]
    category = metadata.get("category", "Unknown")
    url = metadata.get("url", "")
    description = metadata.get("description", "")
    queried_at = _fmt_date(metadata.get("queried_at", "")[:10])

    children = metadata.get("child_protocols", [])
    child_line = f"**Sub-protocols**: {', '.join(children)}" if children else ""

    lines = [
        f"# {name} — DeFi Research Report",
        "",
        f"**Category**: {category}  ",
        f"**Report Date**: {queried_at}  ",
    ]
    if url:
        lines.append(f"**Website**: [{url}]({url})  ")
    if child_line:
        lines.append(f"{child_line}  ")
    lines.append("")
    if description:
        lines.append(f"> {description}")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_executive_summary(report: dict) -> str:
    metadata = report["metadata"]
    tvl = report.get("tvl", {})
    chains = report.get("chains", {})
    red_flags = report.get("red_flags", {})

    name = metadata["protocol_name"]
    category = metadata.get("category", "Unknown")
    current_tvl = _fmt_usd(tvl.get("current_tvl_usd", 0))
    chain_count = len(chains.get("deployed_chains", []))
    risk_level = red_flags.get("risk_level", "unknown") if red_flags else "unknown"

    # Verdict
    if risk_level in ("low",):
        tone = "strong fundamentals with limited risk indicators"
    elif risk_level in ("medium",):
        tone = "solid fundamentals with moderate risk factors worth monitoring"
    elif risk_level in ("high", "critical"):
        tone = "significant risk factors that warrant careful evaluation"
    else:
        tone = "a profile that requires further investigation"

    verdict = (
        f"{name} is a {category} protocol with {current_tvl} in TVL "
        f"deployed across {chain_count} chain{'s' if chain_count != 1 else ''}. "
        f"Based on available data, the protocol shows {tone}."
    )

    # Global score
    score, breakdown = _calculate_global_score(report)
    label = _score_label(score)

    # Risks
    risks = _extract_top_risks(report)

    # Positive signals
    signals = _extract_positive_signals(report)

    lines = [
        "## Executive Summary",
        "",
        f"**Verdict**: {verdict}",
        "",
        f"**Global Score**: {score}/10 ({label})",
        "",
    ]

    # Score breakdown
    lines.append("**Score Breakdown**:")
    lines.append("")
    for dimension, value in breakdown.items():
        sign = "+" if value >= 0 else ""
        lines.append(f"- {dimension}: {sign}{value}")
    lines.append("")

    lines.append("**Top Risks**:")
    for i, risk in enumerate(risks[:3], 1):
        lines.append(f"{i}. {risk}")
    if not risks:
        lines.append("1. No significant risks identified from available data")
    lines.append("")
    lines.append("**Positive Signals**:")
    for i, signal in enumerate(signals[:3], 1):
        lines.append(f"{i}. {signal}")
    if not signals:
        lines.append("1. Insufficient data to identify positive signals")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _calculate_global_score(report: dict) -> tuple:
    """Return (score, breakdown) synthesizing protocol quality metrics.

    Uses continuous scales with diminishing returns instead of step functions.
    On-chain dimensions (always available):
      TVL strength (0–2.5), Multi-chain (0–1.5), Security record (−3–2),
      Funding (0–1.5).
    Web-research dimensions:
      Risk profile (−2–2), Audit & bounty (0–1.5).
    Raw sum is normalized to 0–10.
    """
    import math
    breakdown = {}

    # --- TVL strength (0–2.5) — logarithmic, diminishing above $10B ---
    tvl = report.get("tvl", {}).get("current_tvl_usd", 0)
    if tvl <= 0:
        breakdown["TVL strength"] = 0.0
    elif tvl >= 10_000_000_000:
        extra = min(0.5, 0.5 * math.log10(tvl / 10_000_000_000) / math.log10(10))
        breakdown["TVL strength"] = round(2.0 + extra, 2)
    elif tvl >= 1_000_000_000:
        breakdown["TVL strength"] = round(1.5 + 0.5 * (tvl - 1e9) / (10e9 - 1e9), 2)
    elif tvl >= 100_000_000:
        breakdown["TVL strength"] = round(1.0 + 0.5 * (tvl - 1e8) / (1e9 - 1e8), 2)
    elif tvl >= 1_000_000:
        breakdown["TVL strength"] = round(0.3 + 0.7 * (tvl - 1e6) / (1e8 - 1e6), 2)
    else:
        breakdown["TVL strength"] = 0.1

    # --- Multi-chain (0–1.5) — continuous, diminishing returns ---
    chain_count = len(report.get("chains", {}).get("deployed_chains", []))
    if chain_count <= 1:
        breakdown["Multi-chain"] = 0.0
    elif chain_count <= 3:
        breakdown["Multi-chain"] = round(0.3 * chain_count, 2)
    elif chain_count <= 10:
        breakdown["Multi-chain"] = round(0.9 + 0.06 * (chain_count - 3), 2)
    else:
        breakdown["Multi-chain"] = min(1.5, round(1.32 + 0.02 * (chain_count - 10), 2))

    # --- Security record (−3 to 2) — penalty-based, scaled by loss ---
    hacks = report.get("hacks", {})
    total_lost = hacks.get("total_amount_lost_usd", 0)
    total_returned = hacks.get("total_amount_returned_usd", 0)
    hack_count = hacks.get("total_hacks", 0)
    if hack_count == 0:
        breakdown["Security record"] = 2.0
    else:
        net_loss = max(0, total_lost - total_returned)
        penalty = 0.5  # base penalty for any hack
        if net_loss >= 100_000_000:
            penalty += 2.5
        elif net_loss >= 10_000_000:
            penalty += 1.5
        elif net_loss >= 1_000_000:
            penalty += 0.8
        else:
            penalty += 0.3
        penalty += 0.3 * min(hack_count - 1, 3)
        breakdown["Security record"] = round(max(-3.0, 2.0 - penalty), 2)

    # --- Funding (0–1.5) — graduated ---
    total_raised = report.get("funding", {}).get("total_raised_usd_millions", 0)
    if total_raised <= 0:
        breakdown["Funding"] = 0.0
    elif total_raised >= 100:
        breakdown["Funding"] = 1.5
    elif total_raised >= 50:
        breakdown["Funding"] = 1.2
    elif total_raised >= 10:
        breakdown["Funding"] = 0.8
    else:
        breakdown["Funding"] = 0.4

    # --- Web-research dimensions ---
    # Risk profile — per-flag penalty
    flags = report.get("red_flags", {}).get("flags", [])
    severity_penalties = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}
    flag_penalty = sum(severity_penalties.get(f.get("severity", "low"), 0.5) for f in flags)
    breakdown["Risk profile"] = round(max(-2.0, 2.0 - flag_penalty), 2)

    # Audit & bounty
    audit_sec = report.get("audit_security", {})
    has_bounty = audit_sec.get("bug_bounty", {}).get("active", False)
    has_audits = len(audit_sec.get("audits", [])) > 0
    if has_bounty and has_audits:
        breakdown["Audit & bounty"] = 1.5
    elif has_audits:
        breakdown["Audit & bounty"] = 1.0
    elif has_bounty:
        breakdown["Audit & bounty"] = 0.5
    else:
        breakdown["Audit & bounty"] = 0.0

    # --- Normalize to 0–10 ---
    raw_total = sum(breakdown.values())
    max_possible = 11.0
    score = round(max(0, min(10, (raw_total / max_possible) * 10)), 1)

    return (score, breakdown)


def _score_label(score: float) -> str:
    """Return a qualitative label for the global score."""
    if score >= 8.0:
        return "Excellent"
    if score >= 6.0:
        return "Good"
    if score >= 4.0:
        return "Fair"
    return "Weak"


def _extract_top_risks(report: dict) -> list:
    """Gather risk signals from across the report, sorted by importance."""
    risks = []

    # Red flags (severity-sorted)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    flags = report.get("red_flags", {}).get("flags", [])
    sorted_flags = sorted(flags, key=lambda f: severity_order.get(f.get("severity", "low"), 3))
    for flag in sorted_flags:
        risks.append(f"[{flag['severity'].upper()}] {flag['category']}: {flag['description']}")

    # Hack history
    hacks = report.get("hacks", {})
    if hacks.get("total_amount_lost_usd", 0) > 0:
        lost = _fmt_usd(hacks["total_amount_lost_usd"])
        risks.append(f"Historical security incidents with {lost} in total losses")

    # No funding
    funding = report.get("funding", {})
    if funding.get("total_raised_usd_millions", 0) == 0:
        risks.append("No publicly recorded funding rounds")

    return risks


def _extract_positive_signals(report: dict) -> list:
    """Gather positive signals from across the report."""
    signals = []

    # TVL
    tvl = report.get("tvl", {}).get("current_tvl_usd", 0)
    if tvl >= 1_000_000_000:
        signals.append(f"Strong TVL of {_fmt_usd(tvl)} indicates significant market trust")
    elif tvl >= 100_000_000:
        signals.append(f"Healthy TVL of {_fmt_usd(tvl)} shows established market presence")

    # Multi-chain
    chain_count = len(report.get("chains", {}).get("deployed_chains", []))
    if chain_count >= 5:
        signals.append(f"Broad multi-chain deployment across {chain_count} networks")
    elif chain_count >= 2:
        signals.append(f"Multi-chain presence across {chain_count} networks")

    # Bug bounty
    audit = report.get("audit_security", {})
    bounty = audit.get("bug_bounty", {})
    if bounty.get("active"):
        signals.append(f"Active bug bounty program on {bounty.get('platform', 'N/A')} (max {bounty.get('max_payout', 'N/A')})")

    # Community sentiment
    sentiment = report.get("community_sentiment", {})
    if sentiment.get("overall_sentiment") == "positive":
        signals.append("Active developer community with healthy commit and contributor metrics")

    # Funding
    total_raised = report.get("funding", {}).get("total_raised_usd_millions", 0)
    if total_raised > 0:
        signals.append(f"Raised ${total_raised:.0f}M in funding from institutional investors")

    return signals


def _render_onchain_findings(report: dict) -> str:
    lines = ["## On-Chain Findings", ""]

    # --- TVL ---
    tvl = report.get("tvl", {})
    current = _fmt_usd(tvl.get("current_tvl_usd", 0))
    history = tvl.get("tvl_history", [])

    lines.append("### Total Value Locked")
    lines.append("")
    lines.append(f"**Current TVL**: {current}")
    lines.append("")

    if history:
        recent = history[-6:]  # last 6 months for readability
        lines.append("| Date | TVL |")
        lines.append("|------|-----|")
        for entry in recent:
            lines.append(f"| {_fmt_date(entry['date'])} | {_fmt_usd(entry['tvl_usd'])} |")
        lines.append("")

    # --- Chains ---
    chains = report.get("chains", {})
    deployed = chains.get("deployed_chains", [])
    chain_tvl = chains.get("chain_tvl", {})
    total_chain_tvl = sum(chain_tvl.values()) or 1  # avoid div by zero

    lines.append("### Multi-Chain Deployment")
    lines.append("")
    lines.append(f"**Active on {len(deployed)} chain{'s' if len(deployed) != 1 else ''}**: {', '.join(deployed)}")
    lines.append("")

    if chain_tvl:
        lines.append("| Chain | TVL | Share |")
        lines.append("|-------|-----|-------|")
        for chain, value in chain_tvl.items():
            pct = (value / total_chain_tvl) * 100
            lines.append(f"| {chain} | {_fmt_usd(value)} | {pct:.1f}% |")
        lines.append("")

    # --- Funding ---
    funding = report.get("funding", {})
    rounds = funding.get("rounds", [])
    total_raised = funding.get("total_raised_usd_millions", 0)

    lines.append("### Funding History")
    lines.append("")
    lines.append(f"**Total Raised**: ${total_raised:.0f}M")
    lines.append("")

    if rounds:
        lines.append("| Date | Round | Amount | Lead Investors |")
        lines.append("|------|-------|--------|----------------|")
        for r in rounds:
            date = _fmt_date(r["date"])
            rtype = r.get("round_type") or "N/A"
            amount = f"${r['amount_usd_millions']:.0f}M" if r.get("amount_usd_millions") else "N/A"
            leads = ", ".join(r.get("lead_investors", [])) or "N/A"
            lines.append(f"| {date} | {rtype} | {amount} | {leads} |")
        lines.append("")
    else:
        lines.append("No funding rounds on record.")
        lines.append("")

    # --- Hacks ---
    hacks = report.get("hacks", {})
    incidents = hacks.get("incidents", [])

    lines.append("### Security Incidents")
    lines.append("")
    lines.append(f"**Total Incidents**: {hacks.get('total_hacks', 0)}  ")
    lines.append(f"**Total Lost**: {_fmt_usd(hacks.get('total_amount_lost_usd', 0))}  ")
    lines.append(f"**Funds Returned**: {_fmt_usd(hacks.get('total_amount_returned_usd', 0))}")
    lines.append("")

    if incidents:
        lines.append("| Date | Amount Lost | Chain | Classification | Returned |")
        lines.append("|------|------------|-------|----------------|----------|")
        for inc in incidents:
            date = _fmt_date(inc["date"])
            lost = _fmt_usd(inc["amount_lost_usd"])
            chain = ", ".join(inc["chain"]) if isinstance(inc["chain"], list) else str(inc["chain"])
            classification = inc.get("classification", "N/A")
            returned = _fmt_usd(inc["returned_funds_usd"])
            lines.append(f"| {date} | {lost} | {chain} | {classification} | {returned} |")
        lines.append("")
    else:
        lines.append("No security incidents found in DeFiLlama database.")
        lines.append("")

    # --- Hallmarks ---
    hallmarks = report.get("hallmarks", [])
    if hallmarks:
        lines.append("### Key Events Timeline")
        lines.append("")
        for h in hallmarks:
            lines.append(f"- **{_fmt_date(h['date'])}**: {h['event']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


_TEMPLATE_BANNER = "> ⚠️ **Unverified Data** — This section contains data that could not be verified against live sources."


def _is_placeholder_url(url: str) -> bool:
    """Return True if the URL points to a placeholder/example domain."""
    return "example.com" in url


def _render_third_party_intel(report: dict) -> str:
    analyst = report.get("analyst_coverage")
    audit = report.get("audit_security")
    sentiment = report.get("community_sentiment")

    # Skip entirely if no web research sections present
    if not any([analyst, audit, sentiment]):
        return ""

    lines = ["## Third-Party Intelligence", ""]

    # --- Analyst Coverage ---
    if analyst:
        lines.append("### Analyst Coverage")
        lines.append("")
        if analyst.get("data_source") == "placeholder":
            lines.append(_TEMPLATE_BANNER)
            lines.append("")
        articles = analyst.get("articles", [])
        if articles:
            for a in articles:
                title = a["title"]
                url = a.get("url", "")
                source = a.get("source", "Unknown")
                date = _fmt_date(a.get("date", ""))
                summary = a.get("summary", "")
                if url and not _is_placeholder_url(url):
                    lines.append(f"**[{title}]({url})** — {source} ({date})")
                else:
                    lines.append(f"**{title}** — {source} ({date})")
                lines.append(f"  {summary}")
                lines.append("")
        else:
            lines.append("No analyst coverage found.")
            lines.append("")

    # --- Audits ---
    if audit:
        lines.append("### Security & Audits")
        lines.append("")
        if audit.get("data_source") == "placeholder":
            lines.append(_TEMPLATE_BANNER)
            lines.append("")
        audits = audit.get("audits", [])
        if audits:
            lines.append("| Auditor | Date | Scope | Findings |")
            lines.append("|---------|------|-------|----------|")
            for a in audits:
                lines.append(
                    f"| {a['auditor']} | {_fmt_date(a['date'])} | {a['scope']} | {a['findings_summary']} |"
                )
            lines.append("")

        bounty = audit.get("bug_bounty", {})
        if bounty:
            status = "Active" if bounty.get("active") else "Inactive"
            lines.append(f"**Bug Bounty Program**: {status}  ")
            lines.append(f"**Platform**: {bounty.get('platform', 'N/A')}  ")
            lines.append(f"**Max Payout**: {bounty.get('max_payout', 'N/A')}")
            lines.append("")

    # --- Community Sentiment ---
    if sentiment:
        lines.append("### Community Sentiment")
        lines.append("")
        if sentiment.get("data_source") == "placeholder":
            lines.append(_TEMPLATE_BANNER)
            lines.append("")
        overall = sentiment.get("overall_sentiment", "unknown").capitalize()
        lines.append(f"**Overall Sentiment**: {overall}")
        lines.append("")

        topics = sentiment.get("key_topics", [])
        if topics:
            lines.append("| Topic | Sentiment | Summary |")
            lines.append("|-------|-----------|---------|")
            for t in topics:
                lines.append(f"| {t['topic']} | {t['sentiment'].capitalize()} | {t['summary']} |")
            lines.append("")

        gov = sentiment.get("governance_activity", {})
        if gov:
            lines.append(f"**Recent Governance Proposals**: {gov.get('recent_proposals', 'N/A')}  ")
            lines.append(f"**Voter Participation**: {gov.get('voter_participation', 'N/A')}")
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_red_flags(red_flags: dict | None) -> str:
    if not red_flags:
        return ""

    risk_level = red_flags.get("risk_level", "unknown").upper()
    flags = red_flags.get("flags", [])

    lines = [
        "## Red Flags Register",
        "",
    ]

    if red_flags.get("data_source") == "placeholder":
        lines.append(_TEMPLATE_BANNER)
        lines.append("")

    lines.append(f"**Overall Risk Level**: {risk_level}")
    lines.append("")

    if flags:
        for i, flag in enumerate(flags, 1):
            severity = flag["severity"].upper()
            category = flag["category"]
            desc = flag["description"]
            source = flag.get("source", "N/A")
            lines.append(f"{i}. **[{severity}] {category}** — {desc} *(Source: {source})*")
        lines.append("")
    else:
        lines.append("No red flags identified.")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_unresolved_questions(report: dict) -> str:
    questions = []

    # Check web research sections for placeholder data
    section_labels = {
        "analyst_coverage": "Analyst coverage and research articles",
        "audit_security": "Security audit reports and bug bounty verification",
        "community_sentiment": "Community sentiment analysis",
        "red_flags": "Red flag detection and risk assessment",
    }
    for key, label in section_labels.items():
        section = report.get(key, {})
        if section.get("data_source") == "placeholder":
            questions.append(f"**{label}**: Data source unavailable — could not be verified against live sources")

    # Check for empty DeFiLlama sections
    if report.get("funding", {}).get("total_raised_usd_millions", 0) == 0:
        questions.append("**Funding history**: No publicly recorded funding rounds in DeFiLlama")
    if report.get("hacks", {}).get("total_hacks", 0) == 0:
        questions.append("**Security incidents**: No security incidents recorded in DeFiLlama")

    lines = ["## Data Limitations", ""]

    if questions:
        lines.append("The following data sources have limited coverage:")
        lines.append("")
        for q in questions:
            lines.append(f"- {q}")
        lines.append("")
    else:
        lines.append("All data sections verified against live sources.")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_footer(metadata: dict) -> str:
    queried = _fmt_date(metadata.get("queried_at", "")[:10])
    return f"*Report generated on {queried} by Bitcoineo DeFi Research Agent. Data sources: DeFiLlama API, Bitcoineo Research Network.*\n"
