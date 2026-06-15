/**
 * components/AIFeedback.jsx
 *
 * Tab 2: Accordion-based AI qualitative feedback.
 * Three sections: Strengths, Critical Gaps, and Actionable Suggestions.
 */

import { useState } from 'react'

function AccordionSection({ title, items = [], variant = 'neutral', defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)

  const variantStyles = {
    emerald: {
      icon:   'text-emerald',
      dot:    'bg-emerald',
      border: 'border-emerald/20',
      bg:     'bg-emerald/5',
      bullet: 'bg-emerald/20 text-emerald',
      chevron:'text-emerald/60',
    },
    rose: {
      icon:   'text-rose',
      dot:    'bg-rose',
      border: 'border-rose/20',
      bg:     'bg-rose/5',
      bullet: 'bg-rose/20 text-rose',
      chevron:'text-rose/60',
    },
    amber: {
      icon:   'text-amber',
      dot:    'bg-amber',
      border: 'border-amber/20',
      bg:     'bg-amber/5',
      bullet: 'bg-amber/20 text-amber',
      chevron:'text-amber/60',
    },
    neutral: {
      icon:   'text-cyan',
      dot:    'bg-cyan',
      border: 'border-border',
      bg:     'bg-raised',
      bullet: 'bg-cyan/20 text-cyan',
      chevron:'text-muted',
    },
  }

  const s = variantStyles[variant] || variantStyles.neutral
  const icons = {
    emerald: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    rose: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    amber: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    neutral: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  }

  return (
    <div className={`rounded-xl border ${s.border} overflow-hidden transition-all duration-200`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between p-4 text-left
                    ${open ? s.bg : 'bg-surface hover:bg-raised'}
                    transition-colors duration-150`}
      >
        <div className="flex items-center gap-3">
          <span className={s.icon}>{icons[variant]}</span>
          <span className="font-medium text-ink text-sm">{title}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${s.bullet}`}>
            {items.length}
          </span>
        </div>
        <svg
          className={`w-4 h-4 ${s.chevron} transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className={`${s.bg} border-t ${s.border} p-4`}>
          {items.length === 0 ? (
            <p className="text-muted text-sm italic">No items in this category.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {items.map((item, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className={`w-5 h-5 rounded-full text-[10px] font-mono font-bold flex-shrink-0
                                    flex items-center justify-center mt-0.5 ${s.bullet}`}>
                    {i + 1}
                  </span>
                  <p className="text-sm text-ink/90 leading-relaxed">{item}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default function AIFeedback({ strengths = [], gaps = [], suggestions = [] }) {
  return (
    <div className="flex flex-col gap-4 animate-slide-up">
      <AccordionSection
        title="Strengths"
        items={strengths}
        variant="emerald"
        defaultOpen={true}
      />
      <AccordionSection
        title="Critical Gaps"
        items={gaps}
        variant="rose"
        defaultOpen={true}
      />
      <AccordionSection
        title="Actionable Suggestions"
        items={suggestions}
        variant="amber"
        defaultOpen={false}
      />
    </div>
  )
}
