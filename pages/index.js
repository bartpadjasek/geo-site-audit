import fs from "fs";
import path from "path";
import { useState } from "react";

// ── Design tokens ─────────────────────────────────────────────────────────────

const SEV_CFG = {
  critical: { label: "Critical", bg: "bg-fuchsia-50",   text: "text-fuchsia-500",  border: "border-fuchsia-100", dot: "bg-fuchsia-500"  },
  warning:  { label: "Warning",  bg: "bg-amber-50",     text: "text-amber-700",    border: "border-amber-200",   dot: "bg-amber-400"    },
  info:     { label: "Info",     bg: "bg-teal-50",      text: "text-teal-400",     border: "border-teal-100",    dot: "bg-teal-300"     },
};

const GEO_CFG = {
  high:   { bg: "bg-teal-100",    text: "text-teal-400"     },
  medium: { bg: "bg-amber-100",   text: "text-amber-700"    },
  low:    { bg: "bg-fuchsia-100", text: "text-fuchsia-500"  },
};

const EFFORT_CFG = {
  low:    "bg-teal-50 text-teal-400 border-teal-100",
  medium: "bg-amber-50 text-amber-600 border-amber-200",
  high:   "bg-fuchsia-50 text-fuchsia-500 border-fuchsia-100",
};

const DIM_LABEL = {
  ai_visibility:        "AI Visibility",
  schema_markup:        "Schema Markup",
  entity_coverage:      "Entity Coverage",
  comparison_inclusion: "Comparison / Best-of",
};

const CAT_CFG = {
  core:       "bg-burgundy-50 text-burgundy border-burgundy-100",
  landing:    "bg-beige-300 text-burgundy-500 border-beige-400",
  content:    "bg-teal-50 text-teal-400 border-teal-100",
  conversion: "bg-fuchsia-50 text-fuchsia-500 border-fuchsia-100",
  trust:      "bg-beige-100 text-ink/50 border-beige-300",
};

const TABS = ["Overview", "SEO", "GEO", "Broken Links", "Content Gaps"];

// ── Components ────────────────────────────────────────────────────────────────

function ScoreRing({ score, delta, label, size = 88 }) {
  const pct = Math.max(0, Math.min(100, score || 0));
  const color = pct >= 80 ? "#5B7979" : pct >= 60 ? "#f59e0b" : "#FA1E81";
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const showDelta = delta != null && delta !== 0;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" style={{ position: "absolute" }}>
          <circle cx={size/2} cy={size/2} r={r} stroke="#E6D9CC" strokeWidth={7} fill="none" />
          <circle cx={size/2} cy={size/2} r={r} stroke={color} strokeWidth={7} fill="none"
            strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold text-ink">{Math.round(pct)}</span>
        </div>
      </div>
      <span className="text-xs text-ink/50 font-medium tracking-wide uppercase">{label}</span>
      {showDelta ? (
        <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${delta > 0 ? "bg-teal-50 text-teal-500" : "bg-fuchsia-50 text-fuchsia-500"}`}>
          {delta > 0 ? `+${Math.round(delta)}` : Math.round(delta)}
        </span>
      ) : (
        <span className="h-5" />
      )}
    </div>
  );
}

function Badge({ children, className = "" }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${className}`}>
      {children}
    </span>
  );
}

function SectionLabel({ children }) {
  return <p className="text-xs font-medium uppercase tracking-widest text-ink/40 mb-2">{children}</p>;
}

function IssueRow({ issue }) {
  const cfg = SEV_CFG[issue.severity] || SEV_CFG.info;
  return (
    <div className={`flex items-start gap-2 px-3 py-2 rounded-lg ${cfg.bg} ${cfg.border} border text-xs`}>
      <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
      <span className={`font-medium ${cfg.text}`}>{issue.label}</span>
    </div>
  );
}

