/**
 * components/FileDropZone.jsx
 *
 * Drag-and-drop file upload zone for PDF and DOCX resumes.
 * Uses react-dropzone for drag state and file validation.
 */

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/msword': ['.doc'],
}
const MAX_SIZE = 10 * 1024 * 1024   // 10 MB

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileIcon({ mime }) {
  const isPdf = mime === 'application/pdf'
  return (
    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-mono font-bold
      ${isPdf ? 'bg-rose/10 text-rose border border-rose/20' : 'bg-cyan/10 text-cyan border border-cyan/20'}`}>
      {isPdf ? 'PDF' : 'DOC'}
    </div>
  )
}

export default function FileDropZone({ file, onFileSelect, onRemove, disabled }) {
  const onDrop = useCallback(
    (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) return   // error handled by dropzone state below
      if (acceptedFiles.length > 0) onFileSelect(acceptedFiles[0])
    },
    [onFileSelect]
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject, fileRejections } =
    useDropzone({
      onDrop,
      accept:    ACCEPTED_TYPES,
      maxFiles:  1,
      maxSize:   MAX_SIZE,
      disabled,
      multiple:  false,
    })

  const rejectionMessage = fileRejections[0]?.errors[0]?.message

  // ── Uploaded state ──────────────────────────────────────────────────────────
  if (file) {
    return (
      <div className="flex-1 flex flex-col gap-3">
        <label className="text-xs font-mono text-muted uppercase tracking-widest">
          Resume File
        </label>
        <div className="flex-1 rounded-xl border border-emerald/30 bg-emerald-dim/20 p-5
                        flex flex-col items-center justify-center gap-4 min-h-[200px]
                        shadow-glow-emerald animate-fade-in">
          {/* File card */}
          <div className="w-full max-w-xs bg-raised rounded-lg p-4 flex items-center gap-3 border border-border">
            <FileIcon mime={file.type} />
            <div className="flex-1 min-w-0">
              <p className="text-ink text-sm font-medium truncate">{file.name}</p>
              <p className="text-muted text-xs mt-0.5">{formatBytes(file.size)}</p>
            </div>
            <div className="w-5 h-5 rounded-full bg-emerald/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-3 h-3 text-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <p className="text-emerald text-xs font-mono">File ready for analysis</p>

          <button
            onClick={onRemove}
            disabled={disabled}
            className="text-xs text-muted hover:text-rose transition-colors duration-150
                       flex items-center gap-1.5 disabled:opacity-40"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Remove file
          </button>
        </div>
      </div>
    )
  }

  // ── Drop zone ────────────────────────────────────────────────────────────────
  const borderClass = isDragReject
    ? 'border-rose/50 bg-rose/5'
    : isDragActive
    ? 'border-cyan/60 bg-cyan/5 shadow-glow-cyan'
    : 'border-border hover:border-cyan/30 hover:bg-raised/50'

  return (
    <div className="flex-1 flex flex-col gap-3">
      <label className="text-xs font-mono text-muted uppercase tracking-widest">
        Resume File
      </label>
      <div
        {...getRootProps()}
        className={`flex-1 rounded-xl border-2 border-dashed cursor-pointer
                    flex flex-col items-center justify-center gap-4 p-8 min-h-[200px]
                    transition-all duration-200 outline-none ${borderClass}
                    ${disabled ? 'pointer-events-none opacity-50' : ''}`}
      >
        <input {...getInputProps()} />

        {/* Upload icon */}
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors duration-200
          ${isDragActive ? 'bg-cyan/15' : 'bg-raised'} border border-border`}>
          {isDragReject ? (
            <svg className="w-7 h-7 text-rose" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          ) : (
            <svg className={`w-7 h-7 transition-colors ${isDragActive ? 'text-cyan' : 'text-muted'}`}
                 fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          )}
        </div>

        {isDragActive && !isDragReject ? (
          <p className="text-cyan font-medium text-sm">Drop it here</p>
        ) : isDragReject ? (
          <p className="text-rose font-medium text-sm">File type not supported</p>
        ) : (
          <div className="text-center">
            <p className="text-ink text-sm font-medium">
              Drag your resume here
            </p>
            <p className="text-muted text-xs mt-1">
              or{' '}
              <span className="text-cyan underline underline-offset-2">click to browse</span>
            </p>
          </div>
        )}

        <div className="flex items-center gap-2">
          {['PDF', 'DOCX'].map((fmt) => (
            <span key={fmt} className="px-2 py-0.5 rounded text-[10px] font-mono
                                       bg-ghost/30 text-muted border border-border">
              {fmt}
            </span>
          ))}
          <span className="text-ghost text-[10px] font-mono">up to 10 MB</span>
        </div>
      </div>

      {rejectionMessage && (
        <p className="text-xs text-rose flex items-center gap-1.5 mt-1">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {rejectionMessage}
        </p>
      )}
    </div>
  )
}
