#!/usr/bin/env python3
"""
analyse.py — Process latest snapshot to generate SEO issues, GEO scores, broken links, content gaps.
Usage:
  python analyse.py
Output: writes audit.json to own-site/snapshots/latest_audit.json
"""

import ipaddress
import json
import os
import re
import socket
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

SYSTEM_DIR = Path(__file__).parent
SITE_DIR = SYSTEM_DIR.parent
PAGES_PATH = SYSTEM_DIR / "pages.json"
CONFIG_PATH = SYSTEM_DIR / "config.json"

# Loaded from config at runtime in main()
SITE_HOST = None

# Private/reserved IP ranges to block in link checker (SSRF protection)
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_private_url(url: str) -> bool:
    """Return True if the URL resolves to a private/reserved IP address."""
    try:
        host = urlparse(url).hostname
        if not host:
            return True
        addr = ipaddress.ip_address(socket.gethostbyname(host))
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except Exception:
        return False

# ── SEO issue definitions ─────────────────────────────────────────────────────

SEO_ISSUES = {
    "missing_title":        {"severity": "critical", "label": "Missing page title"},
    "missing_meta_desc":    {"severity": "critical", "label": "Missing meta description"},
    "duplicate_meta_desc":  {"severity": "warning",  "label": "Duplicate meta description"},
    "short_meta_desc":      {"severity": "warning",  "label": "Meta description too short (<70 chars)"},
    "long_meta_desc":       {"severity": "info",     "label": "Meta description too long (>160 chars)"},
    "missing_h1":           {"severity": "critical", "label": "Missing H1 heading"},
    "multiple_h1":          {"severity": "warning",  "label": "Multiple H1 headings"},
    "missing_og_title":     {"severity": "warning",  "label": "Missing OG title"},
    "missing_og_desc":      {"severity": "warning",  "label": "Missing OG description"},
    "title_desc_mismatch":  {"severity": "info",     "label": "Title/URL mismatch (title doesn't match page topic)"},
    "thin_content":         {"severity": "warning",  "label": "Thin content (<300 words)"},
    "no_internal_links":    {"severity": "info",     "label": "No internal links found"},
    "slow_lcp":             {"severity": "warning",  "label": "LCP > 2.5s (Core Web Vital)"},
    "poor_lcp":             {"severity": "critical", "label": "LCP > 4s (Core Web Vital — poor)"},
    "high_cls":             {"severity": "warning",  "label": "CLS > 0.1 (Core Web Vital)"},
    "poor_cls":             {"severity": "critical", "label": "CLS > 0.25 (Core Web Vital — poor)"},
    "slow_inp":             {"severity": "warning",  "label": "INP > 200ms (Core Web Vital)"},
    "poor_inp":             {"severity": "critical", "label": "INP > 500ms (Core Web Vital — poor)"},
}

GEO_SCORES = {"high": 100, "medium": 60, "low": 20}

# GEO score weights — AI visibility is the primary signal
GEO_WEIGHT_AI_VISIBILITY  = 0.65  # actual presence in GPT-4o, Gemini, Claude answers
GEO_WEIGHT_CONTENT        = 0.35  # on-page content quality (structure, data points, FAQs)


def load_pages_config() -> dict:
    with open(PAGES_PATH) as f:
        return json.load(f)


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_latest_snapshot() -> Optional[dict]:
    snapshots_dir = SITE_DIR / "snapshots"
    snapshots = sorted(
        [p for p in snapshots_dir.glob("*.json") if p.stem not in ("baseline", "latest_audit")],
        reverse=True,
    )
    if not snapshots:
        return None
    with open(snapshots[0]) as f:
        return json.load(f)


def word_count(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r'\w+', text))


def audit_seo(page: dict, all_meta_descs: list) -> list:
    """Return list of SEO issues for a single page."""
    issues = []
    data = page.get("data") or {}
    metadata = data.get("metadata") or {}
    json_data = data.get("json") or {}
    markdown = data.get("markdown") or ""

    title = metadata.get("title") or metadata.get("ogTitle") or data.get("title")
    meta_desc = metadata.get("description") or metadata.get("ogDescription")
    og_title = metadata.get("ogTitle")
    og_desc = metadata.get("ogDescription")
    h1 = json_data.get("h1")

    if not title:
        issues.append("missing_title")
    if not meta_desc:
        issues.append("missing_meta_desc")
    else:
        if len(meta_desc) < 70:
            issues.append("short_meta_desc")
        elif len(meta_desc) > 160:
            issues.append("long_meta_desc")
        # Check for duplicate (same description used on other pages)
        if all_meta_descs.count(meta_desc.strip()) > 1:
            issues.append("duplicate_meta_desc")
    if not og_title:
        issues.append("missing_og_title")
    if not og_desc:
        issues.append("missing_og_desc")
    if not h1:
        issues.append("missing_h1")

    if word_count(markdown) < 300:
        issues.append("thin_content")

    links = data.get("links") or []
    internal = [l for l in links if SITE_HOST in (l if isinstance(l, str) else l.get("url", ""))]
    if not internal:
        issues.append("no_internal_links")

    return issues


