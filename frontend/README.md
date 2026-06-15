# Smart Resume Analyzer — Frontend

React + Vite + Tailwind CSS frontend for the Smart Resume Analyzer.

## Stack

| Layer       | Technology                               |
|-------------|------------------------------------------|
| Framework   | React 18 + Vite 5                        |
| Styling     | Tailwind CSS 3 (custom design tokens)    |
| Charts      | Chart.js 4 + react-chartjs-2             |
| HTTP        | axios                                    |
| File upload | react-dropzone                           |
| Fonts       | Space Grotesk · Inter · JetBrains Mono   |

---

## Quick Start

### 1 — Prerequisites

- Node.js ≥ 18
- The FastAPI backend running at `http://localhost:8000`

### 2 — Install dependencies

```bash
npm install
```

### 3 — Environment (optional)

Copy the example env file and set your API base URL if needed:

```bash
cp .env.example .env
```

`.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

If `VITE_API_BASE_URL` is not set, the app defaults to `http://localhost:8000`.

### 4 — Run development server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### 5 — Build for production

```bash
npm run build
npm run preview
```

---

## Project Structure

```
src/
├── main.jsx                  # React entry point
├── App.jsx                   # Root component + page layout
├── styles/
│   └── globals.css           # Tailwind base + custom component classes
├── hooks/
│   └── useAnalysis.js        # All state management (file, loading, result, error)
├── utils/
│   ├── api.js                # Axios wrapper — all backend calls live here
│   └── chartConfig.js        # Chart.js registration + config factories
└── components/
    ├── FileDropZone.jsx       # Drag-and-drop PDF/DOCX upload
    ├── LoadingOverlay.jsx     # Terminal-style scan animation
    ├── ScoreRing.jsx          # Animated doughnut score chart
    ├── KeywordAlignment.jsx   # Matched / missing keyword badges (Tab 1)
    ├── AIFeedback.jsx         # Accordion: strengths, gaps, suggestions (Tab 2)
    ├── RewriteTips.jsx        # Section-by-section rewrite cards (Tab 3)
    └── AnalysisDashboard.jsx  # Full results view (composes all above)
```

---

## API Contract

The frontend sends a `multipart/form-data` POST to `/api/resume/analyze`:

| Field           | Type   | Description                         |
|-----------------|--------|-------------------------------------|
| `resume_file`   | File   | PDF or DOCX resume binary           |
| `job_description`| string | Raw job-description text (≥ 50 chars)|

Expected response shape (matches `AnalysisResponse` Pydantic model):

```json
{
  "analysis_id":       "uuid",
  "resume_id":         "uuid",
  "status":            "complete",
  "similarity_score":  0.82,
  "overall_score":     78.4,
  "section_scores":    { "skills": 0.85, "experience": 0.72, ... },
  "matched_keywords":  ["python", "fastapi", ...],
  "missing_keywords":  ["kubernetes", "terraform", ...],
  "detected_entities": { "ORG": ["Google"], "DATE": ["2022"] },
  "detected_skills":   ["python", "react", ...],
  "strengths":         ["Strong Python background…"],
  "gaps":              ["Missing cloud infrastructure experience…"],
  "suggestions":       ["Add quantified achievements…"],
  "rewrite_tips":      ["Experience: Replace duties with outcomes…"],
  "model_used":        "all-MiniLM-L6-v2",
  "processing_time_ms": 8420
}
```

---

## Design Tokens

| Token    | Value     | Used for                    |
|----------|-----------|-----------------------------|
| `void`   | `#0A0F1E` | Page background             |
| `surface`| `#111827` | Card backgrounds            |
| `raised` | `#1A2236` | Elevated / hover surfaces   |
| `cyan`   | `#22D3EE` | Primary accent, links, CTA  |
| `emerald`| `#10B981` | High scores, matched KWs    |
| `amber`  | `#F59E0B` | Mid scores, warnings        |
| `rose`   | `#F43F5E` | Low scores, missing KWs     |
