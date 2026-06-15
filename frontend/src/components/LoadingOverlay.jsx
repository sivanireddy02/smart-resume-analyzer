/**
 * components/LoadingOverlay.jsx
 *
 * Terminal-style scan animation shown during analysis.
 * The signature UI element: mimics a CLI tool running a file scan,
 * reinforcing the developer-tool identity of the product.
 */

const PHASES = [
  { id: 'upload', label: 'Uploading file…'            },
  { id: 'parse',  label: 'Extracting text & entities…' },
  { id: 'embed',  label: 'Building semantic vectors…'  },
  { id: 'match',  label: 'Calculating match score…'    },
  { id: 'llm',    label: 'Generating AI feedback…'     },
  { id: 'done',   label: 'Analysis complete!'           },
]

function PhaseDot({ phase, currentPhase }) {
  const phases   = PHASES.map((p) => p.id)
  const curIdx   = phases.indexOf(currentPhase?.id)
  const phaseIdx = phases.indexOf(phase.id)
  const isDone   = phase.id === 'done'
  const isActive = currentPhase?.id === phase.id

  let state = 'pending'
  if (isDone && isActive)          state = 'done'
  else if (isActive)               state = 'active'
  else if (phaseIdx < curIdx)      state = 'complete'

  return (
    <div className={`flex items-center gap-2.5 transition-all duration-300
      ${state === 'pending' ? 'opacity-30' : 'opacity-100'}`}>
      <div className={`w-2 h-2 rounded-full flex-shrink-0 transition-all duration-300 ${
        state === 'done'     ? 'bg-emerald shadow-[0_0_8px_rgba(16,185,129,0.8)]' :
        state === 'complete' ? 'bg-emerald/60' :
        state === 'active'   ? 'bg-cyan animate-pulse-slow shadow-[0_0_8px_rgba(34,211,238,0.8)]' :
                               'bg-ghost'
      }`} />
      <span className={`text-xs font-mono transition-colors duration-300 ${
        state === 'done'     ? 'text-emerald' :
        state === 'complete' ? 'text-emerald/70' :
        state === 'active'   ? 'text-cyan' :
                               'text-ghost'
      }`}>
        {state === 'complete' ? '✓ ' : ''}{phase.label}
      </span>
    </div>
  )
}

export default function LoadingOverlay({ currentPhase, uploadProgress }) {
  return (
    <div className="w-full rounded-2xl border border-border bg-surface shadow-card
                    p-8 flex flex-col items-center gap-8 animate-fade-in">

      {/* Terminal window chrome */}
      <div className="w-full max-w-md">
        <div className="rounded-t-lg bg-raised border border-border px-4 py-2.5 flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-rose/60" />
          <div className="w-3 h-3 rounded-full bg-amber/60" />
          <div className="w-3 h-3 rounded-full bg-emerald/60" />
          <span className="ml-3 text-xs font-mono text-muted">resume-analyzer — analyzing</span>
        </div>

        {/* Terminal body with scan line */}
        <div className="scan-line rounded-b-lg bg-void border-x border-b border-border
                        p-5 min-h-[180px] flex flex-col gap-2.5">
          <p className="text-cyan text-xs font-mono mb-2">
            $ resume-analyzer run --model all-MiniLM-L6-v2
          </p>
          {PHASES.map((phase) => (
            <PhaseDot key={phase.id} phase={phase} currentPhase={currentPhase} />
          ))}

          {/* Blinking cursor */}
          <div className="flex items-center gap-1 mt-1">
            <span className="text-muted text-xs font-mono">›</span>
            <div className="w-2 h-3.5 bg-cyan/80 animate-pulse" />
          </div>
        </div>
      </div>

      {/* Upload progress bar (shown briefly during upload phase) */}
      {uploadProgress > 0 && uploadProgress < 100 && (
        <div className="w-full max-w-md">
          <div className="flex justify-between text-xs font-mono text-muted mb-1.5">
            <span>Upload progress</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="h-1 w-full bg-raised rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan rounded-full transition-all duration-300 ease-out"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Status message */}
      <p className="text-muted text-sm text-center max-w-xs leading-relaxed">
        {currentPhase?.id === 'llm'
          ? 'Waiting for AI feedback — this can take up to 30 seconds.'
          : 'Processing your resume. Do not close this tab.'}
      </p>
    </div>
  )
}