def score_geo(page: dict) -> dict:
    """Return GEO score and rationale for a page."""
    data = page.get("data") or {}
    json_data = data.get("json") or {}
    readiness = json_data.get("geo_readiness", "low")
    rationale = json_data.get("geo_rationale", "")
    score = GEO_SCORES.get(readiness, 20)
    return {
        "score": score,
        "readiness": readiness,
        "rationale": rationale,
        "has_faq": json_data.get("has_faq", False),
        "value_proposition": json_data.get("value_proposition"),
        "data_points": json_data.get("data_points", []),
        "content_topics": json_data.get("content_topics", []),
    }


def extract_links(pages: list) -> dict:
    """Collect all internal and external links across all pages."""
    internal_links = {}  # url → [source_pages]
    external_links = {}  # url → [source_pages]

    for page in pages:
        if not page.get("data"):
            continue
        source = page["url"]
        links = page["data"].get("links") or []
        for link in links:
            href = link if isinstance(link, str) else link.get("url", "")
            if not href or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            parsed = urlparse(href)
            if not parsed.scheme or not parsed.netloc:
                continue
            if SITE_HOST in parsed.netloc:
                if href not in internal_links:
                    internal_links[href] = []
                if source not in internal_links[href]:
                    internal_links[href].append(source)
            else:
                if href not in external_links:
                    external_links[href] = []
                if source not in external_links[href]:
                    external_links[href].append(source)

    return {"internal": internal_links, "external": external_links}


def check_url(url: str, timeout: int = 10) -> dict:
    """HEAD-check a URL, return status code and whether it's broken."""
    if _is_private_url(url):
        return {"status": None, "broken": False, "skipped": "private-ip"}
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "geo-site-audit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status": resp.status, "broken": resp.status >= 400}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "broken": e.code >= 400}
    except (urllib.error.URLError, socket.timeout, Exception) as e:
        return {"status": None, "broken": True, "error": "request failed"}


def check_broken_links(links_map: dict, max_external: int = 50, timeout: int = 10) -> list:
    """Check internal and external links for 404s. Returns list of broken link dicts."""
    broken = []
    all_to_check = []

    for url, sources in links_map["internal"].items():
        all_to_check.append({"url": url, "type": "internal", "sources": sources})

    external_items = list(links_map["external"].items())[:max_external]
    for url, sources in external_items:
        all_to_check.append({"url": url, "type": "external", "sources": sources})

    print(f"  Checking {len(all_to_check)} links ({len(links_map['internal'])} internal, {min(len(links_map['external']), max_external)} external)...")

    for item in all_to_check:
        result = check_url(item["url"], timeout=timeout)
        if result["broken"]:
            broken.append({
                "url": item["url"],
                "type": item["type"],
                "status": result.get("status"),
                "error": result.get("error"),
                "found_on": item["sources"],
            })
            print(f"    BROKEN [{result.get('status', 'ERR')}]: {item['url']}")

    return broken


def load_ai_visibility_rate() -> tuple:
    """
    Read ai_visibility.json and return (avg_mention_rate, model_breakdown).
    Returns (None, {}) if the file doesn't exist or no models ran.
    """
    ai_vis_path = SYSTEM_DIR / "ai_visibility.json"
    if not ai_vis_path.exists():
        return None, {}
    try:
        with open(ai_vis_path) as f:
            data = json.load(f)
        breakdown = {}
        rates = []
        for model, stats in data.get("summary", {}).items():
            if stats.get("skipped"):
                breakdown[model] = None
            elif stats.get("queries", 0) > 0:
                rate = stats["rate"]
                breakdown[model] = rate
                rates.append(rate)
        avg = round(sum(rates) / len(rates), 3) if rates else 0.0
        return avg, breakdown
    except Exception:
        return None, {}


