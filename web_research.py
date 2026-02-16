"""Web research module — all functions return live data.

search_audit_reports() uses live data from GitHub (org-scoped search
across known audit firms).  Immunefi bug-bounty detection is attempted
but degrades gracefully (SPA, no public API).

search_red_flags() analyzes DeFiLlama protocol data and hack history
to produce real risk flags (chain concentration, TVL decline, age,
hack history, funding, contract verification via Etherscan).

search_community_sentiment() uses GitHub API for developer activity
metrics (commit frequency, open issues, contributors) and Snapshot
GraphQL for governance data (proposal counts, voter participation).

search_analyst_coverage() gathers coverage links from DeFiLlama
protocol metadata (website, Twitter, audit links) and GitHub README
parsing (documentation, governance, community links).
"""

import datetime
import re
import time
from urllib.parse import urlparse

import requests

# ---------------------------------------------------------------------------
# Shared HTTP configuration (reusable by all web research functions)
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
BACKOFF_BASE = 1.0
RATE_LIMIT_DELAY = 1.0  # minimum seconds between requests to the same domain

GITHUB_API_BASE = "https://api.github.com"
RAW_GITHUB_BASE = "https://raw.githubusercontent.com"
SNAPSHOT_GRAPHQL_URL = "https://hub.snapshot.org/graphql"

KNOWN_AUDIT_FIRMS = {
    "trailofbits": "Trail of Bits",
    "openzeppelin": "OpenZeppelin",
    "certora": "Certora",
    "consensys": "ConsenSys Diligence",
    "sherlock-audit": "Sherlock",
    "code-423n4": "Code4rena",
    "spearbit": "Spearbit",
    "peckshield": "PeckShield",
    "chainsecurity": "ChainSecurity",
    "sigmaprime": "Sigma Prime",
    "mixbytes": "MixBytes",
    "quantstamp": "Quantstamp",
    "cyfrin": "Cyfrin",
}

_session = requests.Session()
_session.headers.update({
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "BitcoineoResearchAgent/1.0",
})

_domain_last_request: dict[str, float] = {}


def _rate_limit_delay(url: str) -> None:
    """Enforce minimum delay between requests to the same domain."""
    domain = urlparse(url).netloc
    now = time.monotonic()
    last = _domain_last_request.get(domain, 0.0)
    elapsed = now - last
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _domain_last_request[domain] = time.monotonic()