function Card({ children, className = "" }) {
  return (
    <div className={`bg-white rounded-2xl border border-beige-300 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

function AiBadge() {
  return (
    <div className="w-6 h-6 rounded-md bg-burgundy flex items-center justify-center flex-shrink-0">
      <span className="text-white text-xs font-bold">AI</span>
    </div>
  );
}

// ── Tab: Overview ─────────────────────────────────────────────────────────────

function OverviewTab({ report }) {
  const { scores, summary, ai, previous_scores } = report;
  const seoIssues = summary?.seo_issues || {};

  const delta = (key) => {
    if (!previous_scores || previous_scores[key] == null || scores?.[key] == null) return null;
    const d = Math.round(scores[key]) - Math.round(previous_scores[key]);
    return d === 0 ? null : d;
  };

  return (
    <div className="space-y-5">

      {/* Score rings */}
      <Card className="p-6">
        <h2 className="font-display text-xl text-burgundy mb-6">Site Health</h2>
        <div className="flex flex-wrap gap-8 justify-around mb-6">
          <ScoreRing score={scores?.overall} delta={delta("overall")} label="Overall" size={96} />
          <ScoreRing score={scores?.seo} delta={delta("seo")} label="SEO" size={96} />
          <ScoreRing score={scores?.geo} delta={delta("geo")} label="GEO" size={96} />
          <ScoreRing score={scores?.links} delta={delta("links")} label="Links" size={96} />
        </div>
        <div className="grid grid-cols-3 gap-3 text-center border-t border-beige-300 pt-4">
          {Object.entries(seoIssues).map(([sev, count]) => (
            <div key={sev}>
              <p className={`text-xl font-bold ${SEV_CFG[sev]?.text || "text-ink"}`}>{count}</p>
              <p className="text-xs text-ink/40 capitalize mt-0.5">{sev} SEO issues</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Score Breakdown */}
      {scores && (
        <Card className="p-5">
          <h2 className="font-medium text-ink mb-4">Why Your Scores Look This Way</h2>
          <div className="space-y-3">
            <div className="border border-beige-300 rounded-xl p-3">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium text-ink">SEO — {Math.round(scores.seo || 0)}/100</p>
                <span className={`w-2 h-2 rounded-full ${(scores.seo || 0) >= 80 ? "bg-teal-400" : (scores.seo || 0) >= 60 ? "bg-amber-400" : "bg-fuchsia-500"}`} />
              </div>
              <p className="text-xs text-ink/60">
                {(seoIssues.critical || 0) > 0 || (seoIssues.warning || 0) > 0
                  ? `${seoIssues.critical || 0} critical issues (−${(seoIssues.critical || 0) * 10} pts) and ${seoIssues.warning || 0} warnings (−${(seoIssues.warning || 0) * 5} pts) across ${summary?.pages_audited || 0} pages. Fix critical issues first — they each cost 10 points.`
                  : `No critical or warning issues across ${summary?.pages_audited || 0} pages. Info-level items only.`}
              </p>
            </div>
            <div className="border border-beige-300 rounded-xl p-3">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium text-ink">GEO — {Math.round(scores.geo || 0)}/100</p>
                <span className={`w-2 h-2 rounded-full ${(scores.geo || 0) >= 80 ? "bg-teal-400" : (scores.geo || 0) >= 60 ? "bg-amber-400" : "bg-fuchsia-500"}`} />
              </div>
              {scores.geo_detail ? (
                <p className="text-xs text-ink/60">
                  AI visibility: <span className="font-medium text-ink/80">{scores.geo_detail.ai_visibility != null ? `${Math.round(scores.geo_detail.ai_visibility)}%` : "not measured"}</span> (65% weight) · Content quality: <span className="font-medium text-ink/80">{scores.geo_detail.content_quality || 0}/100</span> (35% weight).
                  {scores.geo_detail.ai_visibility != null && scores.geo_detail.ai_visibility < 30 && " The brand is rarely surfaced when buyers ask AI — this is the main drag on the GEO score. See the GEO tab for details."}
                </p>
              ) : (
                <p className="text-xs text-ink/60">Scored on page content quality. AI visibility not yet measured.</p>
              )}
            </div>
            <div className="border border-beige-300 rounded-xl p-3">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium text-ink">Links — {Math.round(scores.links || 0)}/100</p>
                <span className={`w-2 h-2 rounded-full ${(scores.links || 0) >= 80 ? "bg-teal-400" : (scores.links || 0) >= 60 ? "bg-amber-400" : "bg-fuchsia-500"}`} />
              </div>
              <p className="text-xs text-ink/60">
                {(summary?.broken_links_count || 0) === 0
                  ? "No broken links found."
                  : `${summary.broken_links_count} broken link${summary.broken_links_count > 1 ? "s" : ""} found (−${summary.broken_links_count * 10} pts). See the Broken Links tab for details.`}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* AI Executive Summary */}
      {ai?.executive_summary && (
        <Card className="p-6">
          <div className="flex items-start gap-3">
            <AiBadge />
            <div>
              <h2 className="font-medium text-ink mb-2">Executive Summary</h2>
              <p className="text-sm text-ink/70 leading-relaxed">{ai.executive_summary}</p>
              {ai.generated_at && (
                <p className="text-xs text-ink/30 mt-2">
                  Generated {new Date(ai.generated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Opportunity matrix */}
      {ai?.opportunity_matrix?.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <AiBadge />
            <h2 className="font-medium text-ink">Opportunity Matrix</h2>
          </div>
          <div className="space-y-3">
            {ai.opportunity_matrix.map((opp, i) => (
              <div key={i} className="border border-beige-300 rounded-xl p-3">
                <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                  <span className="text-xs bg-beige-100 text-ink/50 px-1.5 py-0.5 rounded border border-beige-200">{opp.category?.replace(/_/g, " ")}</span>
                  <Badge className={opp.impact === "high" ? "bg-fuchsia-50 text-fuchsia-500 border-fuchsia-100" : opp.impact === "medium" ? "bg-amber-50 text-amber-600 border-amber-200" : "bg-beige-100 text-ink/40 border-beige-200"}>{opp.impact} impact</Badge>
                  <Badge className={EFFORT_CFG[opp.effort] || ""}>{opp.effort} effort</Badge>
                </div>
                <p className="text-sm font-medium text-ink">{opp.opportunity}</p>
                <p className="text-xs text-ink/50 mt-1">{opp.why_it_matters}</p>
                {opp.estimated_impact && <p className="text-xs text-teal-400 mt-1 font-medium">{opp.estimated_impact}</p>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Quick wins */}
      {ai?.quick_wins?.length > 0 && (
        <div className="bg-teal-400 rounded-2xl p-5">
          <h3 className="font-medium text-white mb-3">Quick Wins</h3>
          <ul className="space-y-2">
            {ai.quick_wins.map((win, i) => {
              const action = typeof win === "string" ? win : win.action;
              const meta = typeof win === "object" ? [win.page, win.effort_hours, win.impact].filter(Boolean).join(" · ") : null;
              return (
                <li key={i} className="flex items-start gap-2.5 text-sm text-white/90">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-white/20 text-white text-xs flex items-center justify-center font-bold mt-0.5">{i + 1}</span>
                  <div>
                    <p>{action}</p>
                    {meta && <p className="text-xs text-white/50 mt-0.5">{meta}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Pages Audited",  value: summary?.pages_audited || 0 },
          { label: "Broken Links",   value: summary?.broken_links_count || 0, warn: (summary?.broken_links_count || 0) > 0 },
          { label: "Content Gaps",   value: summary?.content_gaps_count || 0 },
          { label: "Pages Errored",  value: summary?.pages_errored || 0,     warn: (summary?.pages_errored || 0) > 0 },
        ].map(({ label, value, warn }) => (
          <Card key={label} className="p-4 text-center">
            <p className={`text-2xl font-bold ${warn && value > 0 ? "text-fuchsia-500" : "text-burgundy"}`}>{value}</p>
            <p className="text-xs text-ink/40 mt-1">{label}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Tab: SEO ──────────────────────────────────────────────────────────────────

function SEOTab({ report }) {
  const { pages, ai } = report;
  const [expanded, setExpanded] = useState(null);

  const sorted = [...(pages || [])].sort((a, b) => {
    const critA = (a.seo_issues || []).filter(i => i.severity === "critical").length;
    const critB = (b.seo_issues || []).filter(i => i.severity === "critical").length;
    return critB - critA;
  });

  return (
    <div className="space-y-5">

      {/* AI SEO sections */}
      {[
        { key: "seo_technical",         label: "Technical SEO" },
        { key: "seo_onpage",            label: "On-Page SEO" },
        { key: "seo_backlinks_keywords", label: "Backlinks & Keywords" },
      ].map(({ key, label }) =>
        ai?.[key]?.length > 0 && (
          <Card key={key} className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <AiBadge />
              <h2 className="font-medium text-ink">{label}</h2>
            </div>
            <div className="space-y-4">
              {ai[key].map((item, i) => (
                <div key={i} className="border border-beige-300 rounded-xl p-3 text-sm">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="font-medium text-ink">{item.issue || item.opportunity || item.page}</p>
                    <Badge className={EFFORT_CFG[item.effort] || ""}>{item.effort}</Badge>
                  </div>
                  {item.why_it_matters && <p className="text-xs text-ink/50 mb-1">{item.why_it_matters}</p>}
                  {item.recommendation && <p className="text-xs text-ink/70 mb-1"><span className="font-medium">Fix:</span> {item.recommendation}</p>}
                  {item.semrush_diagnosis && (
                    <p className="text-xs text-ink/40 bg-beige-50 rounded-lg px-2 py-1.5 mt-1.5">
                      <span className="font-medium text-ink/60">SEMrush:</span> {item.semrush_diagnosis}
                    </p>
                  )}
                  {item.estimated_impact && <p className="text-xs text-teal-400 font-medium mt-1">{item.estimated_impact}</p>}
                </div>
              ))}
            </div>
          </Card>
        )
      )}

      {/* SEMrush report recommendations */}
      {ai?.semrush_report_recommendations?.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <AiBadge />
            <h2 className="font-medium text-ink">SEMrush Reports to Run</h2>
          </div>
          <div className="space-y-3">
            {ai.semrush_report_recommendations.map((rec, i) => (
              <div key={i} className="border border-beige-300 rounded-xl p-3">
                <p className="text-sm font-medium text-ink mb-1">{rec.report}</p>
                <p className="text-xs text-ink/50 mb-1">{rec.why}</p>
                {rec.what_to_look_for && <p className="text-xs text-ink/40 italic">{rec.what_to_look_for}</p>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Meta description rewrites */}
      {ai?.meta_description_rewrites && Object.keys(ai.meta_description_rewrites).length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <AiBadge />
            <h2 className="font-medium text-ink">Suggested Meta Descriptions</h2>
          </div>
          <div className="space-y-3">
            {Object.entries(ai.meta_description_rewrites).map(([page, desc]) => (
              <div key={page} className="border border-beige-300 rounded-xl p-3">
                <p className="text-xs font-medium text-ink/40 mb-1">{page}</p>
                <p className="text-sm text-ink">{desc}</p>
                <p className="text-xs text-ink/30 mt-1">{desc.length} chars</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Per-page audit */}
      <h2 className="font-medium text-ink">Per-Page SEO Audit</h2>
      <div className="space-y-3">
        {sorted.map((page, i) => {
          const isOpen = expanded === i;
          const issues = page.seo_issues || [];
          const critCount = issues.filter(x => x.severity === "critical").length;
          const warnCount = issues.filter(x => x.severity === "warning").length;

          return (
            <Card key={i} className="overflow-hidden">
              <button
                onClick={() => setExpanded(isOpen ? null : i)}
                className="w-full px-5 py-4 flex items-center justify-between gap-3 text-left hover:bg-beige-50 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Badge className={CAT_CFG[page.category] || CAT_CFG.core}>{page.category}</Badge>
                  <span className="font-medium text-ink truncate">{page.label}</span>
                  {page.error && <span className="text-xs text-fuchsia-500">Error scraping</span>}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {critCount > 0 && <span className="text-xs font-semibold bg-fuchsia-50 text-fuchsia-500 px-2 py-0.5 rounded-full">{critCount} critical</span>}
                  {warnCount > 0 && <span className="text-xs font-semibold bg-amber-50 text-amber-600 px-2 py-0.5 rounded-full">{warnCount} warning</span>}
                  {issues.length === 0 && !page.error && <span className="text-xs text-teal-400 font-medium">No issues</span>}
                  <span className="text-ink/30 text-sm">{isOpen ? "▲" : "▼"}</span>
                </div>
              </button>

              {isOpen && (
                <div className="px-5 pb-5 border-t border-beige-200 pt-4 space-y-4">
                  {page.error ? (
                    <p className="text-sm text-fuchsia-500">{page.error}</p>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <SectionLabel>Page metadata</SectionLabel>
                          <div className="text-xs space-y-1.5">
                            {[
                              ["Title", page.meta?.title],
                              ["Description", page.meta?.description],
                              ["Canonical", page.meta?.canonical],
                              ["H1", page.meta?.h1],
                            ].map(([label, val]) => (
                              <div key={label}>
                                <span className="text-ink/40 inline-block w-24">{label}:</span>
                                {val ? <span className="text-ink">{val}</span> : <span className="text-fuchsia-500">Missing</span>}
                              </div>
                            ))}
                            <div>
                              <span className="text-ink/40 inline-block w-24">Words:</span>
                              <span className={`${(page.meta?.word_count || 0) < 300 ? "text-amber-600" : "text-ink"}`}>{page.meta?.word_count || 0}</span>
                            </div>
                          </div>
                        </div>
                        <div>
                          <SectionLabel>H2 headings</SectionLabel>
                          {page.meta?.h2s?.length > 0
                            ? <ul className="text-xs text-ink/60 space-y-1">{page.meta.h2s.map((h, j) => <li key={j} className="truncate">· {h}</li>)}</ul>
                            : <p className="text-xs text-ink/30">None found</p>}
                        </div>
                      </div>
                      {issues.length > 0 && (
                        <div>
                          <SectionLabel>Issues</SectionLabel>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {issues.map((issue, j) => <IssueRow key={j} issue={issue} />)}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Tab: GEO ──────────────────────────────────────────────────────────────────

const MODEL_DISPLAY = {
  "openai/gpt-4o":               "OpenAI",
  "google/gemini-2.5-flash":     "Gemini",
  "anthropic/claude-sonnet-4.6": "Claude",
  "perplexity/sonar":            "Perplexity",
  "meta-llama/llama-4-maverick": "Llama 4",
  "mistralai/mistral-large":     "Mistral",
};

const stripMd = (s) => (s || "")
  .replace(/\|[-: |]+\|/g, "")
  .replace(/\|/g, " · ")
  .replace(/#{1,6}\s*/g, "")
  .replace(/\*\*(.*?)\*\*/g, "$1")
  .replace(/\*(.*?)\*/g, "$1")
  .replace(/\n{2,}/g, " · ")
  .replace(/\s{2,}/g, " ")
  .trim();

function GEOTab({ report }) {
  const { pages, ai, ai_visibility } = report;
  const [expandedQueries, setExpandedQueries] = useState({});

  const sorted = [...(pages || [])].filter(p => p.geo).sort((a, b) => {
    const order = { low: 0, medium: 1, high: 2 };
    return (order[a.geo?.readiness] ?? 1) - (order[b.geo?.readiness] ?? 1);
  });

  // Group ai_visibility results by query for the per-query breakdown
  const uniqueQueries = Array.from(new Set((ai_visibility?.results || []).map(r => r.query)));

  return (
    <div className="space-y-5">
      <div className="bg-burgundy rounded-2xl p-5">
        <h3 className="font-medium text-white mb-1">What is GEO?</h3>
        <p className="text-sm text-white/70 leading-relaxed">
          Generative Engine Optimisation — how well your pages appear when AI tools like ChatGPT, Gemini, Claude, Perplexity,
          Llama, or Mistral surface answers for queries in your space. High-GEO pages have clear entity definitions, structured
          answers, specific data points, and FAQ-style content.
        </p>
      </div>

      {/* AI Visibility Results */}
      {ai_visibility?.summary && Object.keys(ai_visibility.summary).length > 0 && (
        <Card className="p-5">
          <h2 className="font-medium text-ink mb-1">AI Visibility — Are You Being Recommended?</h2>
          <p className="text-xs text-ink/40 mb-4">
            We asked 7 realistic questions to ChatGPT, Gemini, Claude, Perplexity, Llama 4, and Mistral — the kind someone would ask when looking for a brand like this. Here is how often the brand was mentioned.
          </p>

          {/* Per-model rate cards */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            {Object.entries(ai_visibility.summary).map(([model, stats]) => {
              const name = MODEL_DISPLAY[model] || model;
              if (stats.skipped) return (
                <div key={model} className="bg-beige-100 border border-beige-200 rounded-xl p-3 text-center">
                  <p className="text-xs text-ink/30 font-medium">{name}</p>
                  <p className="text-xs text-ink/20 mt-1">not measured</p>
                </div>
              );
              const pct = Math.round(stats.rate * 100);
              const color = pct >= 50 ? "text-teal-400" : pct >= 20 ? "text-amber-600" : "text-fuchsia-500";
              return (
                <div key={model} className="bg-beige-50 border border-beige-200 rounded-xl p-3 text-center">
                  <p className="text-xs text-ink/40 font-medium mb-1">{name}</p>
                  <p className={`text-2xl font-bold ${color}`}>{pct}%</p>
                  <p className="text-xs text-ink/30 mt-0.5">{stats.mentions}/{stats.queries} queries</p>
                </div>
              );
            })}
          </div>

          {/* Per-query breakdown */}
          <SectionLabel>Per-Query Breakdown — click any row to see what each AI said</SectionLabel>
          <div className="space-y-2">
            {uniqueQueries.map((query, qi) => {
              const queryResults = (ai_visibility.results || []).filter(r => r.query === query && !r.skipped);
              const anyMentioned = queryResults.some(r => r.mentioned);
              const isOpen = !!expandedQueries[qi];
              // Deduplicated competitors mentioned across all models for this query
              const allCompetitors = [...new Set(queryResults.flatMap(r => r.competitors_mentioned || []))];
              return (
                <div key={qi} className={`border rounded-xl overflow-hidden ${anyMentioned ? "border-teal-200" : "border-beige-300"}`}>
                  {/* Header — always visible, click to expand */}
                  <button
                    onClick={() => setExpandedQueries(e => ({ ...e, [qi]: !e[qi] }))}
                    className={`w-full text-left px-3 pt-3 pb-2 flex items-start gap-2 transition-colors hover:bg-beige-50 ${anyMentioned ? "bg-teal-50/30" : ""}`}
                  >
                    <span className={`flex-shrink-0 w-4 h-4 rounded-full text-xs flex items-center justify-center font-bold mt-0.5 ${anyMentioned ? "bg-teal-100 text-teal-500" : "bg-fuchsia-50 text-fuchsia-400"}`}>
                      {anyMentioned ? "✓" : "✗"}
                    </span>
                    <p className="text-xs text-ink/70 leading-relaxed flex-1">{query}</p>
                    <span className="text-ink/25 text-xs flex-shrink-0 mt-0.5">{isOpen ? "▲" : "▼"}</span>
                  </button>
                  <div className={`px-3 pb-3 flex flex-wrap gap-1.5 ${anyMentioned ? "bg-teal-50/30" : ""}`}>
                    {queryResults.map(r => (
                      <span key={r.model} className={`text-xs px-2 py-0.5 rounded-full border ${r.mentioned ? "bg-teal-50 text-teal-500 border-teal-200" : r.error ? "bg-amber-50 text-amber-600 border-amber-200" : "bg-beige-100 text-ink/30 border-beige-200"}`}>
                        {MODEL_DISPLAY[r.model] || r.model} {r.mentioned ? "✓" : r.error ? "err" : "✗"}
                      </span>
                    ))}
                    {allCompetitors.map(c => (
                      <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-fuchsia-50 text-fuchsia-500 border border-fuchsia-100 font-medium">
                        {c}
                      </span>
                    ))}
                  </div>

                  {/* Expanded — per-model response detail */}
                  {isOpen && (
                    <div className="border-t border-beige-200 bg-beige-50/40 px-3 py-3 space-y-3">
                      {queryResults.map(r => {
                        const name = MODEL_DISPLAY[r.model] || r.model;
                        if (r.error) return (
                          <div key={r.model} className="border border-amber-100 rounded-lg p-2.5">
                            <p className="text-xs font-semibold text-amber-600 mb-1">{name} — API error</p>
                            <p className="text-xs text-ink/40">{r.error.slice(0, 120)}</p>
                          </div>
                        );
                        const competitors = r.competitors_mentioned || [];
                        return (
                          <div key={r.model} className={`border rounded-lg p-2.5 ${r.mentioned ? "border-teal-100 bg-teal-50/50" : "border-beige-200 bg-white"}`}>
                            <p className={`text-xs font-semibold mb-2 ${r.mentioned ? "text-teal-500" : "text-ink/40"}`}>
                              {name} — {r.mentioned ? "mentioned the brand" : "did not mention the brand"}
                            </p>
                            {r.mentioned && r.context && (
                              <div className="bg-teal-50 border border-teal-100 rounded-md p-2 mb-2">
                                <p className="text-xs text-teal-500/60 mb-0.5">Mentioned as:</p>
                                <p className="text-xs text-teal-700 italic">"{r.context}"</p>
                              </div>
                            )}
                            {competitors.length > 0 && (
                              <div className="flex flex-wrap gap-1 mb-2">
                                {competitors.map(c => (
                                  <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-fuchsia-50 text-fuchsia-500 border border-fuchsia-100 font-medium">
                                    {c}
                                  </span>
                                ))}
                              </div>
                            )}
                            {!r.mentioned && r.response_preview && (
                              <div>
                                <p className="text-xs text-ink/40 mb-1">What {name} recommended instead:</p>
                                <p className="text-xs text-ink/60 leading-relaxed">{stripMd(r.response_preview)}</p>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {ai?.geo_opportunities?.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <AiBadge />
            <h2 className="font-medium text-ink">GEO Opportunities</h2>
          </div>
          <div className="space-y-4">
            {ai.geo_opportunities.map((opp, i) => (
              <div key={i} className="border border-beige-300 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  {opp.dimension && <Badge className="bg-burgundy/10 text-burgundy border-burgundy/20">{DIM_LABEL[opp.dimension] || opp.dimension}</Badge>}
                  <p className="text-sm font-medium text-ink">{opp.page}</p>
                  {opp.effort && <Badge className={`ml-auto ${EFFORT_CFG[opp.effort] || ""}`}>{opp.effort} effort</Badge>}
                </div>
                {opp.issue && <p className="text-xs text-ink/60 mb-1"><span className="font-medium text-ink/80">Issue:</span> {opp.issue}</p>}
                {opp.why_it_matters && <p className="text-xs text-ink/50 mb-1"><span className="font-medium text-ink/70">Why it matters:</span> {opp.why_it_matters}</p>}
                <p className="text-xs text-ink/70 mb-2"><span className="font-medium">Fix:</span> {opp.recommendation}</p>
                {opp.semrush_diagnosis && (
                  <p className="text-xs text-ink/40 bg-beige-50 rounded-lg px-2 py-1.5 mb-2">
                    <span className="font-medium text-ink/60">SEMrush:</span> {opp.semrush_diagnosis}
                  </p>
                )}
                {opp.example && (
                  <div className="bg-beige-100 border border-beige-300 rounded-lg p-2.5 mb-2">
                    <p className="text-xs text-ink/40 mb-1">Example:</p>
                    <p className="text-xs text-ink/70 italic">"{opp.example}"</p>
                  </div>
                )}
                {opp.estimated_impact && <p className="text-xs text-teal-400 font-medium">{opp.estimated_impact}</p>}
              </div>
            ))}
          </div>
        </Card>
      )}

      <h2 className="font-medium text-ink">Content Quality by Page</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sorted.map((page, i) => {
          const geo = page.geo;
          const cfg = GEO_CFG[geo.readiness] || GEO_CFG.medium;
          return (
            <Card key={i} className="p-4">
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <p className="font-medium text-ink text-sm">{page.label}</p>
                  <Badge className={`mt-1 ${CAT_CFG[page.category] || CAT_CFG.core}`}>{page.category}</Badge>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-bold ${cfg.bg} ${cfg.text}`}>
                  {geo.readiness?.toUpperCase()} · {geo.score}
                </div>
              </div>
              {geo.rationale && <p className="text-xs text-ink/60 mb-2">{geo.rationale}</p>}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className={`px-2 py-1.5 rounded-lg ${geo.has_faq ? "bg-teal-100 text-teal-400" : "bg-beige-100 text-ink/30"}`}>
                  {geo.has_faq ? "Has FAQ" : "No FAQ"}
                </div>
                <div className={`px-2 py-1.5 rounded-lg ${geo.data_points?.length > 0 ? "bg-teal-100 text-teal-400" : "bg-beige-100 text-ink/30"}`}>
                  {geo.data_points?.length > 0 ? `${geo.data_points.length} data point${geo.data_points.length > 1 ? "s" : ""}` : "No data points"}
                </div>
              </div>
              {geo.value_proposition && (
                <p className="text-xs text-ink/40 mt-2 italic">"{geo.value_proposition}"</p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Tab: Broken Links ─────────────────────────────────────────────────────────

function BrokenLinksTab({ report }) {
  const { broken_links } = report;

  if (!broken_links?.length) {
    return (
      <div className="bg-teal-400 rounded-2xl p-10 text-center">
        <p className="text-white font-semibold text-lg">No broken links found</p>
        <p className="text-white/70 text-sm mt-1">All checked links returned a valid response.</p>
      </div>
    );
  }

  const internal = broken_links.filter(l => l.type === "internal");
  const external = broken_links.filter(l => l.type === "external");

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-fuchsia-500">{internal.length}</p>
          <p className="text-xs text-ink/40 mt-1">Internal broken links</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-amber-600">{external.length}</p>
          <p className="text-xs text-ink/40 mt-1">External broken links</p>
        </Card>
      </div>

      {[{ label: "Internal", items: internal, sev: "critical" }, { label: "External", items: external, sev: "warning" }].map(({ label, items, sev }) =>
        items.length > 0 && (
          <Card key={label} className="overflow-hidden">
            <div className="px-5 py-3 border-b border-beige-200">
              <h2 className="font-medium text-ink">{label} broken links</h2>
            </div>
            <div className="divide-y divide-beige-100">
              {items.map((link, i) => (
                <div key={i} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <a href={link.url} target="_blank" rel="noreferrer"
                        className="text-sm text-burgundy hover:underline truncate block">{link.url}</a>
                      <p className="text-xs text-ink/40 mt-0.5">
                        Found on: {link.found_on?.slice(0, 2).join(", ")}
                        {link.error && ` · ${link.error}`}
                      </p>
                    </div>
                    <span className={`flex-shrink-0 text-xs font-bold px-2 py-0.5 rounded-lg ${SEV_CFG[sev].bg} ${SEV_CFG[sev].text}`}>
                      {link.status || "ERR"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )
      )}
    </div>
  );
}

// ── Tab: Content Gaps ─────────────────────────────────────────────────────────

function ContentGapsTab({ report }) {
  const { content_gaps, ai } = report;

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <h2 className="font-medium text-ink mb-1">Missing Pages</h2>
        <p className="text-xs text-ink/40 mb-4">Pages that competitors have that this site doesn't.</p>
        <div className="space-y-3">
          {(content_gaps || []).map((gap, i) => (
            <div key={i} className="flex items-start gap-3 border border-beige-300 rounded-xl p-3">
              <div className="w-7 h-7 rounded-full bg-fuchsia-50 border border-fuchsia-100 text-fuchsia-500 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">!</div>
              <div>
                <p className="text-sm font-medium text-ink">{gap.label} <span className="text-ink/30 font-normal text-xs">{gap.url}</span></p>
                <p className="text-xs text-ink/50 mt-0.5">{gap.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {ai?.content_gaps?.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <AiBadge />
            <h2 className="font-medium text-ink">AI Content Gap Analysis</h2>
          </div>
          <div className="space-y-4">
            {ai.content_gaps.map((gap, i) => (
              <div key={i} className="border border-beige-300 rounded-xl p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="font-medium text-ink text-sm">{gap.missing_page}</p>
                  {gap.suggested_url && (
                    <span className="text-xs text-ink/40 bg-beige-100 px-2 py-0.5 rounded flex-shrink-0">{gap.suggested_url}</span>
                  )}
                </div>
                <p className="text-xs text-ink/60 mb-2">{gap.why_it_matters}</p>
                {gap.key_content && (
                  <div className="bg-beige-100 border border-beige-200 rounded-lg p-2.5">
                    <p className="text-xs text-ink/40 mb-1">Suggested content:</p>
                    <p className="text-xs text-ink/70">{gap.key_content}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Home({ report }) {
  const [activeTab, setActiveTab] = useState("Overview");

  if (!report || !report.snapshot_date) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-beige-100">
        <div className="text-center">
          <p className="font-display text-2xl text-burgundy mb-2">No audit data yet.</p>
          <code className="text-xs bg-beige-200 text-ink/60 px-3 py-1.5 rounded-lg">python _system/audit.py --baseline</code>
        </div>
      </div>
    );
  }

  const { scores, summary, snapshot_date, generated_at } = report;
  const overall = scores?.overall || 0;

  return (
    <div className="min-h-screen bg-beige-100">
      <header className="bg-white border-b border-beige-300 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-burgundy" />
            <div>
              <h1 className="text-sm font-medium text-ink">
                Oatly · Site Audit
              </h1>
              <p className="text-xs text-ink/40">
                oatly.com · {summary?.pages_audited || 0} pages ·{" "}
                {snapshot_date ? `Scraped ${snapshot_date}` : "—"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs text-ink/40">Overall score</p>
              <p className={`text-lg font-bold ${overall >= 80 ? "text-teal-400" : overall >= 60 ? "text-amber-600" : "text-fuchsia-500"}`}>
                {Math.round(overall)}<span className="text-xs font-normal text-ink/30">/100</span>
              </p>
            </div>
            <div className="flex gap-2 flex-wrap">
              {(summary?.seo_issues?.critical || 0) > 0 && (
                <span className="bg-fuchsia-50 text-fuchsia-500 px-2.5 py-1 rounded-full text-xs font-semibold">
                  {summary.seo_issues.critical} critical
                </span>
              )}
              {(summary?.broken_links_count || 0) > 0 && (
                <span className="bg-amber-50 text-amber-700 px-2.5 py-1 rounded-full text-xs font-semibold">
                  {summary.broken_links_count} broken links
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="max-w-5xl mx-auto px-6 flex gap-0 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 flex-shrink-0 transition-colors ${
                activeTab === tab
                  ? "border-burgundy text-burgundy"
                  : "border-transparent text-ink/40 hover:text-ink/70"
              }`}
            >
              {tab}
              {tab === "Broken Links" && (summary?.broken_links_count || 0) > 0 && (
                <span className="ml-1.5 bg-fuchsia-50 text-fuchsia-500 text-xs px-1.5 py-0.5 rounded-full">
                  {summary.broken_links_count}
                </span>
              )}
              {tab === "Content Gaps" && (summary?.content_gaps_count || 0) > 0 && (
                <span className="ml-1.5 bg-beige-200 text-ink/40 text-xs px-1.5 py-0.5 rounded-full">
                  {summary.content_gaps_count}
                </span>
              )}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {activeTab === "Overview"     && <OverviewTab     report={report} />}
        {activeTab === "SEO"          && <SEOTab          report={report} />}
        {activeTab === "GEO"          && <GEOTab          report={report} />}
        {activeTab === "Broken Links" && <BrokenLinksTab  report={report} />}
        {activeTab === "Content Gaps" && <ContentGapsTab  report={report} />}
      </main>

      <footer className="border-t border-beige-300 mt-12 py-6 text-center text-xs text-ink/30">
        Site data via Firecrawl · AI insights via Claude · Built with geo-site-audit
        {generated_at && ` · Generated ${new Date(generated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`}
      </footer>
    </div>
  );
}

export async function getStaticProps() {
  const dataPath = path.join(process.cwd(), "public", "data.json");
  if (!fs.existsSync(dataPath)) {
    return { props: { report: null } };
  }
  const raw = fs.readFileSync(dataPath, "utf-8");
  const report = JSON.parse(raw);
  return { props: { report } };
}
