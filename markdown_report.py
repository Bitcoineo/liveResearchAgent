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
    risk_level = red_flags.get("risk_level", "unknown")

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

    # Confidence level
    confidence, confidence_reason = _calculate_confidence(report)

    # Risks
    risks = _extract_top_risks(report)

    # Positive signals
    signals = _extract_positive_signals(report)

    lines = [
        "## Executive Summary",
        "",
        f"**Verdict**: {verdict}",
        "",
        f"**Confidence Level**: {confidence} — {confidence_reason}",
        "",
        "**Top Risks**:",
    ]
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


def _calculate_confidence(report: dict) -> tuple:
    """Return (level, reason) based on data completeness."""
    placeholder_sections = []
    for key in ("analyst_coverage", "audit_security", "community_sentiment", "red_flags"):
        section = report.get(key, {})
        if section.get("data_source") == "placeholder":
            placeholder_sections.append(key)

    if not placeholder_sections:
        return ("High", "All data sections populated with live data")
    if len(placeholder_sections) <= 2:
        return ("Medium", "Some third-party data sources are not yet live")
    return ("Low", "Third-party intelligence sections use placeholder data — real web research not yet wired in")


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
        signals.append("Positive community sentiment across key discussion topics")

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
        recent = history[-5:]  # last 5 entries for readability
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
        articles = analyst.get("articles", [])
        if articles:
            for a in articles:
                title = a["title"]
                url = a.get("url", "")
                source = a.get("source", "Unknown")
                date = _fmt_date(a.get("date", ""))
                summary = a.get("summary", "")
                if url:
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
        f"**Overall Risk Level**: {risk_level}",
        "",
    ]

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
            questions.append(f"**{label}**: Using placeholder data — real web research not yet implemented")

    # Check for empty DeFiLlama sections
    if report.get("funding", {}).get("total_raised_usd_millions", 0) == 0:
        questions.append("**Funding history**: No funding rounds found in DeFiLlama data — may be unreported")
    if report.get("hacks", {}).get("total_hacks", 0) == 0:
        questions.append("**Security incidents**: No hacks found — protocol may be too new or data may be incomplete")

    lines = ["## Unresolved Questions", ""]

    if questions:
        lines.append("The following aspects could not be fully verified:")
        lines.append("")
        for q in questions:
            lines.append(f"- {q}")
        lines.append("")
    else:
        lines.append("No significant unresolved questions — all data sections populated with live data.")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_footer(metadata: dict) -> str:
    queried = _fmt_date(metadata.get("queried_at", "")[:10])
    return f"*Report generated on {queried} by DeFi Research Agent. Data sources: DeFiLlama API, Web Research (placeholder).*\n"