def _fetch_with_retry(url: str, params: dict | None = None) -> requests.Response:
    """GET with retry + exponential backoff.

    Retries on ConnectionError, Timeout, HTTP 403 (rate limit), and 5xx.
    Does NOT retry 404 or other 4xx — those propagate immediately.
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            _rate_limit_delay(url)
            resp = _session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 403 or resp.status_code >= 500:
                last_exc = requests.HTTPError(
                    f"HTTP {resp.status_code} for {url}", response=resp
                )
                time.sleep(BACKOFF_BASE * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_BASE * (2 ** attempt))
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Private helpers for search_audit_reports
# ---------------------------------------------------------------------------

def _normalize_protocol_name(protocol_name: str) -> str:
    return protocol_name.strip().lower()


def _extract_auditor(repo: dict) -> str | None:
    """Return display name if the repo owner is a known audit firm."""
    owner = repo.get("owner", {}).get("login", "").lower()
    return KNOWN_AUDIT_FIRMS.get(owner)


def _extract_scope(repo: dict, protocol_name: str) -> str:
    """Build a scope string from the repo description or name."""
    desc = repo.get("description") or ""
    if desc:
        first_sentence = desc.split(". ")[0]
        return first_sentence[:120] + ("..." if len(first_sentence) > 120 else "")
    cleaned = repo.get("name", "").replace("-", " ").replace("_", " ")
    return f"{protocol_name} — {cleaned}"


def _search_github_audits(protocol_name: str) -> list[dict]:
    """Search GitHub for audit repos scoped to known audit firm orgs.

    Uses ``user:`` qualifiers so only repos owned by recognised firms
    are returned.  Companion repos (``-judging``, ``-findings``) are
    filtered out to avoid duplicates.
    """
    normalized = _normalize_protocol_name(protocol_name)
    user_qualifiers = " ".join(f"user:{org}" for org in KNOWN_AUDIT_FIRMS)
    query = f"{normalized} {user_qualifiers}"

    resp = _fetch_with_retry(
        f"{GITHUB_API_BASE}/search/repositories",
        params={"q": query, "sort": "updated", "per_page": 30},
    )
    data = resp.json()

    audits = []
    seen_urls: set[str] = set()

    for repo in data.get("items", []):
        repo_name = repo.get("name", "")

        # Skip companion / judging repos — they duplicate the main audit
        if repo_name.endswith(("-judging", "-findings")):
            continue

        auditor = _extract_auditor(repo)
        if auditor is None:
            continue

        html_url = repo.get("html_url", "")
        if html_url in seen_urls:
            continue
        seen_urls.add(html_url)

        updated = repo.get("updated_at", "")
        audits.append({
            "auditor": auditor,
            "date": updated[:10] if updated else "Unknown",
            "scope": _extract_scope(repo, protocol_name),
            "findings_summary": "See full report for details",
            "report_url": html_url,
        })

    return audits


def _fetch_immunefi_bounty(protocol_name: str) -> dict:
    """Try to get bug bounty info from Immunefi. Degrades gracefully."""
    default = {"active": False, "max_payout": "N/A", "platform": "N/A"}
    normalized = _normalize_protocol_name(protocol_name)

    urls = [
        f"https://immunefi.com/bug-bounty/{normalized}/",
        f"https://immunefi.com/bounty/{normalized}/",
    ]

    for url in urls:
        try:
            resp = _fetch_with_retry(url)
            content_type = resp.headers.get("Content-Type", "")

            if "application/json" in content_type:
                data = resp.json()
                max_payout = data.get("maxBounty") or data.get("maximumPayout")
                if isinstance(max_payout, (int, float)):
                    max_payout = f"${max_payout:,.0f}"
                return {
                    "active": True,
                    "max_payout": str(max_payout) if max_payout else "N/A",
                    "platform": "Immunefi",
                }

            if resp.status_code == 200:
                text = resp.text[:5000]
                if normalized in text.lower() and (
                    "bounty" in text.lower() or "reward" in text.lower()
                ):
                    return {
                        "active": True,
                        "max_payout": "N/A",
                        "platform": "Immunefi",
                    }
        except Exception:
            continue

    return default


# ---------------------------------------------------------------------------
# Private helpers for search_analyst_coverage
# ---------------------------------------------------------------------------

# URL-pattern and text-pattern pairs for categorising README links.
# Each key is a category name; value is (text_patterns, url_patterns).
_LINK_CATEGORIES: dict[str, tuple[list[str], list[str]]] = {
    "Documentation": (
        ["doc", "guide", "tutorial", "reference", "wiki"],
        ["docs.", "gitbook.io", "readthedocs", "/docs"],
    ),
    "Governance": (
        ["governance", "govern", "forum", "vote", "proposal"],
        ["governance.", "forum.", "snapshot.org", "tally.xyz"],
    ),
    "Discord": (["discord"], ["discord.gg", "discord.com"]),
    "Telegram": (["telegram"], ["t.me/"]),
    "Blog": (
        ["blog", "article", "announcement", "news", "update"],
        ["medium.com", "mirror.xyz", "blog.", "substack.com"],
    ),
    "Security": (
        ["security", "audit", "bug bounty", "bounty"],
        ["immunefi.com", "hackerone.com"],
    ),
    "Analytics": (
        ["analytics", "dashboard", "stats", "dune"],
        ["dune.com", "defillama.com", "debank.com"],
    ),
}


def _extract_markdown_links(text: str) -> list[tuple[str, str]]:
    """Extract ``[text](url)`` pairs from markdown text."""
    return re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', text)


def _categorize_link(text: str, url: str) -> str | None:
    """Return a category name if the link matches, else None."""
    text_lower = text.lower()
    url_lower = url.lower()
    for category, (text_patterns, url_patterns) in _LINK_CATEGORIES.items():
        for tp in text_patterns:
            if tp in text_lower:
                return category
        for up in url_patterns:
            if up in url_lower:
                return category
    return None


def _build_defillama_coverage(protocol_detail: dict) -> list[dict]:
    """Extract website, Twitter, and audit links from DeFiLlama detail."""
    articles: list[dict] = []

    url = protocol_detail.get("url")
    if url and isinstance(url, str):
        articles.append({
            "title": "Official Website",
            "source": "DeFiLlama",
            "url": url,
            "date": "",
            "summary": "Protocol homepage",
        })

    twitter = protocol_detail.get("twitter")
    if twitter and isinstance(twitter, str):
        handle = twitter.strip().lstrip("@")
        articles.append({
            "title": "Twitter / X",
            "source": "DeFiLlama",
            "url": f"https://x.com/{handle}",
            "date": "",
            "summary": f"Official Twitter account (@{handle})",
        })

    audit_links = protocol_detail.get("audit_links")
    if audit_links and isinstance(audit_links, list):
        for link in audit_links:
            if isinstance(link, str) and link.startswith("http"):
                articles.append({
                    "title": "Audit Report",
                    "source": "DeFiLlama",
                    "url": link,
                    "date": "",
                    "summary": "Audit report linked from protocol metadata",
                })

    return articles


def _fetch_readme_links(orgs: list[str]) -> list[dict]:
    """Fetch README from top-starred repo per org and extract categorised links.

    Uses 1 GitHub API call per org (repos list) + 1 free
    raw.githubusercontent.com fetch for the README.
    """
    today = datetime.date.today().isoformat()
    articles: list[dict] = []

    for org in orgs:
        try:
            resp = _fetch_with_retry(
                f"{GITHUB_API_BASE}/orgs/{org}/repos",
                params={"sort": "stars", "per_page": 1},
            )
            repos = resp.json()
            if not isinstance(repos, list) or not repos:
                continue

            repo_name = repos[0].get("name", "")
            default_branch = repos[0].get("default_branch", "main")
            if not repo_name:
                continue

            # Try fetching README (not an API call — raw.githubusercontent.com)
            readme_text = None
            branches = [default_branch] if default_branch not in ("main", "master") else []
            branches.extend(["main", "master", "HEAD"])
            # Deduplicate while preserving order
            seen_branches: list[str] = []
            for b in branches:
                if b not in seen_branches:
                    seen_branches.append(b)

            for branch in seen_branches:
                readme_url = f"{RAW_GITHUB_BASE}/{org}/{repo_name}/{branch}/README.md"
                try:
                    _rate_limit_delay(readme_url)
                    r = _session.get(readme_url, timeout=REQUEST_TIMEOUT)
                    if r.status_code == 200 and len(r.text) > 50:
                        readme_text = r.text
                        break
                except Exception:
                    continue

            if not readme_text:
                continue

            links = _extract_markdown_links(readme_text)
            for link_text, link_url in links:
                category = _categorize_link(link_text, link_url)
                if category is None:
                    continue
                articles.append({
                    "title": f"{category}: {link_text}",
                    "source": f"GitHub README ({org}/{repo_name})",
                    "url": link_url,
                    "date": today,
                    "summary": f"{category} link found in {org}/{repo_name} README",
                })
        except Exception:
            continue

    return articles


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def search_analyst_coverage(
    protocol_name: str,
    protocol_detail: dict | None = None,
) -> dict:
    """Gather coverage links from DeFiLlama metadata and GitHub READMEs.

    Returns website, social, audit, documentation, governance, and
    community links discovered from protocol metadata and top-repo READMEs.
    No article scraping — just verifies coverage exists and links to it.
    """
    if protocol_detail is None:
        return {"articles": [], "data_source": "no_protocol_detail"}

    sources: list[str] = []

    # Source 1: DeFiLlama metadata (0 API calls)
    defillama_articles = _build_defillama_coverage(protocol_detail)
    if defillama_articles:
        sources.append("defillama")

    # Source 2: GitHub README links (1 API call per org)
    readme_articles: list[dict] = []
    orgs = _extract_github_orgs(protocol_detail)
    if orgs:
        try:
            readme_articles = _fetch_readme_links(orgs)
            if readme_articles:
                sources.append("github")
        except Exception:
            pass

    # Merge: DeFiLlama first (higher authority), then README links
    all_articles = defillama_articles + readme_articles

    # Deduplicate by URL (DeFiLlama wins on conflicts)
    seen_urls: set[str] = set()
    unique_articles: list[dict] = []
    for article in all_articles:
        url = article["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    data_source = ", ".join(sources) if sources else "no_coverage_found"

    return {
        "articles": unique_articles,
        "data_source": data_source,
    }


def search_audit_reports(protocol_name: str) -> dict:
    """Search for security audits and bug-bounty programmes for a protocol."""
    audits: list[dict] = []
    sources: list[str] = []

    # Source 1: GitHub org-scoped search across known audit firms
    try:
        github_audits = _search_github_audits(protocol_name)
        if github_audits:
            audits.extend(github_audits)
            sources.append("github")
    except Exception:
        pass

    # Source 2: Immunefi bug bounty
    bug_bounty = {"active": False, "max_payout": "N/A", "platform": "N/A"}
    try:
        bug_bounty = _fetch_immunefi_bounty(protocol_name)
        if bug_bounty.get("active"):
            sources.append("immunefi")
    except Exception:
        pass

    # Sort audits by date descending
    audits.sort(key=lambda a: a.get("date", ""), reverse=True)

    return {
        "audits": audits,
        "bug_bounty": bug_bounty,
        "data_source": ", ".join(sources) if sources else "error",
    }


# ---------------------------------------------------------------------------
# Private helpers for search_community_sentiment
# ---------------------------------------------------------------------------

def _extract_github_orgs(protocol_detail: dict) -> list[str]:
    """Parse GitHub org handles from DeFiLlama protocol detail."""
    raw = protocol_detail.get("github")
    if not raw or not isinstance(raw, list):
        return []
    return [h.strip().strip("/") for h in raw if isinstance(h, str) and h.strip()]


def _fetch_github_dev_activity(orgs: list[str]) -> dict:
    """Fetch developer activity metrics from GitHub for the given orgs.

    Uses ``/repos`` for issue counts and ``/commits`` for commit activity
    (avoids ``/stats/contributors`` which returns 202 for cold repos and
    can take 30+ seconds to compute).

    Returns aggregated metrics: commits in last 90 days, open issues,
    unique contributors, most active repo, and last push date.
    """
    total_commits_90d = 0
    total_open_issues = 0
    contributors_set: set[str] = set()
    most_active_repo: str | None = None
    most_active_commits = 0
    last_push_date: str | None = None

    since_dt = datetime.datetime.utcnow() - datetime.timedelta(days=90)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    for org in orgs:
        # Fetch top 5 recently-pushed source repos for this org
        try:
            resp = _fetch_with_retry(
                f"{GITHUB_API_BASE}/orgs/{org}/repos",
                params={"sort": "pushed", "per_page": 5, "type": "sources"},
            )
            repos = resp.json()
        except Exception:
            continue

        if not isinstance(repos, list):
            continue

        for repo in repos:
            total_open_issues += repo.get("open_issues_count", 0)

            pushed = repo.get("pushed_at", "")
            if pushed and (last_push_date is None or pushed > last_push_date):
                last_push_date = pushed[:10]

        # Fetch recent commits for the top repo (most recently pushed)
        if repos:
            top_repo_name = repos[0].get("name", "")
            if top_repo_name:
                try:
                    commits_resp = _fetch_with_retry(
                        f"{GITHUB_API_BASE}/repos/{org}/{top_repo_name}/commits",
                        params={"since": since_iso, "per_page": 100},
                    )
                    commits_data = commits_resp.json()
                    if isinstance(commits_data, list):
                        repo_commits = len(commits_data)
                        total_commits_90d += repo_commits
                        for commit in commits_data:
                            author = commit.get("author")
                            if author and author.get("login"):
                                contributors_set.add(author["login"])
                        if repo_commits > most_active_commits:
                            most_active_commits = repo_commits
                            most_active_repo = f"{org}/{top_repo_name}"
                except Exception:
                    pass

    return {
        "total_commits_90d": total_commits_90d,
        "total_open_issues": total_open_issues,
        "total_contributors": len(contributors_set),
        "most_active_repo": most_active_repo,
        "last_push_date": last_push_date,
    }


def _assess_dev_health(metrics: dict) -> tuple[str, list[dict]]:
    """Map developer activity metrics to sentiment and key topics.

    Returns (overall_sentiment, key_topics) using the existing vocabulary
    ("positive"/"mixed"/"negative") for backward compatibility with scoring.
    """
    commits = metrics["total_commits_90d"]
    issues = metrics["total_open_issues"]
    contributors = metrics["total_contributors"]

    # --- Commit activity ---
    if commits >= 100:
        commit_sentiment = "positive"
        commit_summary = f"{commits} commits in the last 90 days — very active development."
    elif commits >= 20:
        commit_sentiment = "mixed"
        commit_summary = f"{commits} commits in the last 90 days — moderate development pace."
    else:
        commit_sentiment = "negative"
        commit_summary = f"Only {commits} commits in the last 90 days — low development activity."

    # --- Open issues (across up to 10 repos, so thresholds are generous) ---
    if issues < 100:
        issues_sentiment = "positive"
        issues_summary = f"{issues} open issues across repositories — manageable backlog."
    elif issues < 300:
        issues_sentiment = "mixed"
        issues_summary = f"{issues} open issues across repositories — moderate backlog."
    else:
        issues_sentiment = "negative"
        issues_summary = f"{issues} open issues across repositories — large backlog."

    # --- Contributor base ---
    if contributors >= 10:
        contrib_sentiment = "positive"
        contrib_summary = f"{contributors} active contributors in the last 90 days — healthy contributor base."
    elif contributors >= 3:
        contrib_sentiment = "mixed"
        contrib_summary = f"{contributors} active contributors in the last 90 days — small team."
    else:
        contrib_sentiment = "negative"
        contrib_summary = f"Only {contributors} active contributors in the last 90 days — very small team."

    # --- Overall: majority of 3 signals ---
    sentiments = [commit_sentiment, issues_sentiment, contrib_sentiment]
    positive_count = sentiments.count("positive")
    negative_count = sentiments.count("negative")

    if positive_count >= 2:
        overall = "positive"
    elif negative_count >= 2:
        overall = "negative"
    else:
        overall = "mixed"

    key_topics = [
        {"topic": "Commit activity", "sentiment": commit_sentiment, "summary": commit_summary},
        {"topic": "Open issues", "sentiment": issues_sentiment, "summary": issues_summary},
        {"topic": "Contributor base", "sentiment": contrib_sentiment, "summary": contrib_summary},
    ]

    return overall, key_topics


def _fetch_snapshot_governance(protocol_detail: dict) -> dict:
    """Fetch governance activity from Snapshot GraphQL API.

    Parses governanceID for 'snapshot:*' entries, queries for recent
    closed proposals, and computes average votes per proposal.
    """
    default = {"recent_proposals": 0, "voter_participation": "N/A"}

    gov_ids = protocol_detail.get("governanceID")
    if not gov_ids or not isinstance(gov_ids, list):
        return default

    # Find Snapshot space ID
    space = None
    for gid in gov_ids:
        if isinstance(gid, str) and gid.startswith("snapshot:"):
            space = gid[len("snapshot:"):]
            break

    if not space:
        return default

    query = """
    query ($space: String!) {
        proposals(
            first: 20,
            skip: 0,
            where: { space_in: [$space], state: "closed" },
            orderBy: "created",
            orderDirection: desc
        ) {
            id
            votes
        }
    }
    """

    try:
        _rate_limit_delay(SNAPSHOT_GRAPHQL_URL)
        resp = _session.post(
            SNAPSHOT_GRAPHQL_URL,
            json={"query": query, "variables": {"space": space}},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        proposals = data.get("data", {}).get("proposals", [])
        if not proposals:
            return default

        total_votes = sum(p.get("votes", 0) for p in proposals)
        avg_votes = total_votes // len(proposals) if proposals else 0

        return {
            "recent_proposals": len(proposals),
            "voter_participation": f"{avg_votes} avg votes/proposal",
        }
    except Exception:
        return default


def search_community_sentiment(
    protocol_name: str,
    protocol_detail: dict | None = None,
) -> dict:
    """Analyze developer activity and governance for a protocol.

    Uses GitHub API for commit frequency, open issues, and contributor
    counts.  Uses Snapshot GraphQL for governance proposal data.
    Falls back to empty data if sources are unavailable.
    """
    empty = {
        "overall_sentiment": "unknown",
        "key_topics": [],
        "governance_activity": {"recent_proposals": 0, "voter_participation": "N/A"},
        "data_source": "no_protocol_detail",
    }

    if protocol_detail is None:
        return empty

    # --- GitHub developer activity ---
    github_ok = False
    orgs = _extract_github_orgs(protocol_detail)
    metrics = None
    if orgs:
        try:
            metrics = _fetch_github_dev_activity(orgs)
            # If all metrics are zero, GitHub calls likely failed silently
            if metrics["total_commits_90d"] > 0 or metrics["total_contributors"] > 0:
                github_ok = True
        except Exception:
            pass

    # --- Snapshot governance (always attempted) ---
    governance = _fetch_snapshot_governance(protocol_detail)

    # --- Assemble result ---
    if github_ok:
        overall, key_topics = _assess_dev_health(metrics)
        sources = ["github"]
        if governance["recent_proposals"] > 0:
            sources.append("snapshot")
        return {
            "overall_sentiment": overall,
            "key_topics": key_topics,
            "governance_activity": governance,
            "data_source": ", ".join(sources),
        }

    # GitHub failed — return what we have
    source = "github_unavailable" if orgs else "no_github_orgs"
    if governance["recent_proposals"] > 0:
        source = "snapshot"
    empty["governance_activity"] = governance
    empty["data_source"] = source
    return empty


# ---------------------------------------------------------------------------
# Private helpers for search_red_flags
# ---------------------------------------------------------------------------

# Aggregate keys in currentChainTvls that are NOT real chains
_NON_CHAIN_KEYS = {"borrowed", "staking", "pool2", "vesting", "offers"}


def _check_chain_concentration(protocol_detail: dict) -> list[dict]:
    """Flag single-chain or heavily concentrated TVL."""
    chain_tvls = protocol_detail.get("currentChainTvls", {})
    if not chain_tvls:
        return []

    # Filter to real chains only: skip aggregate keys and sub-chain keys (contain '-')
    real_chains = {
        k: v for k, v in chain_tvls.items()
        if k.lower() not in _NON_CHAIN_KEYS and "-" not in k
    }
    if not real_chains:
        return []

    total = sum(real_chains.values())
    if total <= 0:
        return []

    dominant_chain = max(real_chains, key=real_chains.get)
    dominant_pct = real_chains[dominant_chain] / total

    flags = []
    if len(real_chains) == 1:
        flags.append({
            "severity": "medium",
            "category": "Concentration",
            "description": f"Single-chain deployment ({dominant_chain} only)",
            "source": "DeFiLlama",
        })
    elif dominant_pct > 0.90:
        flags.append({
            "severity": "low",
            "category": "Concentration",
            "description": f"Heavy concentration on {dominant_chain} ({dominant_pct:.0%} of TVL)",
            "source": "DeFiLlama",
        })

    return flags


def _check_tvl_decline(protocol_detail: dict) -> list[dict]:
    """Flag significant TVL decline over the last 90 days."""
    tvl_history = protocol_detail.get("tvl", [])
    if len(tvl_history) < 2:
        return []

    now_ts = time.time()
    ninety_days_ago = now_ts - (90 * 86400)

    recent = [
        p for p in tvl_history
        if p.get("date", 0) >= ninety_days_ago
    ]
    if len(recent) < 2:
        return []

    peak = max(p.get("totalLiquidityUSD", 0) for p in recent)
    current = recent[-1].get("totalLiquidityUSD", 0)

    if peak <= 0:
        return []

    decline = (peak - current) / peak

    flags = []
    if decline > 0.50:
        flags.append({
            "severity": "high",
            "category": "TVL",
            "description": f"TVL declined >50% in 90 days (peak ${peak:,.0f} → ${current:,.0f})",
            "source": "DeFiLlama",
        })
    elif decline > 0.30:
        flags.append({
            "severity": "medium",
            "category": "TVL",
            "description": f"TVL declined >30% in 90 days (peak ${peak:,.0f} → ${current:,.0f})",
            "source": "DeFiLlama",
        })

    return flags


def _check_protocol_age(protocol_detail: dict) -> list[dict]:
    """Flag very new protocols based on earliest TVL data point."""
    tvl_history = protocol_detail.get("tvl", [])
    if not tvl_history:
        return []

    first_ts = tvl_history[0].get("date", 0)
    if first_ts <= 0:
        return []

    age_days = (time.time() - first_ts) / 86400

    flags = []
    if age_days < 90:
        flags.append({
            "severity": "medium",
            "category": "Maturity",
            "description": "Very new protocol — less than 3 months of track record",
            "source": "DeFiLlama",
        })
    elif age_days < 180:
        flags.append({
            "severity": "low",
            "category": "Maturity",
            "description": "New protocol — less than 6 months of track record",
            "source": "DeFiLlama",
        })

    return flags


def _check_hack_history(hacks: list) -> list[dict]:
    """Flag past security incidents from DeFiLlama hack data."""
    if not hacks:
        return []

    flags = []
    for hack in hacks:
        amount = hack.get("amount", 0)
        # DeFiLlama hack amounts are in millions
        amount_usd = amount * 1_000_000 if amount < 1_000 else amount
        hack_date = hack.get("date", "Unknown")
        if isinstance(hack_date, (int, float)):
            hack_date = datetime.datetime.utcfromtimestamp(hack_date).strftime("%Y-%m-%d")

        if amount_usd > 10_000_000:
            severity = "critical"
            label = "Major exploit"
        elif amount_usd > 1_000_000:
            severity = "high"
            label = "Significant exploit"
        else:
            severity = "medium"
            label = "Security incident"

        flags.append({
            "severity": severity,
            "category": "Security",
            "description": f"{label}: ${amount_usd:,.0f} lost on {hack_date}",
            "source": "DeFiLlama",
        })

    if len(hacks) > 1:
        flags.append({
            "severity": "medium",
            "category": "Security",
            "description": f"Protocol has been exploited {len(hacks)} times",
            "source": "DeFiLlama",
        })

    return flags


def _check_no_funding(protocol_detail: dict) -> list[dict]:
    """Flag protocols with no known funding rounds."""
    raises = protocol_detail.get("raises", [])
    if not raises:
        return [{
            "severity": "low",
            "category": "Funding",
            "description": "No known funding rounds — bootstrap risk",
            "source": "DeFiLlama",
        }]
    return []


def _check_contract_verification(protocol_detail: dict) -> tuple[list[dict], bool]:
    """Check if token contract is verified on Etherscan.

    Returns (flags, etherscan_checked) — the bool indicates whether an
    Etherscan call was actually made (for data_source tracking).
    """
    address = protocol_detail.get("address")
    if not address or not isinstance(address, str) or len(address) != 42:
        return [], False

    try:
        resp = _fetch_with_retry(
            "https://api.etherscan.io/api",
            params={"module": "contract", "action": "getabi", "address": address},
        )
        data = resp.json()
        if data.get("status") == "0" and "not verified" in data.get("result", "").lower():
            return [{
                "severity": "high",
                "category": "Security",
                "description": "Token contract not verified on Etherscan",
                "source": "Etherscan",
            }], True
        return [], True
    except Exception:
        return [], False


_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _derive_risk_level(flags: list[dict]) -> str:
    """Return the highest severity found among flags."""
    if not flags:
        return "low"
    worst = max(flags, key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "low"), 0))
    return worst["severity"]


def search_red_flags(
    protocol_name: str,
    protocol_detail: dict | None = None,
    hacks: list | None = None,
) -> dict:
    """Analyze red flags from DeFiLlama protocol data and hack history.

    If protocol_detail is not provided, returns empty flags with
    data_source "error" (backward-compatible with old call sites).
    """
    if protocol_detail is None:
        return {"flags": [], "risk_level": "low", "data_source": "error"}

    if hacks is None:
        hacks = []

    flags: list[dict] = []
    sources: list[str] = ["defillama"]

    flags.extend(_check_chain_concentration(protocol_detail))
    flags.extend(_check_tvl_decline(protocol_detail))
    flags.extend(_check_protocol_age(protocol_detail))
    flags.extend(_check_hack_history(hacks))
    flags.extend(_check_no_funding(protocol_detail))

    etherscan_flags, etherscan_checked = _check_contract_verification(protocol_detail)
    flags.extend(etherscan_flags)
    if etherscan_checked:
        sources.append("etherscan")

    return {
        "flags": flags,
        "risk_level": _derive_risk_level(flags),
        "data_source": ", ".join(sources),
    }
