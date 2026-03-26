# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## What this repo is

Automated SEO, GEO (Generative Engine Optimisation), and content audit for [getwhy.io](https://www.getwhy.io). A Python pipeline scrapes the site weekly, checks AI visibility, analyses issues, and publishes results as a Next.js report deployed on Vercel.

## Commands

### Frontend (Next.js report)
```bash
npm install
npm run dev       # preview report at localhost:3000
npm run build     # production build
```

### Full audit pipeline
```bash
pip install firecrawl-py anthropic openai
FIRECRAWL_API_KEY=... ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=... PSI_API_KEY=... python3 _system/audit.py --no-push
```
All 5 API keys are required. The audit will stop with a clear error if any are missing.

### Individual pipeline steps (no re-scraping)
```bash
python3 _system/analyse.py                                # reprocess latest snapshot → snapshots/latest_audit.json
ANTHROPIC_API_KEY=... python3 _system/generate_ai_insights.py   # Claude recommendations → _system/ai_insights.json
python3 _system/generate_report.py                        # compile → public/data.json
OPENAI_API_KEY=... GEMINI_API_KEY=... ANTHROPIC_API_KEY=... python3 _system/check_ai_visibility.py   # AI visibility check → _system/ai_visibility.json
```

## Architecture

### Pipeline flow
```
audit.py → check_ai_visibility.py → analyse.py → generate_ai_insights.py → generate_report.py → public/data.json → Vercel
```

1. **`_system/audit.py`** — Scrapes all pages in `_system/pages.json` via Firecrawl (markdown + JSON structured extraction + links). Saves a dated snapshot to `snapshots/YYYY-MM-DD.json`. `analyse.py` picks the most recent non-baseline file there.
2. **`_system/check_ai_visibility.py`** — Sends 7 ICP buyer queries to GPT-4o, Gemini 2.0 Flash, and Claude. Records whether GetWhy is mentioned; persists history (up to 12 weeks) in `_system/ai_visibility.json`.
3. **`_system/analyse.py`** — Reads the latest snapshot, runs per-page SEO checks, calls Google PageSpeed Insights API for Core Web Vitals, scores GEO readiness, checks broken links. Writes `snapshots/latest_audit.json`.
4. **`_system/generate_ai_insights.py`** — Sends the audit summary + competitor context (from `../competitors/public/data.json`) to Claude and writes structured JSON recommendations to `_system/ai_insights.json`.
5. **`_system/generate_report.py`** — Merges `latest_audit.json` + `ai_insights.json` + `ai_visibility.json` into `public/data.json`, which is the sole data source for the Next.js frontend.

### GEO score formula
```
GEO score = (avg AI mention rate × 0.65) + (content quality score × 0.35)
```
Weights are defined as constants at the top of `_system/analyse.py` (`GEO_WEIGHT_AI_VISIBILITY`, `GEO_WEIGHT_CONTENT`).

### Frontend
- Single-page Next.js app: `pages/index.js` (all UI in one file, ~1300 lines).
- Data loaded at build time via `getStaticProps` from `public/data.json` — no runtime API calls.
- Tailwind with a custom brand palette: `burgundy`, `fuchsia`, `beige`, `teal`, `ink`. Custom fonts: `Aeonik` (sans) and `EdictDisplay` (display/serif).
- Five tabs: Overview, SEO, GEO, Broken Links, Content Gaps.

### Key data files
| File | Purpose | Git-tracked? |
|---|---|---|
| `_system/pages.json` | Pages to audit + known content gaps | Yes |
| `_system/config.json` | API keys, Firecrawl settings | **No** (gitignored) |
| `_system/ai_visibility.json` | AI mention history (up to 12 weeks) | **No** (gitignored locally; pushed by CI) |
| `_system/ai_insights.json` | Latest Claude recommendations | **No** (gitignored) |
| `snapshots/` | Raw Firecrawl snapshots + latest_audit.json | **No** (gitignored) |
| `public/data.json` | Compiled report consumed by Next.js | Yes (updated by CI) |

### Adding or removing audited pages
Edit `_system/pages.json`. Each page requires `url`, `label`, and `category` (`core`, `landing`, `content`, `conversion`, or `trust`). Known content gaps (pages that should exist but don't) go in the `known_gaps` array.

## CI / Deployment
- **GitHub Actions** (`.github/workflows/audit.yml`): runs every Monday at 6am UTC; can be triggered manually. Uses `--no-push` flag and instead writes `public/data.json` and `_system/ai_visibility.json` back to the repo via the GitHub Contents API.
- **Vercel**: deploys automatically on every push to `main` (triggered by the CI commit of `public/data.json`).
- Required secrets: `FIRECRAWL_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `PSI_API_KEY`.

## Competitor context
`generate_ai_insights.py` reads `../competitors/public/data.json` (a sibling repo) for competitor benchmarking context passed to Claude. If that file doesn't exist, Claude proceeds without it.
