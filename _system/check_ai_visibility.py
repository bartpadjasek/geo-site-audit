#!/usr/bin/env python3
"""
check_ai_visibility.py — Test brand visibility in AI-generated answers.
Queries 6 LLMs via OpenRouter with realistic questions and records
whether the brand is mentioned. Results are saved to ai_visibility.json for
week-over-week trend tracking.

Usage:
  python check_ai_visibility.py
  OPENROUTER_API_KEY=sk-or-... python check_ai_visibility.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_DIR = Path(__file__).parent
OUTPUT_PATH = SYSTEM_DIR / "ai_visibility.json"

BRAND_VARIANTS = ["oatly"]
BRAND_DISPLAY = "Oatly"
MAX_HISTORY = 12  # keep last 12 runs (~3 months of weekly audits)

# Known competitors — variants are matched case-insensitively
COMPETITORS = {
    "Alpro":          ["alpro"],
    "Califia Farms":  ["califia farms", "califia"],
    "Minor Figures":  ["minor figures"],
}

# Realistic queries a consumer or buyer would ask about oat milk
ICP_QUERIES = [
    "What are the best oat milk brands available in supermarkets right now?",
    "Which oat milk is best for baristas and coffee shops?",
    "What are the most sustainable plant-based milk brands?",
    "Which oat milk tastes closest to dairy milk?",
    "What are the top oat milk brands recommended by nutritionists?",
    "Which plant-based milk brands are most popular in Europe?",
    "What oat milk brands are best for people switching from dairy?",
]

MODELS = [
    "openai/gpt-4o",
    "google/gemini-2.5-flash",
    "anthropic/claude-sonnet-4.6",
    "perplexity/sonar",
    "meta-llama/llama-4-maverick",
    "mistralai/mistral-large",
]


def extract_mention_context(text: str) -> str:
    """Return up to 2 sentences from the response that mention GetWhy."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    relevant = [s.strip() for s in sentences if any(v in s.lower() for v in BRAND_VARIANTS)]
    return " ".join(relevant[:2])


def is_mentioned(text: str) -> bool:
    return any(v in text.lower() for v in BRAND_VARIANTS)


def extract_competitors(text: str) -> list:
    """Return list of competitor names found in the response text."""
    if not text:
        return []
    text_lower = text.lower()
    return [name for name, variants in COMPETITORS.items() if any(v in text_lower for v in variants)]


def query_openrouter(query: str, model: str, api_key: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        print("    openai not installed — skipping")
        return ""
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": query}],
        max_tokens=800,
    )
    return response.choices[0].message.content or ""


def run_queries() -> list:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\nERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    results = []
    for i, query in enumerate(ICP_QUERIES, 1):
        print(f"  Query {i}/{len(ICP_QUERIES)}: {query[:70]}...")
        for model in MODELS:
            print(f"    [{model}]", end="", flush=True)
            try:
                text = query_openrouter(query, model, api_key)
                mentioned = is_mentioned(text)
                context = extract_mention_context(text) if mentioned else None
                competitors = extract_competitors(text)
                if competitors:
                    print(f" {'MENTIONED' if mentioned else 'not mentioned'} (competitors: {', '.join(competitors)})")
                else:
                    print(f" {'MENTIONED' if mentioned else 'not mentioned'}")
                results.append({
                    "query": query,
                    "model": model,
                    "skipped": False,
                    "mentioned": mentioned,
                    "context": context,
                    "response_preview": text[:700],
                    "competitors_mentioned": competitors,
                })
            except Exception as e:
                print(f" ERROR: {e}")
                results.append({
                    "query": query,
                    "model": model,
                    "skipped": False,
                    "mentioned": False,
                    "context": None,
                    "error": str(e),
                    "response_preview": None,
                    "competitors_mentioned": [],
                })

    return results


def build_summary(results: list) -> dict:
    summary = {}
    for model in MODELS:
        # Exclude skipped entries AND errored entries — errors are not real responses
        model_results = [
            r for r in results
            if r["model"] == model and not r.get("skipped") and not r.get("error")
        ]
        if not model_results:
            summary[model] = {"skipped": True}
            continue
        mentions = sum(1 for r in model_results if r.get("mentioned"))
        total = len(model_results)
        summary[model] = {
            "mentions": mentions,
            "queries": total,
            "rate": round(mentions / total, 2) if total else 0,
        }
    return summary





def main():
    print("\n── Checking AI visibility ──")

    results = run_queries()
    summary = build_summary(results)

    # Print summary
    print("\n  Results:")
    for model, stats in summary.items():
        if stats.get("skipped"):
            print(f"    {model}: skipped")
        else:
            print(f"    {model}: {stats['mentions']}/{stats['queries']} queries mentioned {BRAND_DISPLAY} ({stats['rate']*100:.0f}%)")

    # Load existing data to append history
    history = []
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text())
            history = existing.get("history", [])
            # Carry forward previous run summary into history
            if existing.get("checked_at"):
                history.append({
                    "checked_at": existing["checked_at"],
                    "summary": existing.get("summary", {}),
                })
            history = history[-MAX_HISTORY:]
        except Exception:
            pass

    output = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "brand": BRAND_DISPLAY,
        "queries_tested": len(ICP_QUERIES),
        "models_tested": MODELS,
        "summary": summary,
        "results": results,
        "history": history,
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n  Saved → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
