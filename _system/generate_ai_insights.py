#!/usr/bin/env python3
"""
generate_ai_insights.py — Use Claude to generate SEO, GEO, and content recommendations.
Reads latest_audit.json, makes one Claude API call, writes ai_insights.json.

Usage:
  python generate_ai_insights.py
  OPENROUTER_API_KEY=sk-or-... python generate_ai_insights.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_DIR = Path(__file__).parent
SITE_DIR = SYSTEM_DIR.parent
AUDIT_PATH = SITE_DIR / "snapshots" / "latest_audit.json"
AI_VISIBILITY_PATH = SYSTEM_DIR / "ai_visibility.json"
OUTPUT_PATH = SYSTEM_DIR / "ai_insights.json"
MODEL = "anthropic/claude-sonnet-4.6"

BRAND_CONTEXT = """
Oatly is the original oat milk brand, pioneering plant-based dairy alternatives since the 1990s.
- Core products: Oat-based milk, cream, yogurt, ice cream, and barista editions
- Differentiators: Category creator, strong sustainability credentials, bold and irreverent brand voice
- Key positioning: Making it easy and enjoyable to shift from dairy to plant-based
- Target audience: Health-conscious consumers, sustainability-minded shoppers, baristas and coffee professionals
- Known for: Transparent sustainability reporting, provocative advertising, strong cafe/barista community
- Key competitors: Alpro, Califia Farms, Minor Figures
"""


def load_ai_visibility() -> str:
    if not AI_VISIBILITY_PATH.exists():
        return "No AI visibility data found."
    with open(AI_VISIBILITY_PATH) as f:
        data = json.load(f)
    lines = [f"AI visibility check run: {data.get('checked_at', '?')[:10]}"]
    summary = data.get("summary", {})
    for model, stats in summary.items():
        if stats.get("skipped"):
            lines.append(f"  {model}: skipped (no API key)")
        else:
            lines.append(f"  {model}: {stats['mentions']}/{stats['queries']} queries mentioned the brand ({stats['rate']*100:.0f}%)")

    # Show which queries triggered a mention
    mentions = [r for r in data.get("results", []) if r.get("mentioned")]
    if mentions:
        lines.append("\nQueries where the brand was mentioned:")
        for r in mentions:
            lines.append(f"  [{r['model']}] {r['query'][:90]}")
            if r.get("context"):
                lines.append(f"    Context: {r['context'][:200]}")
    else:
        lines.append("\nThe brand was not mentioned in any AI response.")

    # Show trend if history exists
    history = data.get("history", [])
    if history:
        lines.append("\nHistorical mention rates (most recent first):")
        for run in reversed(history[-4:]):
            date = run.get("checked_at", "?")[:10]
            rates = ", ".join(
                f"{m}: {s['rate']*100:.0f}%"
                for m, s in run.get("summary", {}).items()
                if not s.get("skipped")
            )
            lines.append(f"  {date}: {rates}")

    return "\n".join(lines)


def load_audit() -> dict:
    if not AUDIT_PATH.exists():
        print("ERROR: latest_audit.json not found. Run analyse.py first.")
        sys.exit(1)
    with open(AUDIT_PATH) as f:
        return json.load(f)


def call_claude(prompt: str, system: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai not installed. Run: pip3 install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if fence_match:
        text = fence_match.group(1).strip()
    # Last resort: find the first { and last }
    if not text.startswith('{'):
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: Claude returned invalid JSON — {e}")
        print(f"  Response preview: {text[:300]}")
        sys.exit(1)


def build_audit_summary(audit: dict) -> str:
    """Condense audit data into a text block for Claude."""
    lines = []
    scores = audit.get("scores", {})
    summary = audit.get("summary", {})

    lines.append(f"SCORES: SEO={scores.get('seo')}, GEO={scores.get('geo')}, Links={scores.get('links')}, Overall={scores.get('overall')}")
    issues = summary.get("seo_issues", {})
    lines.append(f"SEO ISSUES: {issues.get('critical', 0)} critical, {issues.get('warning', 0)} warning, {issues.get('info', 0)} info")
    lines.append(f"BROKEN LINKS: {summary.get('broken_links_count', 0)}")
    lines.append(f"CONTENT GAPS: {', '.join(g['label'] for g in audit.get('content_gaps', []))}")
    lines.append("")

    lines.append("PER-PAGE AUDIT:")
    for page in audit.get("pages", []):
        if page.get("error"):
            lines.append(f"  [{page['label']}] ERROR: {page['error']}")
            continue
        meta = page.get("meta", {})
        geo = page.get("geo") or {}
        seo_issues = [i["key"] for i in page.get("seo_issues", [])]
        lines.append(f"  [{page['label']}] ({page['category']})")
        lines.append(f"    Title: {meta.get('title') or 'MISSING'}")
        lines.append(f"    Meta desc: {(meta.get('description') or 'MISSING')[:100]}")
        lines.append(f"    H1: {meta.get('h1') or 'MISSING'}")
        lines.append(f"    H2s: {', '.join(meta.get('h2s', [])) or 'none'}")
        lines.append(f"    Words: {meta.get('word_count', 0)}")
        lines.append(f"    GEO: {geo.get('readiness', '?')} — {geo.get('rationale', '')}")
        lines.append(f"    Has FAQ: {geo.get('has_faq', False)}")
        lines.append(f"    Data points: {', '.join(geo.get('data_points', [])) or 'none'}")
        lines.append(f"    SEO issues: {', '.join(seo_issues) or 'none'}")
        cwv = page.get("cwv") or {}
        if cwv and not cwv.get("error"):
            lcp = cwv.get("field_lcp_ms") or cwv.get("lab_lcp_ms", "?")
            cls = cwv.get("field_cls", "?")
            inp = cwv.get("field_inp_ms") or cwv.get("lab_inp_ms", "?")
            perf = cwv.get("performance_score", "?")
            field = cwv.get("field_overall", "no field data")
            lines.append(f"    CWV (mobile): LCP={lcp}ms, CLS={cls}, INP={inp}ms, Perf={perf}/100, Field={field}")
        elif cwv.get("error"):
            lines.append(f"    CWV: error — {cwv['error']}")
        lines.append("")

    if audit.get("broken_links"):
        lines.append("BROKEN LINKS:")
        for bl in audit["broken_links"][:10]:
            lines.append(f"  [{bl.get('status', 'ERR')}] {bl['url']} (found on: {', '.join(bl.get('found_on', [])[:2])})")

    return "\n".join(lines)


def main():
    audit = load_audit()
    audit_text = build_audit_summary(audit)
    ai_visibility_text = load_ai_visibility()

    system_prompt = f"""You are a senior SEO and GEO (generative engine optimisation) strategist with 15+ years running site audits for consumer brands. You think like a CMO — you prioritise ruthlessly, size opportunities by business impact, and translate technical findings into revenue-relevant language. You have deep expertise in SEMrush.
{BRAND_CONTEXT}
You will be given a full site audit. Identify WHERE THE BIGGEST OPPORTUNITIES ARE — quick wins and strategic bets. Be direct. Avoid boilerplate. If you see a pattern that screams "this site is leaving X on the table," name it clearly.
Respond with valid JSON only — no markdown, no explanation, no code fences."""

    schema = {
        "executive_summary": "<2-3 sentence CMO-level overview: current health and the single biggest revenue opportunity being missed>",
        "opportunity_matrix": [
            {
                "id": "<short-slug>",
                "category": "<seo_technical|seo_onpage|seo_backlinks|seo_keywords|geo_ai_visibility|geo_schema|geo_entity|geo_comparison>",
                "opportunity": "<specific opportunity — not generic>",
                "why_it_matters": "<why this moves the needle for the brand's target audience>",
                "semrush_diagnosis": "<exact report name, which filter to apply, and what number/pattern to look for>",
                "estimated_impact": "<traffic lift, authority gain, or AI visibility improvement — be specific where data allows>",
                "effort": "<low|medium|high>",
                "impact": "<high|medium|low>"
            }
        ],
        "seo_technical": [
            {
                "issue": "<specific technical issue>",
                "why_it_matters": "<business/ICP rationale>",
                "semrush_diagnosis": "<Site Audit report, filter, metric to check>",
                "estimated_impact": "<crawlability, indexation, or CWV impact>",
                "effort": "<low|medium|high>"
            }
        ],
        "seo_onpage": [
            {
                "page": "<page label or 'All pages'>",
                "issue": "<specific on-page gap: title, H1, meta desc, content>",
                "recommendation": "<what to change>",
                "semrush_diagnosis": "<On Page SEO Checker or Site Audit — which section and filter>",
                "estimated_impact": "<ranking or CTR impact>",
                "effort": "<low|medium|high>"
            }
        ],
        "seo_backlinks_keywords": [
            {
                "opportunity": "<authority gap, keyword cannibalisation, or ranking opportunity>",
                "why_it_matters": "<business rationale>",
                "semrush_diagnosis": "<Backlink Analytics / Keyword Gap / Position Tracking — exact report and filter>",
                "estimated_impact": "<DA lift, traffic potential, or SERP position gain>",
                "effort": "<low|medium|high>"
            }
        ],
        "geo_opportunities": [
            {
                "dimension": "<ai_visibility|schema_markup|entity_coverage|comparison_inclusion>",
                "page": "<page label or 'Site-wide'>",
                "issue": "<specific gap — e.g. no FAQ schema, absent from Perplexity answers for X query, entity not in knowledge graph>",
                "why_it_matters": "<why this matters for AI-generated answer visibility and the ICP>",
                "semrush_diagnosis": "<report or tool — e.g. On Page SEO Checker schema tab, or manual query test to run>",
                "recommendation": "<specific content addition, restructure, or schema to implement>",
                "example": "<concrete example of what to write, mark up, or add>",
                "estimated_impact": "<AI visibility or citation lift>",
                "effort": "<low|medium|high>"
            }
        ],
        "content_gaps": [
            {
                "missing_page": "<page that should exist>",
                "why_it_matters": "<SEO and/or GEO rationale for this ICP>",
                "suggested_url": "<suggested URL slug>",
                "key_content": "<what the page should cover to rank and appear in AI answers>"
            }
        ],
        "quick_wins": [
            {
                "action": "<specific fix — not generic advice>",
                "page": "<page label or 'All pages'>",
                "effort_hours": "<realistic estimate>",
                "impact": "<expected outcome>"
            }
        ],
        "roadmap_90_day": {
            "weeks_1_2": ["<high-impact, low-effort actions>"],
            "weeks_3_6": ["<medium-effort SEO and GEO improvements>"],
            "weeks_7_12": ["<strategic bets: new pages, schema overhaul, authority building>"]
        },
        "semrush_report_recommendations": [
            {
                "report": "<exact SEMrush report name>",
                "why": "<what specific insight it unlocks for this brand>",
                "what_to_look_for": "<specific filters, metrics, or thresholds to act on>"
            }
        ],
        "meta_description_rewrites": {
            "<page_label>": "<suggested new meta description, 140-155 chars, ICP-relevant>"
        }
    }

    user_prompt = f"""Analyse the site audit below and return JSON matching this exact schema:

