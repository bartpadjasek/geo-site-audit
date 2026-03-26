# geo-site-audit

Hey — I'm not a developer, so fair warning upfront: this is something I vibe coded for a work project and decided to share because a few people asked.

The idea was simple: I wanted something that would automatically scrape our own website every week, flag SEO and GEO issues, and show us how often we're being recommended by AI tools compared to our competitors. It scratches that itch pretty well. Whether it'll work perfectly for your setup — no idea, but good luck.

I won't be updating this regularly. We run a private version internally, and if we make big improvements there I may eventually bring them over here. No promises though.

---

Automated SEO, GEO, and content audit for any website. Configured here as an example using [oatly.com](https://www.oatly.com).

Runs every Monday at 6am UTC. Scrapes the site, checks whether the brand is recommended by 6 LLMs (GPT-4o, Gemini 2.5 Flash, Claude Sonnet, Perplexity Sonar, Llama 4 Maverick, Mistral Large), analyses SEO issues and Core Web Vitals, generates AI insights, and publishes an updated report.

## What it audits

| Area | What's checked |
|---|---|
| **SEO** | Meta titles, descriptions, H1s, OG tags, canonical URLs, word count, duplicate descriptions |
| **Core Web Vitals** | LCP, CLS, INP via Google PageSpeed Insights API (mobile, field data) |
| **GEO** | Whether the brand appears when people ask GPT-4o, Gemini, Claude, Perplexity, Llama 4, or Mistral. 7 queries per model. Scored as 65% AI mention rate + 35% on-page content quality |
| **Competitor detection** | Each AI response is scanned for competitor mentions so you can see who is being recommended instead |
| **Broken links** | Internal and external links checked for 404s |
| **Content gaps** | Missing pages flagged for SEO and GEO impact |

---

## Quick start

### What you need

| Requirement | Where to get it |
|---|---|
| Python 3.9+ | [python.org](https://www.python.org/downloads/) |
| Node.js 18+ | [nodejs.org](https://nodejs.org/) |
| Firecrawl API key | [firecrawl.dev](https://www.firecrawl.dev) — free tier available |
| OpenRouter API key | [openrouter.ai](https://openrouter.ai) — pay per use, very cheap |
| PageSpeed Insights API key | [Google Cloud Console](https://console.cloud.google.com/) — free |

### Step 1 — Clone the repo

```bash
git clone https://github.com/bartpadjasek/geo-site-audit.git
cd geo-site-audit
```

### Step 2 — Configure your brand

**`_system/config.json`** — set your site URL (no API keys here — pass those as environment variables):
```json
{
  "site_url": "https://www.yourbrand.com",
  "wait_for_ms": 2000,
  "max_age_ms": 86400000,
  "scrape_proxy": "enhanced",
  "link_check_timeout_s": 10,
  "link_check_max_external": 50
}
```

**`_system/pages.json`** — list the pages you want audited:
```json
{
  "pages": [
    { "url": "https://www.yourbrand.com", "label": "Homepage", "category": "core" },
    { "url": "https://www.yourbrand.com/about", "label": "About", "category": "core" }
  ],
  "known_gaps": [
    { "url": "/faq", "label": "FAQ", "reason": "GEO opportunity — Q&A content helps AI surface your brand" }
  ]
}
```

Page categories: `core`, `landing`, `content`, `conversion`, `trust`

**`_system/check_ai_visibility.py`** — update the brand and competitors (near the top of the file):
```python
BRAND_VARIANTS = ["yourbrand"]   # how your brand name appears in text
BRAND_DISPLAY  = "YourBrand"     # display name for the report

COMPETITORS = {
    "Competitor A": ["competitor a"],
    "Competitor B": ["competitor b"],
}

ICP_QUERIES = [
    "What are the best [your category] brands?",
    "Which [your category] brands do experts recommend?",
    # ... add 5-7 realistic queries someone would ask AI about your space
]
```

**`_system/generate_ai_insights.py`** — update `BRAND_CONTEXT` with a short description of your brand (near the top of the file).

**`pages/index.js`** — update the header label. Search for `"Oatly · Site Audit"` and replace with your brand name.

### Step 3 — Install dependencies

```bash
# Python dependencies
pip install firecrawl-py openai

# Node dependencies (for the report UI)
npm install
```

### Step 4 — Run the audit

```bash
FIRECRAWL_API_KEY=fc-... OPENROUTER_API_KEY=sk-or-... PSI_API_KEY=AIza... python3 _system/audit.py --no-push
```

All API keys are passed as environment variables — never put them in `config.json`.

This will:
1. Scrape all pages via Firecrawl
2. Query 6 LLMs to check AI visibility
3. Analyse SEO issues and Core Web Vitals
4. Generate AI insights and recommendations
5. Compile everything into `public/data.json`

### Step 5 — View the report

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser. That's it.

---

## Automated weekly runs

### Option A — Vercel (hosted, auto-deploys)

1. Push this repo to GitHub
2. Connect the repo to [Vercel](https://vercel.com) — it will auto-detect Next.js and deploy
3. Add the following secrets to your GitHub repo under **Settings → Secrets → Actions**:

| Secret | Purpose |
|---|---|
| `FIRECRAWL_API_KEY` | Page scraping |
| `OPENROUTER_API_KEY` | AI visibility checks + insights |
| `PSI_API_KEY` | Core Web Vitals |

4. The workflow in `.github/workflows/audit.yml` runs every Monday at 6am UTC, pushes the updated report to the repo, and Vercel redeploys automatically. You can also trigger it manually from the **Actions** tab.

### Option B — Run locally on a schedule

If you don't want to use Vercel, you can run the audit manually whenever you want and just view it at `localhost:3000`:

```bash
# Run the audit
OPENROUTER_API_KEY=sk-or-... python3 _system/audit.py --no-push

# View the report
npm run dev
```

Or set up a cron job to run it automatically:
```bash
# Run every Monday at 6am (add to crontab -e)
0 6 * * 1 cd /path/to/geo-site-audit && OPENROUTER_API_KEY=sk-or-... FIRECRAWL_API_KEY=fc-... python3 _system/audit.py --no-push
```

---

## Re-running parts of the pipeline

If you want to regenerate the report without re-scraping (e.g. to tweak the AI insights):

```bash
# Re-run analysis only (uses existing snapshot)
python3 _system/analyse.py

# Re-generate AI insights only
OPENROUTER_API_KEY=sk-or-... python3 _system/generate_ai_insights.py

# Recompile the report
python3 _system/generate_report.py

# Preview
npm run dev
```

---

## How it works

```
audit.py → check_ai_visibility.py → analyse.py → generate_ai_insights.py → generate_report.py → public/data.json
```

1. **`audit.py`** — Scrapes all pages in `_system/pages.json` via Firecrawl, extracting markdown, metadata, links, and structured SEO/GEO signals
2. **`check_ai_visibility.py`** — Sends 7 queries to 6 LLMs via OpenRouter. Records whether the brand is mentioned, which competitors appear, and saves results + week-over-week history to `_system/ai_visibility.json`
3. **`analyse.py`** — Per-page SEO issues, Core Web Vitals via PageSpeed Insights, GEO scores, broken links
4. **`generate_ai_insights.py`** — Calls Claude Sonnet 4.6 via OpenRouter to generate prioritised fixes, GEO opportunities, content gaps, and a 90-day roadmap
5. **`generate_report.py`** — Compiles everything into `public/data.json` for the Next.js frontend

## GEO score formula

```
GEO score = (avg AI mention rate × 0.65) + (content quality score × 0.35)
```

AI mention rate = average across all 6 models of (queries where the brand was mentioned / 7 total queries).
