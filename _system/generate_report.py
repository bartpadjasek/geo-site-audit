#!/usr/bin/env python3
"""
generate_report.py — Compile latest_audit.json + ai_insights.json into public/data.json.
Usage:
  python generate_report.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_DIR = Path(__file__).parent
SITE_DIR = SYSTEM_DIR.parent
AUDIT_PATH = SITE_DIR / "snapshots" / "latest_audit.json"
AI_INSIGHTS_PATH = SYSTEM_DIR / "ai_insights.json"
AI_VISIBILITY_PATH = SYSTEM_DIR / "ai_visibility.json"
OUTPUT_PATH = SITE_DIR / "public" / "data.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_previous_scores(output_path: Path) -> dict:
    """Read scores from the existing report before overwriting it."""
    try:
        existing = load_json(output_path)
        scores = existing.get("scores", {})
        # Only keep the top-level numeric scores, not geo_detail
        return {k: v for k, v in scores.items() if k != "geo_detail" and isinstance(v, (int, float))}
    except Exception:
        return {}


def main():
    audit = load_json(AUDIT_PATH)
    ai = load_json(AI_INSIGHTS_PATH)
    ai_visibility = load_json(AI_VISIBILITY_PATH)
    previous_scores = load_previous_scores(OUTPUT_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": audit.get("snapshot_date"),
        "scores": audit.get("scores", {}),
        "previous_scores": previous_scores,
        "summary": audit.get("summary", {}),
        "pages": audit.get("pages", []),
        "broken_links": audit.get("broken_links", []),
        "content_gaps": audit.get("content_gaps", []),
        "seo_issue_definitions": audit.get("seo_issue_definitions", {}),
        "ai_visibility": {
            "checked_at": ai_visibility.get("checked_at"),
            "summary": ai_visibility.get("summary", {}),
            "results": ai_visibility.get("results", []),
            "history": ai_visibility.get("history", []),
        },
        "ai": {
            "executive_summary": ai.get("executive_summary"),
            "opportunity_matrix": ai.get("opportunity_matrix", []),
            "seo_technical": ai.get("seo_technical", []),
            "seo_onpage": ai.get("seo_onpage", []),
            "seo_backlinks_keywords": ai.get("seo_backlinks_keywords", []),
            "geo_opportunities": ai.get("geo_opportunities", []),
            "content_gaps": ai.get("content_gaps", []),
            "quick_wins": ai.get("quick_wins", []),
            "roadmap_90_day": ai.get("roadmap_90_day", {}),
            "semrush_report_recommendations": ai.get("semrush_report_recommendations", []),
            "meta_description_rewrites": ai.get("meta_description_rewrites", {}),
            "generated_at": ai.get("generated_at"),
        },
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report written → {OUTPUT_PATH}")
    scores = report["scores"]
    print(f"  Overall: {scores.get('overall')} | SEO: {scores.get('seo')} | GEO: {scores.get('geo')} | Links: {scores.get('links')}")


if __name__ == "__main__":
    main()