{json.dumps(schema, indent=2)}

Guidelines — be concise (1 sentence per field unless detail is essential):
- opportunity_matrix: top 6 items only, sorted by impact desc then effort asc
- seo_technical: top 3 items
- seo_onpage: top 3 items
- seo_backlinks_keywords: top 3 items
- geo_opportunities: top 4 items across the 4 dimensions
- content_gaps: top 3 gaps only
- quick_wins: top 5 items, each fixable in under 2 weeks
- roadmap_90_day: 2-3 actions per phase, one sentence each
- semrush_report_recommendations: top 4 reports
- meta_description_rewrites: only pages with missing or duplicate meta description

--- SITE AUDIT DATA ---

{audit_text}

--- AI VISIBILITY (brand presence across 6 LLMs) ---

{ai_visibility_text}"""

    print(f"Calling Claude API ({MODEL})...")
    insights = call_claude(user_prompt, system_prompt)
    insights["generated_at"] = datetime.now(timezone.utc).isoformat()
    insights["model"] = MODEL

    with open(OUTPUT_PATH, "w") as f:
        json.dump(insights, f, indent=2, default=str)

    print(f"AI insights saved → {OUTPUT_PATH}")
    print(f"  Opportunity matrix: {len(insights.get('opportunity_matrix', []))}")
    print(f"  SEO technical: {len(insights.get('seo_technical', []))}")
    print(f"  SEO on-page: {len(insights.get('seo_onpage', []))}")
    print(f"  SEO backlinks/keywords: {len(insights.get('seo_backlinks_keywords', []))}")
    print(f"  GEO opportunities: {len(insights.get('geo_opportunities', []))}")
    print(f"  Content gaps: {len(insights.get('content_gaps', []))}")
    print(f"  Quick wins: {len(insights.get('quick_wins', []))}")
    print(f"  SEMrush report recommendations: {len(insights.get('semrush_report_recommendations', []))}")


if __name__ == "__main__":
    main()
