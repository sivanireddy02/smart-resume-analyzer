/**
 * components/RewriteTips.jsx
 *
 * Tab 3: Section-by-section rewrite suggestions.
 * Renders each tip with a clear "before/after" style if the text
 * contains a colon-delimited structure, otherwise as a plain card.
 */

function TipCard({ tip, index }) {
  // Try to parse "Section: suggestion" pattern for enhanced display
  const colonIdx = tip.indexOf(':')
  const hasLabel = colonIdx > 0 && colonIdx < 40

  const label   = hasLabel ? tip.slice(0, colonIdx).trim() : null
  const content = hasLabel ? tip.slice(colonIdx + 1).trim() : tip

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden
                    hover:border-cyan/20 transition-colors duration-200">
      <div className="px-4 py-3 bg-raised border-b border-border flex items-center gap-3">
        <span className="w-6 h-6 rounded-md bg-cyan/10 text-cyan text-xs font-mono font-bold
                         flex items-center justify-center flex-shrink-0">
          {index + 1}
        </span>
        {label ? (
          <span className="text-sm font-medium text-ink">{label}</span>
        ) : (
          <span className="text-sm font-medium text-cyan">Rewrite Tip</span>
        )}
      </div>

      <div className="p-4">
        <p className="text-sm text-ink/85 leading-relaxed">{content}</p>
      </div>
    </div>
  )
}

export default function RewriteTips({ tips = [] }) {
  if (tips.length === 0) {
    return (
      <div className="animate-slide-up rounded-xl border border-border bg-raised p-10 text-center flex flex-col items-center gap-3">
        <svg className="w-10 h-10 text-ghost" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
        </svg>
        <p className="text-muted text-sm">No rewrite tips were generated.</p>
        <p className="text-ghost text-xs">This usually means your resume is already well-structured.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 animate-slide-up">
      <p className="text-muted text-xs flex items-center gap-2">
        <svg className="w-3.5 h-3.5 text-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Specific wording and structural changes recommended by the AI reviewer.
      </p>

      <div className="flex flex-col gap-3">
        {tips.map((tip, i) => (
          <TipCard key={i} tip={tip} index={i} />
        ))}
      </div>
    </div>
  )
}