def fetch_cwv(url: str, psi_key: str = None) -> dict:
    """Call PageSpeed Insights API (mobile) and return Core Web Vitals."""
    from urllib.parse import urlencode
    # PSI requires the key as a query param — this is the only supported auth method.
    # The URL is never logged; only errors are surfaced.
    params = {"url": url, "strategy": "mobile"}
    if psi_key:
        params["key"] = psi_key
    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urlencode(params)
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "geo-site-audit/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {"error": "PSI request failed"}

    result = {}
    lhr = data.get("lighthouseResult", {})
    audits = lhr.get("audits", {})
    perf_score = (lhr.get("categories") or {}).get("performance", {}).get("score")
    if perf_score is not None:
        result["performance_score"] = round(perf_score * 100)

    for out_key, audit_id in [
        ("lcp", "largest-contentful-paint"),
        ("cls", "cumulative-layout-shift"),
        ("inp", "interaction-to-next-paint"),
        ("fcp", "first-contentful-paint"),
        ("ttfb", "server-response-time"),
    ]:
        audit = audits.get(audit_id, {})
        if audit.get("displayValue"):
            result[f"lab_{out_key}"] = audit["displayValue"]
        if audit.get("numericValue") is not None:
            result[f"lab_{out_key}_ms"] = round(audit["numericValue"])

    field = data.get("loadingExperience", {})
    if field.get("overall_category"):
        result["field_overall"] = field["overall_category"]
    for api_metric, out_key in [
        ("LARGEST_CONTENTFUL_PAINT_MS", "field_lcp_ms"),
        ("CUMULATIVE_LAYOUT_SHIFT_SCORE", "field_cls"),
        ("INTERACTION_TO_NEXT_PAINT",    "field_inp_ms"),
        ("FIRST_CONTENTFUL_PAINT_MS",    "field_fcp_ms"),
    ]:
        m = field.get("metrics", {}).get(api_metric, {})
        if m.get("percentile") is not None:
            result[out_key] = m["percentile"]
        if m.get("category"):
            result[f"{out_key}_category"] = m["category"]

    return result


def audit_cwv(cwv: dict) -> list:
    """Return CWV-based SEO issue keys from a fetch_cwv result."""
    issues = []
    if not cwv or cwv.get("error"):
        return issues

    lcp_cat = cwv.get("field_lcp_ms_category")
    lcp_ms  = cwv.get("field_lcp_ms") or cwv.get("lab_lcp_ms")
    if lcp_cat == "SLOW" or (not lcp_cat and lcp_ms and lcp_ms > 4000):
        issues.append("poor_lcp")
    elif lcp_cat == "AVERAGE" or (not lcp_cat and lcp_ms and lcp_ms > 2500):
        issues.append("slow_lcp")

    cls_cat = cwv.get("field_cls_category")
    if cls_cat == "SLOW":
        issues.append("poor_cls")
    elif cls_cat == "AVERAGE":
        issues.append("high_cls")

    inp_cat = cwv.get("field_inp_ms_category")
    inp_ms  = cwv.get("field_inp_ms") or cwv.get("lab_inp_ms")
    if inp_cat == "SLOW" or (not inp_cat and inp_ms and inp_ms > 500):
        issues.append("poor_inp")
    elif inp_cat == "AVERAGE" or (not inp_cat and inp_ms and inp_ms > 200):
        issues.append("slow_inp")

    return issues


