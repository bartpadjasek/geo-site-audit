#!/usr/bin/env python3
"""
audit.py — Firecrawl-based site auditor for getwhy.io
Usage:
  python audit.py              # audit all pages, save snapshot
  python audit.py --no-push    # skip git commit and push (used in CI)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_DIR = Path(__file__).parent
SITE_DIR = SYSTEM_DIR.parent
CONFIG_PATH = SYSTEM_DIR / "config.json"
PAGES_PATH = SYSTEM_DIR / "pages.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_pages():
    with open(PAGES_PATH) as f:
        return json.load(f)


def clean_markdown(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'!\[.*?\]\(data:[^)]+\)', '[image]', text)
    text = re.sub(r'!\[.*?\]\(https?://[^)]+\)', '[image]', text)
    text = re.sub(r'<svg[^>]*>.*?</svg>', '[svg]', text, flags=re.DOTALL)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _build_json_opts(V1JsonConfig) -> dict:
    """Build Firecrawl JSON extraction configs for SEO and GEO analysis."""
    seo_geo_schema = {
        "type": "object",
        "properties": {
            "h1": {"type": "string"},
            "h2s": {"type": "array", "items": {"type": "string"}},
            "has_faq": {"type": "boolean"},
            "value_proposition": {"type": "string"},
            "key_entities": {"type": "array", "items": {"type": "string"}},
            "data_points": {"type": "array", "items": {"type": "string"}},
            "content_topics": {"type": "array", "items": {"type": "string"}},
            "geo_readiness": {"type": "string"},
            "geo_rationale": {"type": "string"},
        },
        "required": [],
    }

    core_prompt = (
        "Analyse this webpage for SEO and GEO (Generative Engine Optimisation). Extract: "
        "(1) the exact H1 heading text, "
        "(2) the first 3 H2 headings, "
        "(3) whether a FAQ section or Q&A-style content exists (true/false), "
        "(4) a one-sentence value proposition — what this page offers and who it's for, "
        "(5) key named entities: company name, product names, buyer personas mentioned, "
        "(6) any specific statistics, data points, or numbers cited, "
        "(7) main topics this page covers, "
        "(8) GEO readiness: 'high' if the page clearly answers specific questions an AI might surface "
        "(clear entity, clear value prop, structured content, data points), 'medium' if partial, 'low' if vague, "
        "(9) one sentence explaining the GEO rating."
    )

    landing_prompt = (
        "Analyse this ICP landing page for SEO and GEO (Generative Engine Optimisation). Extract: "
        "(1) the exact H1 heading text, "
        "(2) the first 3 H2 headings, "
        "(3) whether a FAQ section or Q&A-style content exists (true/false), "
        "(4) a one-sentence value proposition — what pain this page solves and for whom specifically, "
        "(5) key named entities: target persona, use cases, product features mentioned, "
        "(6) any specific statistics, data points, or numbers cited, "
        "(7) main topics this page covers, "
        "(8) GEO readiness: 'high' if the page would appear in AI answers for '[persona] qualitative research tool' queries, "
        "'medium' if partially, 'low' if too generic, "
        "(9) one sentence explaining the GEO rating."
    )

    return {
        "core": V1JsonConfig(prompt=core_prompt, schema=seo_geo_schema),
        "landing": V1JsonConfig(prompt=landing_prompt, schema=seo_geo_schema),
        "content": V1JsonConfig(prompt=core_prompt, schema=seo_geo_schema),
        "conversion": V1JsonConfig(prompt=core_prompt, schema=seo_geo_schema),
        "trust": V1JsonConfig(prompt=core_prompt, schema=seo_geo_schema),
    }


def audit_site(config: dict, pages_config: dict):
    try:
        from firecrawl import V1FirecrawlApp, V1JsonConfig
    except ImportError:
        print("ERROR: firecrawl not installed. Run: pip install firecrawl-py")
        sys.exit(1)

    api_key = os.environ.get("FIRECRAWL_API_KEY") or config.get("firecrawl_api_key")
    if not api_key:
        print("ERROR: No Firecrawl API key found. Set FIRECRAWL_API_KEY env var or add to config.json")
        sys.exit(1)

    client = V1FirecrawlApp(api_key=api_key)
    JSON_OPTS = _build_json_opts(V1JsonConfig)

    pages = pages_config["pages"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    site_url = config.get("site_url", "the site")
    print(f"\n── Auditing {site_url} ({len(pages)} pages) ──")

    results = []
    for page in pages:
        url = page["url"]
        label = page["label"]
        category = page.get("category", "core")
        json_opts = JSON_OPTS.get(category, JSON_OPTS["core"])

        scrape_kwargs = {
            "formats": ["markdown", "json", "links"],
            "only_main_content": False,
            "max_age": config.get("max_age_ms", 86400000),
            "proxy": config.get("scrape_proxy", "enhanced"),
            "timeout": 60000,
            "wait_for": config.get("wait_for_ms", 2000),
            "json_options": json_opts,
        }

        print(f"  Scraping: {label} ({url})", end="", flush=True)
        try:
            result = client.scrape_url(url, **scrape_kwargs)
            data = result.model_dump() if hasattr(result, "model_dump") else dict(result)

            if "json_field" in data:
                data["json"] = data.pop("json_field")
            if data.get("markdown"):
                data["markdown"] = clean_markdown(data["markdown"])

            entry = {
                "url": url,
                "label": label,
                "category": category,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            results.append(entry)
            print(" ✓")
        except Exception as e:
            print(f" ✗ (scrape failed)")
            results.append({
                "url": url,
                "label": label,
                "category": category,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "error": "scrape failed",
                "data": None,
            })

    snapshot = {
        "site": config.get("site_url", "https://www.getwhy.io"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "page_count": len(results),
        "pages": results,
    }

    snapshots_dir = SITE_DIR / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = snapshots_dir / f"{today}.json"
    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"\n  Saved snapshot → {snapshot_path}")

    return snapshot_path


def run_analyse():
    print("\n── Running analysis ──")
    result = subprocess.run(
        [sys.executable, str(SYSTEM_DIR / "analyse.py")],
        cwd=str(SYSTEM_DIR),
    )
    if result.returncode != 0:
        print(f"  WARNING: analyse.py exited with code {result.returncode}")


def run_check_ai_visibility():
    print("\n── Checking AI visibility ──")
    result = subprocess.run(
        [sys.executable, str(SYSTEM_DIR / "check_ai_visibility.py")],
        cwd=str(SYSTEM_DIR),
    )
    if result.returncode != 0:
        print(f"  WARNING: check_ai_visibility.py exited with code {result.returncode}")


def run_generate_ai_insights():
    print("\n── Generating AI insights ──")
    result = subprocess.run(
        [sys.executable, str(SYSTEM_DIR / "generate_ai_insights.py")],
        cwd=str(SYSTEM_DIR),
    )
    if result.returncode != 0:
        print(f"  WARNING: generate_ai_insights.py exited with code {result.returncode}")


def run_generate_report():
    print("\n── Generating report ──")
    result = subprocess.run(
        [sys.executable, str(SYSTEM_DIR / "generate_report.py")],
        cwd=str(SYSTEM_DIR),
    )
    if result.returncode != 0:
        print(f"  WARNING: generate_report.py exited with code {result.returncode}")


def git_commit_and_push():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_json = SITE_DIR / "public" / "data.json"
    print("\n── Pushing report to GitHub ──")
    try:
        subprocess.run(["git", "add", str(data_json)], cwd=str(SITE_DIR), check=True)
        subprocess.run(
            ["git", "commit", "-m", f"report: site audit {today}"],
            cwd=str(SITE_DIR), check=True,
        )
        subprocess.run(["git", "push"], cwd=str(SITE_DIR), check=True)
        print("  Pushed — Vercel deploy triggered.")
    except subprocess.CalledProcessError as e:
        print(f"  WARNING: git operation failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Audit getwhy.io via Firecrawl")
    parser.add_argument("--no-push", action="store_true", help="Skip git commit and push")
    args = parser.parse_args()

    config = load_config()
    pages_config = load_pages()

    audit_site(config, pages_config)
    run_check_ai_visibility()
    run_analyse()
    run_generate_ai_insights()
    run_generate_report()

    if not args.no_push:
        git_commit_and_push()


if __name__ == "__main__":
    main()
