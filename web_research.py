"""Web research module — Bitcoineo research templates.

Each function returns structured template data so the report pipeline
runs end-to-end.  Live source integration is planned; every response
includes "data_source": "placeholder" so consumers can distinguish
template data from verified sources.
"""


def search_analyst_coverage(protocol_name: str) -> dict:
    """Search for analyst articles and research coverage on a protocol."""
    return {
        "articles": [
            {
                "title": f"{protocol_name} Protocol: Deep Dive Analysis",
                "source": "Messari",
                "url": "https://example.com/placeholder-messari",
                "date": "2025-12-15",
                "summary": f"Comprehensive overview of {protocol_name}'s architecture, tokenomics, and competitive positioning.",
            },
            {
                "title": f"The State of {protocol_name} in 2025",
                "source": "Delphi Digital",
                "url": "https://example.com/placeholder-delphi",
                "date": "2025-11-20",
                "summary": f"Analysis of {protocol_name}'s growth trajectory and market share trends.",
            },
        ],
        "data_source": "placeholder",
    }


def search_audit_reports(protocol_name: str) -> dict:
    """Search for security audits and bug-bounty programmes for a protocol."""
    return {
        "audits": [
            {
                "auditor": "Trail of Bits",
                "date": "2025-09-01",
                "scope": f"{protocol_name} core contracts v3",
                "findings_summary": "2 medium, 5 low-severity findings — all addressed before deployment.",
                "report_url": "https://example.com/placeholder-tob-audit",
            },
            {
                "auditor": "OpenZeppelin",
                "date": "2025-06-15",
                "scope": f"{protocol_name} governance module",
                "findings_summary": "1 high, 3 medium findings — high-severity issue patched within 48 h.",
                "report_url": "https://example.com/placeholder-oz-audit",
            },
        ],
        "bug_bounty": {
            "active": True,
            "max_payout": "$1,000,000",
            "platform": "Immunefi",
        },
        "data_source": "placeholder",
    }


def search_community_sentiment(protocol_name: str) -> dict:
    """Search community channels for sentiment around a protocol."""
    return {
        "overall_sentiment": "positive",
        "key_topics": [
            {
                "topic": "Protocol upgrades",
                "sentiment": "positive",
                "summary": f"Community is optimistic about {protocol_name}'s upcoming v4 upgrade roadmap.",
            },
            {
                "topic": "Token utility",
                "sentiment": "mixed",
                "summary": f"Ongoing debate about expanding {protocol_name} token utility and fee-sharing mechanisms.",
            },
            {
                "topic": "Cross-chain expansion",
                "sentiment": "positive",
                "summary": f"Strong support for {protocol_name}'s deployment on additional L2 networks.",
            },
        ],
        "governance_activity": {
            "recent_proposals": 5,
            "voter_participation": "12.3%",
        },
        "data_source": "placeholder",
    }


def search_red_flags(protocol_name: str) -> dict:
    """Search for potential red flags and risk indicators for a protocol."""
    return {
        "flags": [
            {
                "severity": "medium",
                "category": "Centralization",
                "description": f"{protocol_name} admin multisig retains upgrade authority over core contracts.",
                "source": "Contract analysis",
            },
            {
                "severity": "low",
                "category": "Dependency",
                "description": f"{protocol_name} relies on a single oracle provider for price feeds.",
                "source": "Architecture review",
            },
        ],
        "risk_level": "medium",
        "data_source": "placeholder",
    }
