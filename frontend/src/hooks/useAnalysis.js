/**
 * hooks/useAnalysis.js
 *
 * Central state machine for the analysis pipeline.
 * Manages: file selection, upload progress, loading phases,
 * result storage, and error handling.
 */

import { useState, useCallback, useRef } from 'react'
import { analyzeResume } from '../utils/api'

// Pipeline phases — drives UI messaging during loading
const PHASES = [
  { id: 'upload',    label: 'Uploading file…',            duration: 800  },
  { id: 'parse',     label: 'Extracting text & entities…', duration: 2500 },
  { id: 'embed',     label: 'Building semantic vectors…',  duration: 2000 },
  { id: 'match',     label: 'Calculating match score…',    duration: 1500 },
  { id: 'llm',       label: 'Generating AI feedback…',     duration: 0    }, // waits for real response
]

export function useAnalysis() {
  const [file,           setFile]           = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [loading,        setLoading]        = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [currentPhase,   setCurrentPhase]   = useState(null)
  const [result,         setResult]         = useState(null)
  const [error,          setError]          = useState(null)

  const phaseTimers = useRef([])

  // Clear previous timers to avoid memory leaks on re-run
  const clearTimers = () => {
    phaseTimers.current.forEach(clearTimeout)
    phaseTimers.current = []
  }

  // Simulate pipeline phase progression in the UI
  const startPhaseAnimation = useCallback(() => {
    let elapsed = 0
    PHASES.slice(0, -1).forEach((phase, i) => {
      const timer = setTimeout(() => {
        setCurrentPhase(phase)
      }, elapsed)
      phaseTimers.current.push(timer)
      elapsed += phase.duration
    })
    // Last phase is activated when the real request is still pending
    const lastTimer = setTimeout(() => setCurrentPhase(PHASES[PHASES.length - 1]), elapsed)
    phaseTimers.current.push(lastTimer)
  }, [])

  const handleFileSelect = useCallback((acceptedFile) => {
    if (!acceptedFile) return
    setFile(acceptedFile)
    setError(null)
    setResult(null)
  }, [])

  const handleRemoveFile = useCallback(() => {
    setFile(null)
    setResult(null)
    setError(null)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!file || !jobDescription.trim()) {
      setError(!file ? 'Please upload a resume file.' : 'Please paste a job description.')
      return
    }
    if (jobDescription.trim().length < 50) {
      setError('Job description must be at least 50 characters.')
      return
    }

    clearTimers()
    setLoading(true)
    setError(null)
    setResult(null)
    setUploadProgress(0)
    startPhaseAnimation()

    try {
      const data = await analyzeResume(
        file,
        jobDescription,
        (pct) => setUploadProgress(pct),
      )
      clearTimers()
      setCurrentPhase({ id: 'done', label: 'Analysis complete!' })
      // Small delay so the "complete" message is briefly visible
      setTimeout(() => {
        setResult(data)
        setLoading(false)
        setCurrentPhase(null)
      }, 600)
    } catch (err) {
      clearTimers()
      setError(err.message || 'Analysis failed. Is the backend running?')
      setLoading(false)
      setCurrentPhase(null)
    }
  }, [file, jobDescription, startPhaseAnimation])

  const handleReset = useCallback(() => {
    clearTimers()
    setFile(null)
    setJobDescription('')
    setResult(null)
    setError(null)
    setLoading(false)
    setCurrentPhase(null)
    setUploadProgress(0)
  }, [])

  return {
    // State
    file,
    jobDescription,
    loading,
    uploadProgress,
    currentPhase,
    result,
    error,
    // Actions
    handleFileSelect,
    handleRemoveFile,
    setJobDescription,
    handleSubmit,
    handleReset,
  }
}
