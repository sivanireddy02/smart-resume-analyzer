/**
 * components/AnalysisDashboard.jsx
 *
 * The results dashboard revealed after analysis completes.
 * Composed of:
 *   - Hero metrics strip (score ring, radar, processing time)
 *   - Three-tab detailed view (Keywords | AI Feedback | Rewrite Tips)
 */

import { useState, useRef, useEffect } from 'react'
import { Radar, Bar } from 'react-chartjs-2'
import ScoreRing          from './ScoreRing'
import KeywordAlignment   from './KeywordAlignment'
import AIFeedback         from './AIFeedback'
import RewriteTips        from './RewriteTips'
import { buildRadarConfig, buildBarConfig } from '../utils/chartConfig'

const TABS = [
  { id: 'keywords', label: 'Keyword Alignment' },
  { id: 'feedback', label: 'AI Feedback'       },
  { id: 'rewrite',  label: 'Rewrite Tips'      },
]

function MetricPill({ label, value, colour }) {
  return (
    <div className="flex flex-col items-center gap-1 px-5 py-3 rounded-xl bg-raised border border-border min-w-[90px]">
      <span className="text-xl font-display font-bold tabular-nums" style={{ color: colour }}>
        {value}
      </span>
      <span className="text-[10px] font-mono text-muted uppercase tracking-wider text-center leading-tight">
        {label}
      </span>
    </div>
  )
}

export default function AnalysisDashboard({ result, onReset }) {
  const [activeTab,  setActiveTab]  = useState('keywords')
  const dashboardRef = useRef(null)

  // Scroll into view on mount
  useEffect(() => {
    dashboardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const radarConfig = buildRadarConfig(result.section_scores || {})
  const barConfig   = buildBarConfig(result.section_scores || {})

  const processingSeconds = result.processing_time_ms
    ? (result.processing_time_ms / 1000).toFixed(1)
    : null

  return (
    <div ref={dashboardRef} className="flex flex-col gap-6 animate-slide-up">

      {/* ── Header strip ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-display font-semibold text-ink">Analysis Results</h2>
          {result.analysis_id && (
            <p className="text-xs font-mono text-ghost mt-0.5">
              ID: {result.analysis_id.slice(0, 8)}…
            </p>
          )}
        </div>
        <button
          onClick={onReset}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium
                     text-muted border border-border hover:border-cyan/30 hover:text-cyan
                     transition-all duration-150"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          New analysis
        </button>
      </div>

      {/* ── Hero metrics card ───────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface shadow-card p-6
                      grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">

        {/* Score ring */}
        <div className="flex flex-col items-center gap-2">
          <p className="text-xs font-mono text-muted uppercase tracking-widest mb-2">
            Overall Match Score
          </p>
          <ScoreRing score={result.overall_score ?? 0} />
        </div>

        {/* Radar chart */}
        <div className="flex flex-col items-center">
          <p className="text-xs font-mono text-muted uppercase tracking-widest mb-4">
            Section Breakdown
          </p>
          <div className="w-full max-w-[260px]">
            <Radar data={radarConfig.data} options={radarConfig.options} />
          </div>
        </div>

        {/* Side metrics */}
        <div className="flex flex-col items-center gap-4">
          <p className="text-xs font-mono text-muted uppercase tracking-widest">
            Quick Stats
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <MetricPill
              label="Similarity"
              value={`${Math.round((result.similarity_score ?? 0) * 100)}%`}
              colour="#22D3EE"
            />
            <MetricPill
              label="Matched KW"
              value={result.matched_keywords?.length ?? 0}
              colour="#10B981"
            />
            <MetricPill
              label="Missing KW"
              value={result.missing_keywords?.length ?? 0}
              colour="#F43F5E"
            />
            {processingSeconds && (
              <MetricPill
                label="Processed in"
                value={`${processingSeconds}s`}
                colour="#64748B"
              />
            )}
          </div>

          {/* Detected skills */}
          {result.detected_skills?.length > 0 && (
            <div className="w-full">
              <p className="text-[10px] font-mono text-muted uppercase tracking-wider mb-2 text-center">
                Detected Skills
              </p>
              <div className="flex flex-wrap justify-center gap-1.5 max-h-24 overflow-y-auto">
                {result.detected_skills.slice(0, 12).map((s) => (
                  <span key={s}
                    className="px-2 py-0.5 rounded text-[10px] font-mono
                               bg-ghost/20 text-muted border border-border">
                    {s}
                  </span>
                ))}
                {result.detected_skills.length > 12 && (
                  <span className="text-[10px] text-ghost font-mono">
                    +{result.detected_skills.length - 12} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Section bar chart ───────────────────────────────────────────────── */}
      {result.section_scores && (
        <div className="rounded-2xl border border-border bg-surface shadow-card p-6">
          <p className="text-xs font-mono text-muted uppercase tracking-widest mb-5">
            Score by Dimension
          </p>
          <div style={{ height: '160px' }}>
            <Bar data={barConfig.data} options={barConfig.options} />
          </div>
        </div>
      )}

      {/* ── Tabs ────────────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface shadow-card overflow-hidden">

        {/* Tab strip */}
        <div className="flex border-b border-border">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-4 py-3.5 text-sm font-medium transition-all duration-150
                          border-b-2 -mb-px
                          ${activeTab === tab.id
                            ? 'text-cyan border-cyan bg-cyan/5'
                            : 'text-muted border-transparent hover:text-ink hover:border-border'
                          }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="p-6">
          {activeTab === 'keywords' && (
            <KeywordAlignment
              matched={result.matched_keywords ?? []}
              missing={result.missing_keywords ?? []}
            />
          )}
          {activeTab === 'feedback' && (
            <AIFeedback
              strengths={result.strengths ?? []}
              gaps={result.gaps ?? []}
              suggestions={result.suggestions ?? []}
            />
          )}
          {activeTab === 'rewrite' && (
            <RewriteTips tips={result.rewrite_tips ?? []} />
          )}
        </div>
      </div>

      {/* ── Model footnote ──────────────────────────────────────────────────── */}
      {result.model_used && (
        <p className="text-center text-xs font-mono text-ghost">
          Embeddings: {result.model_used}
          {result.llm_model_used && ` · LLM: ${result.llm_model_used}`}
        </p>
      )}
    </div>
  )
}
