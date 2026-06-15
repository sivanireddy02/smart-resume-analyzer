/**
 * components/KeywordAlignment.jsx
 *
 * Tab 1: Visual keyword diff between the resume and job description.
 * Matched keywords show in emerald; missing ones in rose.
 */

export default function KeywordAlignment({ matched = [], missing = [] }) {
  return (
    <div className="flex flex-col gap-8 animate-slide-up">

      {/* Summary row */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl bg-raised border border-emerald/20 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald/10 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p className="text-2xl font-display font-bold text-emerald">{matched.length}</p>
            <p className="text-xs text-muted">Matched keywords</p>
          </div>
        </div>

        <div className="rounded-xl bg-raised border border-rose/20 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-rose/10 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-rose" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <p className="text-2xl font-display font-bold text-rose">{missing.length}</p>
            <p className="text-xs text-muted">Missing keywords</p>
          </div>
        </div>
      </div>

      {/* Matched section */}
      {matched.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald" />
            <h3 className="text-sm font-medium text-ink">Keywords in your resume</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {matched.map((kw) => (
              <span key={kw} className="badge-matched">
                <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 8 8">
                  <circle cx="4" cy="4" r="3" />
                </svg>
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Missing section */}
      {missing.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1.5 h-1.5 rounded-full bg-rose" />
            <h3 className="text-sm font-medium text-ink">Keywords to add</h3>
            <span className="text-xs text-muted ml-1">(found in the job description)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {missing.map((kw) => (
              <span key={kw} className="badge-missing">
                <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 8 8" stroke="currentColor" strokeWidth={2}>
                  <path d="M4 1v6M1 4h6" strokeLinecap="round" />
                </svg>
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {matched.length === 0 && missing.length === 0 && (
        <div className="rounded-xl border border-border bg-raised p-8 text-center">
          <p className="text-muted text-sm">No keyword data available for this analysis.</p>
        </div>
      )}
    </div>
  )
}
