/**
 * App.jsx — Root component for Smart Resume Analyzer
 *
 * Page structure:
 *   1. Fixed nav header
 *   2. Hero section
 *   3. Input zone (file upload + job description)
 *   4. Analyze CTA
 *   5. Loading overlay (conditional)
 *   6. Results dashboard (conditional)
 *   7. Footer
 */

import "./utils/chartConfig";   // registers Chart.js elements globally (side-effect import)
import { useRef } from 'react'
import { useDropzone }          from 'react-dropzone'
import { useAnalysis }          from './hooks/useAnalysis'
import FileDropZone             from './components/FileDropZone'
import LoadingOverlay           from './components/LoadingOverlay'
import AnalysisDashboard        from './components/AnalysisDashboard'

// ─── Error alert ─────────────────────────────────────────────────────────────

function ErrorAlert({ message, onDismiss }) {
  return (
    <div className="rounded-xl border border-rose/30 bg-rose/10 px-4 py-3
                    flex items-start gap-3 animate-fade-in">
      <svg className="w-4 h-4 text-rose flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-rose font-medium">Analysis failed</p>
        <p className="text-xs text-rose/80 mt-0.5 break-words">{message}</p>
      </div>
      <button onClick={onDismiss} className="text-rose/60 hover:text-rose transition-colors flex-shrink-0">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

// ─── Navbar ───────────────────────────────────────────────────────────────────

function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-void/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {/* Logo mark */}
          <div className="w-7 h-7 rounded-md bg-cyan/10 border border-cyan/30
                          flex items-center justify-center">
            <svg className="w-4 h-4 text-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="font-display font-semibold text-sm text-ink tracking-tight">
            Resume Analyzer
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden sm:block text-xs font-mono text-ghost px-2.5 py-1
                           border border-border rounded-md bg-raised">
            v1.0.0
          </span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted hover:text-cyan transition-colors duration-150
                       flex items-center gap-1.5"
          >
            API Docs
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  )
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <div className="text-center flex flex-col items-center gap-4 pt-16 pb-10">
      {/* Eyebrow tag */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                      border border-cyan/20 bg-cyan/5 text-cyan text-xs font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan animate-pulse-slow" />
        AI-Powered · Semantic Matching · LLM Feedback
      </div>

      <h1 className="font-display font-bold text-4xl sm:text-5xl text-ink leading-tight tracking-tight max-w-xl">
        Smart Resume{' '}
        <span className="text-transparent bg-clip-text"
              style={{ backgroundImage: 'linear-gradient(135deg, #22D3EE 0%, #10B981 100%)' }}>
          Analyzer
        </span>
      </h1>

      <p className="text-muted text-base max-w-md leading-relaxed">
        Upload your resume and paste a job description. Get an instant semantic match
        score, keyword gap analysis, and AI-written improvement suggestions.
      </p>
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const resultsRef = useRef(null)

  const {
    file, jobDescription, loading, uploadProgress,
    currentPhase, result, error,
    handleFileSelect, handleRemoveFile,
    setJobDescription, handleSubmit, handleReset,
  } = useAnalysis()

  const canSubmit = file && jobDescription.trim().length >= 50 && !loading

  return (
    <div className="min-h-screen bg-void bg-grid-pattern bg-grid">
      <Navbar />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 pb-24">
        <Hero />

        {/* ── Input zone ─────────────────────────────────────────────────────── */}
        {!result && (
          <div className="flex flex-col gap-5">
            {/* Step label */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs font-mono text-muted uppercase tracking-widest px-3">
                Input
              </span>
              <div className="flex-1 h-px bg-border" />
            </div>

            {/* Split-screen input card */}
            <div className="rounded-2xl border border-border bg-surface shadow-card p-6
                            grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Left: File upload */}
              <FileDropZone
                file={file}
                onFileSelect={handleFileSelect}
                onRemove={handleRemoveFile}
                disabled={loading}
              />

              {/* Divider on desktop */}
              <div className="hidden md:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-px h-3/4 bg-border" />

              {/* Right: Job description */}
              <div className="flex flex-col gap-3">
                <label htmlFor="jd" className="text-xs font-mono text-muted uppercase tracking-widest">
                  Job Description
                </label>
                <div className="flex-1 relative">
                  <textarea
                    id="jd"
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                    disabled={loading}
                    placeholder="Paste the full job description here…&#10;&#10;Include the role summary, required skills,&#10;qualifications, and responsibilities."
                    className="w-full h-full min-h-[240px] resize-none rounded-xl
                               bg-raised border border-border text-sm text-ink
                               placeholder:text-ghost font-body leading-relaxed
                               p-4 input-focus disabled:opacity-50
                               transition-colors duration-200"
                    style={{ fieldSizing: 'content' }}
                  />
                  {/* Char counter */}
                  <div className="absolute bottom-3 right-3 flex items-center gap-2">
                    {jobDescription.length > 0 && jobDescription.length < 50 && (
                      <span className="text-[10px] font-mono text-amber">
                        {50 - jobDescription.length} more chars needed
                      </span>
                    )}
                    <span className={`text-[10px] font-mono ${
                      jobDescription.length >= 50 ? 'text-emerald' : 'text-ghost'
                    }`}>
                      {jobDescription.length.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Error alert */}
            {error && !loading && (
              <ErrorAlert
                message={error}
                onDismiss={() => handleReset()}
              />
            )}

            {/* CTA button */}
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className={`w-full rounded-xl py-4 text-sm font-display font-semibold
                          flex items-center justify-center gap-2.5
                          transition-all duration-200 relative overflow-hidden
                          ${canSubmit
                            ? 'bg-cyan text-void hover:brightness-110 shadow-glow-cyan cursor-pointer'
                            : 'bg-raised text-ghost border border-border cursor-not-allowed'
                          }`}
            >
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Analyzing…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                  Analyze Resume
                </>
              )}
            </button>

            {/* Requirements hint */}
            {!file || jobDescription.length < 50 ? (
              <p className="text-center text-xs text-ghost">
                {!file
                  ? 'Upload a PDF or DOCX resume to continue.'
                  : `Add ${Math.max(0, 50 - jobDescription.length)} more characters to the job description.`}
              </p>
            ) : null}
          </div>
        )}

        {/* ── Loading overlay ─────────────────────────────────────────────────── */}
        {loading && (
          <div className="mt-6">
            <LoadingOverlay currentPhase={currentPhase} uploadProgress={uploadProgress} />
          </div>
        )}

        {/* ── Results ─────────────────────────────────────────────────────────── */}
        {result && !loading && (
          <div className="mt-2" ref={resultsRef}>
            <AnalysisDashboard result={result} onReset={handleReset} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-6">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row
                        items-center justify-between gap-2">
          <p className="text-xs font-mono text-ghost">
            Smart Resume Analyzer · FastAPI + React · all-MiniLM-L6-v2
          </p>
          <a
            href="http://localhost:8000/health"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono text-ghost hover:text-emerald transition-colors
                       flex items-center gap-1.5"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald animate-pulse-slow" />
            Backend health check
          </a>
        </div>
      </footer>
    </div>
  )
}
