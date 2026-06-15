/**
 * utils/api.js
 *
 * Thin axios wrapper for the Smart Resume Analyzer backend.
 * All backend communication funnels through this module so base URL,
 * headers, and error normalisation live in exactly one place.
 */

import axios from 'axios'

// ─── Axios instance ──────────────────────────────────────────────────────────

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 120_000,   // 2-min timeout — LLM calls can be slow
})

// Response interceptor — normalises error shape for consumers
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred.'
    return Promise.reject(new Error(message))
  }
)

// ─── API calls ───────────────────────────────────────────────────────────────

/**
 * POST /api/resume/analyze
 *
 * Sends the resume file and job description as multipart/form-data.
 *
 * @param {File}     resumeFile      - The uploaded PDF or DOCX file object
 * @param {string}   jobDescription  - Raw job-description text
 * @param {Function} onUploadProgress - Optional upload progress callback (0–100)
 * @returns {Promise<AnalysisResult>} - The structured analysis response
 */
export async function analyzeResume(resumeFile, jobDescription, onUploadProgress) {
  const formData = new FormData()
  formData.append('resume_file', resumeFile)           // matches FastAPI param name
  formData.append('job_description', jobDescription)

  const response = await apiClient.post('/api/resume/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onUploadProgress
      ? (evt) => {
          const pct = evt.total ? Math.round((evt.loaded / evt.total) * 100) : 0
          onUploadProgress(pct)
        }
      : undefined,
  })

  return response.data
}

export default apiClient
