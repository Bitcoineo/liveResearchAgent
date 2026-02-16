"""DeFi research agent — DeFiLlama data + web research reports."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from defillama import DefiLlamaClient, DefiLlamaAPIError, ProtocolNotFoundError
from markdown_report import render_markdown
from report import build_report
from web_research import (
    search_analyst_coverage,
    search_audit_reports,
    search_community_sentiment,
    search_red_flags,
)


def run_report(client, protocol_name, tvl_days=180, verified_only=True):
    """Orchestrate API calls and build a structured report dict."""
    meta = client.resolve_protocol(protocol_name)
    detail = client.get_protocol_detail(meta["slug"])

    child_names = [c["name"] for c in meta["children"]]
    hacks = client.find_hacks_for_protocol(meta["name"], child_names)

    web_research = None
    if not verified_only:
        web_research = {
            "analyst_coverage": search_analyst_coverage(meta["name"], protocol_detail=detail),
            "audit_reports": search_audit_reports(meta["name"]),
            "community_sentiment": search_community_sentiment(meta["name"], protocol_detail=detail),
            "red_flags": search_red_flags(meta["name"], protocol_detail=detail, hacks=hacks),
        }

    return build_report(detail, meta, hacks, tvl_history_days=tvl_days, web_research=web_research, verified_only=verified_only)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a DeFi protocol research report from DeFiLlama data."
    )
    parser.add_argument("protocol", help="Protocol name (e.g., 'aave', 'uniswap', 'lido')")
    parser.add_argument("--days", type=int, default=180, help="Days of TVL history (default: 180)")
    parser.add_argument("--full", action="store_true", help="Include web research template sections (default: verified on-chain data only)")
    parser.add_argument("--json", action="store_true", dest="raw_json", help="Output raw JSON")
    args = parser.parse_args()

    client = DefiLlamaClient()

    try:
        report = run_report(client, args.protocol, tvl_days=args.days, verified_only=not args.full)
    except ProtocolNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except DefiLlamaAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Save markdown report to reports/ directory
    md = render_markdown(report)
    slug = report["metadata"]["slug"]
    filename = f"{slug}-{date.today().isoformat()}.md"
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / filename
    report_path.write_text(md)
    print(f"Report saved to {report_path}", file=sys.stderr)

    if args.raw_json:
        print(json.dumps(report))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
