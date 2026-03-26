# geo-site-audit

> **⚠️ Use at your own risk.** This project is ~99% vibe coded. It works for its intended purpose but is not actively maintained — don't expect regular updates or production-grade polish.

Automated SEO, GEO, and content audit for any website, deployed as a live report on Vercel. Configured here as an example using [oatly.com](https://www.oatly.com).

Runs every Monday at 6am UTC. Scrapes the site, checks whether the brand is recommended by 6 LLMs (GPT-4o, Gemini 2.5 Flash, Claude Sonnet, Perplexity Sonar, Llama 4 Maverick, Mistral Large), analyses SEO issues and Core Web Vitals, generates AI insights, and publishes an updated report automatically.

## What it audits

| Area | What's checked |
|---|---|
| **SEO** | Meta titles, descriptions, H1s, OG tags, canonical URLs, word count, duplicate descriptions |
| **Core Web Vitals** | LCP, CLS, INP via Google PageSpeed Insights API (mobile, field data) |
| **GEO** | Whether the brand is recommended when people ask GPT-4o, Gemini 2.5 Flash, Claude Sonnet, Perplexity Sonar, Llama 4 Maverick, or Mistral Large. 7 queries per model. Scored as 65% AI mention rate + 35% on-page content quality |
| **Competitor detection** | Each AI response is scanned for mentions of known competitors so you can see who is being recommended instead |
| **Broken links** | Internal and external links checked for 404s |
| **Content gaps** | Missing pages flagged for SEO and GEO impact |

## How it works

```
audit.py → check_ai_visibility.py → analyse.py → generate_ai_insights.py → generate_report.py → public/data.json → Vercel
```

1. **`audit.py`** — Scrapes all pages in `_system/pages.json` via Firecrawl, extracting markdown, metadata, links, and structured SEO/GEO signals
2. **`check_ai_visibility.py`** — Sends 7 queries to 6 LLMs via OpenRouter (GPT-4o, Gemini 2.5 Flash, Claude Sonnet 4.6, Perplexity Sonar, Llama 4 Maverick, Mistral Large). Records whether the brand is mentioned, which competitors appear, and saves results + week-over-week history to `_system/ai_visibility.json`
3. **`analyse.py`** — Processes the snapshot: per-page SEO issues, Core Web Vitals via PageSpeed Insights, GEO scores (weighted by AI visibility), broken links
4. **`generate_ai_insights.py`** — Calls Claude Sonnet 4.6 via OpenRouter to generate prioritised fixes, GEO opportunities, content gaps, and a 90-day roadmap
5. **`generate_report.py`** — Compiles everything into a new report for the Next.js frontend
6. **Vercel** — Deploys the Next.js report on every push to `main`

## GEO score formula

```
GEO score = (avg AI mention rate × 0.65) + (content quality score × 0.35)
```

AI mention rate = average across all 6 models of (queries where the brand was mentioned / 7 total queries).

## What the report shows

- **Overview** — score rings for Overall, SEO, GEO, Links with week-over-week deltas
- **GEO tab** — per-model mention rates, expandable per-query breakdown showing exactly what each AI recommended and which competitors were named
- **SEO tab** — technical issues, on-page gaps, backlink/keyword opportunities, SEMrush report recommendations
- **Broken Links** — internal and external broken links
- **Content Gaps** — pages that should exist but don't

## Adapting for your own brand

1. Edit `_system/config.json` — set `site_url` to your domain
2. Edit `_system/pages.json` — list the pages you want audited and any known content gaps
3. Edit `_system/check_ai_visibility.py` — update `BRAND_VARIANTS`, `BRAND_DISPLAY`, `COMPETITORS`, and `ICP_QUERIES`
4. Edit `_system/generate_ai_insights.py` — update `BRAND_CONTEXT` with a description of your brand
5. Update `pages/index.js` — change the brand name in the header (search for "Oatly · Site Audit")

## Running locally

### Run the full audit
```bash
pip install firecrawl-py openai
FIRECRAWL_API_KEY=... OPENROUTER_API_KEY=... PSI_API_KEY=... python3 _system/audit.py --no-push
```

Required environment variables:
- `FIRECRAWL_API_KEY` — Page scraping ([firecrawl.dev](https://firecrawl.dev))
- `OPENROUTER_API_KEY` — All LLM calls — AI visibility (6 models) + AI insights ([openrouter.ai](https://openrouter.ai))
- `PSI_API_KEY` — Google PageSpeed Insights (optional but recommended)

### Re-run analysis only (no scraping)
```bash
python3 _system/analyse.py
OPENROUTER_API_KEY=... python3 _system/generate_ai_insights.py
python3 _system/generate_report.py
```

### Preview the report locally
```bash
npm install
npm run dev
```

## Adding or removing pages

Edit `_system/pages.json`. Each page needs a `url`, `label`, and `category` (`core`, `landing`, `content`, `conversion`, or `trust`). Known content gaps (pages that should exist but don't) are listed in the `known_gaps` array.

## GitHub Actions

One workflow: `.github/workflows/audit.yml`. Runs automatically every Monday at 6am UTC. Can also be triggered manually from the Actions tab.

After each run, both `public/data.json` and `_system/ai_visibility.json` are pushed back to the repo via the GitHub Contents API. The visibility file persists history across runs (up to 12 weeks) for trend tracking.

Required secrets:

| Secret | Purpose |
|---|---|
| `FIRECRAWL_API_KEY` | Page scraping via Firecrawl |
| `OPENROUTER_API_KEY` | All LLM calls — AI visibility (6 models) + AI insights (Claude Sonnet 4.6) |
| `PSI_API_KEY` | Core Web Vitals via Google PageSpeed Insights |
