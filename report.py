"""Report builder: transforms raw DeFiLlama data into a structured report dict."""

from datetime import datetime, timezone

from defillama import AGGREGATE_TVL_KEYS


def build_report(protocol_detail, protocol_meta, hacks, tvl_history_days=30, web_research=None):
    """Build a structured report dict from raw API data.

    Args:
        protocol_detail: Response from /protocol/{slug}
        protocol_meta: Resolution dict from resolve_protocol()
        hacks: Filtered hack records for this protocol
        tvl_history_days: Number of days of TVL history to include
        web_research: Optional dict with keys analyst_coverage, audit_reports,
                      community_sentiment, red_flags from the web_research module
    """
    report = {
        "metadata": _build_metadata(protocol_detail, protocol_meta),
        "tvl": _build_tvl_section(protocol_detail, tvl_history_days),
        "chains": _build_chains_section(protocol_detail),
        "funding": _build_funding_section(protocol_detail),
        "hacks": _build_hacks_section(hacks),
        "hallmarks": _build_hallmarks(protocol_detail),
    }

    if web_research is not None:
        report["analyst_coverage"] = _build_analyst_coverage(web_research["analyst_coverage"])
        report["audit_security"] = _build_audit_security(web_research["audit_reports"])
        report["community_sentiment"] = _build_community_sentiment(web_research["community_sentiment"])
        report["red_flags"] = _build_red_flags(web_research["red_flags"])

    return report


def _build_metadata(detail, meta):
    return {
        "protocol_name": meta["name"],
        "slug": meta["slug"],
        "description": detail.get("description", ""),
        "url": detail.get("url", ""),
        "logo": detail.get("logo", ""),
        "category": meta.get("category") or detail.get("category") or "Unknown",
        "is_parent_protocol": meta["is_parent"],
        "child_protocols": [c["name"] for c in meta.get("children", [])],
        "queried_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _build_tvl_section(detail, history_days):
    tvl_history = detail.get("tvl", [])

    # Current TVL is the last entry
    current_tvl = tvl_history[-1]["totalLiquidityUSD"] if tvl_history else 0.0

    # Slice to requested number of days
    recent = tvl_history[-history_days:] if tvl_history else []

    # Resample to monthly (last entry per calendar month)
    monthly = {}
    for entry in recent:
        iso = _unix_to_iso_date(entry["date"])
        month_key = iso[:7]  # "YYYY-MM"
        monthly[month_key] = {"date": iso, "tvl_usd": entry["totalLiquidityUSD"]}

    return {
        "current_tvl_usd": current_tvl,
        "tvl_history": list(monthly.values()),
    }


def _build_chains_section(detail):
    current_chain_tvls = detail.get("currentChainTvls", {})

    # Filter to base chain names only
    chain_tvl = {}
    for key, value in current_chain_tvls.items():
        if "-" in key:
            continue
        if key.lower() in AGGREGATE_TVL_KEYS:
            continue
        chain_tvl[key] = value

    # Sort by TVL descending
    sorted_chains = dict(sorted(chain_tvl.items(), key=lambda x: x[1], reverse=True))

    return {
        "deployed_chains": list(sorted_chains.keys()),
        "chain_tvl": sorted_chains,
    }


def _build_funding_section(detail):
    raises = detail.get("raises", []) or []

    rounds = sorted(
        [
            {
                "date": _unix_to_iso_date(r["date"]),
                "round_type": r.get("round"),
                "amount_usd_millions": r.get("amount"),
                "lead_investors": r.get("leadInvestors", []) or [],
                "other_investors": r.get("otherInvestors", []) or [],
                "valuation": r.get("valuation"),
                "source_url": r.get("source", ""),
            }
            for r in raises
        ],
        key=lambda x: x["date"],
    )

    total = sum(r["amount_usd_millions"] or 0 for r in rounds)

    return {
        "total_raised_usd_millions": total,
        "rounds": rounds,
    }


def _build_hacks_section(hacks):
    incidents = sorted(
        [
            {
                "date": _unix_to_iso_date(h["date"]),
                "amount_lost_usd": h.get("amount", 0) or 0,
                "chain": h.get("chain", []),
                "classification": h.get("classification", ""),
                "technique": h.get("technique", ""),
                "returned_funds_usd": h.get("returnedFunds") or 0,
                "source_url": h.get("source", ""),
            }
            for h in hacks
        ],
        key=lambda x: x["date"],
        reverse=True,
    )

    return {
        "total_hacks": len(incidents),
        "total_amount_lost_usd": sum(i["amount_lost_usd"] for i in incidents),
        "total_amount_returned_usd": sum(i["returned_funds_usd"] for i in incidents),
        "incidents": incidents,
    }


def _build_hallmarks(detail):
    raw = detail.get("hallmarks") or []
    return [
        {"date": _unix_to_iso_date(entry[0]), "event": entry[1]}
        for entry in raw
        if isinstance(entry, (list, tuple)) and len(entry) >= 2
    ]


def _build_analyst_coverage(data):
    """Format analyst coverage data for the report."""
    return data


def _build_audit_security(data):
    """Format audit and security data for the report."""
    return data


def _build_community_sentiment(data):
    """Format community sentiment data for the report."""
    return data


def _build_red_flags(data):
    """Format red flags data for the report."""
    return data


def _unix_to_iso_date(ts):
    """Convert unix timestamp to YYYY-MM-DD string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