def main():
    global SITE_HOST
    config = load_config()
    pages_config = load_pages_config()
    psi_key = os.environ.get("PSI_API_KEY") or config.get("psi_api_key")
    SITE_HOST = urlparse(config.get("site_url", "")).hostname or "localhost"
    snapshot = get_latest_snapshot()

    if not snapshot:
        print("ERROR: No snapshot found. Run audit.py first.")
        return

    scraped_at = snapshot.get("scraped_at", "")[:10]
    pages = snapshot.get("pages", [])
    successful_pages = [p for p in pages if p.get("data")]

    print(f"\n── Analysing snapshot ({scraped_at}, {len(successful_pages)}/{len(pages)} pages) ──")

    # Collect all meta descriptions upfront to detect duplicates
    all_meta_descs = []
    for page in successful_pages:
        metadata = (page.get("data") or {}).get("metadata") or {}
        desc = metadata.get("description") or metadata.get("ogDescription") or ""
        all_meta_descs.append(desc.strip())

    # Per-page SEO + GEO audit
    page_audits = []
    geo_scores = []
    all_issues = {"critical": 0, "warning": 0, "info": 0}

    for page in pages:
        url = page["url"]
        label = page["label"]
        category = page["category"]
        data = page.get("data") or {}
        metadata = data.get("metadata") or {}
        json_data = data.get("json") or {}

        if page.get("error"):
            page_audits.append({
                "url": url,
                "label": label,
                "category": category,
                "error": page["error"],
                "seo_issues": [],
                "geo": None,
                "meta": {},
            })
            continue

        issue_keys = audit_seo(page, all_meta_descs)
        geo = score_geo(page)
        geo_scores.append(geo["score"])

        for k in issue_keys:
            sev = SEO_ISSUES.get(k, {}).get("severity", "info")
            all_issues[sev] += 1

        print(f"    CWV: {label}", end="", flush=True)
        cwv = fetch_cwv(url, psi_key)
        cwv_issue_keys = audit_cwv(cwv)
        for k in cwv_issue_keys:
            sev = SEO_ISSUES.get(k, {}).get("severity", "info")
            all_issues[sev] += 1
        print(f" ✓" if not cwv.get("error") else f" ✗ ({cwv.get('error', '')})")

        title = metadata.get("title") or metadata.get("ogTitle") or data.get("title")
        meta_desc = metadata.get("description") or metadata.get("ogDescription")
        canonical = metadata.get("canonicalUrl") or metadata.get("canonical")

        page_audits.append({
            "url": url,
            "label": label,
            "category": category,
            "meta": {
                "title": title,
                "description": meta_desc,
                "canonical": canonical,
                "og_title": metadata.get("ogTitle"),
                "og_description": metadata.get("ogDescription"),
                "h1": json_data.get("h1"),
                "h2s": json_data.get("h2s", []),
                "word_count": word_count(data.get("markdown") or ""),
            },
            "seo_issues": [
                {"key": k, "severity": SEO_ISSUES.get(k, {}).get("severity", "info"), "label": SEO_ISSUES.get(k, {}).get("label", k)}
                for k in issue_keys + cwv_issue_keys
            ],
            "geo": geo,
            "cwv": cwv,
        })

    content_geo_score = round(sum(geo_scores) / len(geo_scores), 1) if geo_scores else 0
    ai_vis_rate, ai_vis_breakdown = load_ai_visibility_rate()

    if ai_vis_rate is not None:
        ai_vis_score = round(ai_vis_rate * 100, 1)
        avg_geo_score = round(ai_vis_score * GEO_WEIGHT_AI_VISIBILITY + content_geo_score * GEO_WEIGHT_CONTENT, 1)
        print(f"\n  GEO breakdown — AI visibility: {ai_vis_score} ({ai_vis_breakdown}), Content quality: {content_geo_score}, Weighted: {avg_geo_score}")
    else:
        avg_geo_score = content_geo_score
        ai_vis_score = None
        print(f"\n  GEO: no AI visibility data — using content quality only ({content_geo_score})")

    # Link extraction and broken link check
    print("\n── Checking links ──")
    links_map = extract_links(successful_pages)
    broken_links = check_broken_links(
        links_map,
        max_external=config.get("link_check_max_external", 50),
        timeout=config.get("link_check_timeout_s", 10),
    )

    # Known content gaps
    known_gaps = pages_config.get("known_gaps", [])

    # SEO score: start at 100, deduct per issue
    deductions = {"critical": 10, "warning": 5, "info": 1}
    seo_score = max(0, 100 - sum(deductions[sev] * count for sev, count in all_issues.items()))
    link_score = max(0, 100 - len(broken_links) * 10)

    audit_summary = {
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": scraped_at,
        "scores": {
            "seo": seo_score,
            "geo": avg_geo_score,
            "geo_detail": {
                "ai_visibility": ai_vis_score,
                "ai_visibility_breakdown": ai_vis_breakdown,
                "content_quality": content_geo_score,
                "weights": {"ai_visibility": GEO_WEIGHT_AI_VISIBILITY, "content": GEO_WEIGHT_CONTENT},
            },
            "links": link_score,
            "overall": round((seo_score + avg_geo_score + link_score) / 3, 1),
        },
        "summary": {
            "pages_audited": len(successful_pages),
            "pages_errored": len(pages) - len(successful_pages),
            "seo_issues": all_issues,
            "broken_links_count": len(broken_links),
            "content_gaps_count": len(known_gaps),
        },
        "pages": page_audits,
        "broken_links": broken_links,
        "content_gaps": known_gaps,
        "seo_issue_definitions": SEO_ISSUES,
    }

    output_path = SITE_DIR / "snapshots" / "latest_audit.json"
    with open(output_path, "w") as f:
        json.dump(audit_summary, f, indent=2, default=str)

    print(f"\n  Audit saved → {output_path}")
    print(f"  Scores — SEO: {seo_score}, GEO: {avg_geo_score}, Links: {link_score}, Overall: {audit_summary['scores']['overall']}")
    print(f"  Issues — {all_issues['critical']} critical, {all_issues['warning']} warning, {all_issues['info']} info")
    print(f"  Broken links: {len(broken_links)}")


if __name__ == "__main__":
    main()
