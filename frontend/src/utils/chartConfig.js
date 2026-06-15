/**
 * utils/chartConfig.js
 *
 * Centralised Chart.js registration and configuration factories.
 * Import this once at app root so all chart components share the same registry.
 */

import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js'

// Register all elements used across the app
ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  CategoryScale,
  LinearScale,
  BarElement,
)

// ─── Global chart defaults ───────────────────────────────────────────────────

ChartJS.defaults.color          = '#64748B'   // muted
ChartJS.defaults.borderColor    = '#1F2D45'   // border
ChartJS.defaults.font.family    = '"Inter", system-ui, sans-serif'
ChartJS.defaults.font.size      = 12

// ─── Score colour helper ─────────────────────────────────────────────────────

/**
 * Returns the appropriate colour tokens for a 0–100 overall score.
 * @param {number} score
 * @returns {{ primary: string, secondary: string, label: string }}
 */
export function scoreColour(score) {
  if (score >= 75) return { primary: '#10B981', secondary: '#065F46', label: 'Strong match' }
  if (score >= 50) return { primary: '#F59E0B', secondary: '#78350F', label: 'Partial match' }
  return              { primary: '#F43F5E', secondary: '#881337', label: 'Needs work'   }
}

// ─── Doughnut chart config factory ───────────────────────────────────────────

/**
 * Builds a Chart.js Doughnut config for the overall match score ring.
 * @param {number} score - 0 to 100
 */
export function buildScoreDoughnutConfig(score) {
  const { primary, secondary } = scoreColour(score)
  const remainder = 100 - score

  return {
    data: {
      datasets: [
        {
          data: [score, remainder],
          backgroundColor: [primary, secondary],
          borderColor:     [primary, secondary],
          borderWidth:     0,
          circumference:   280,
          rotation:        -140,
          borderRadius:    6,
          hoverOffset:     4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '78%',
      animation: {
        animateRotate: true,
        duration:      1200,
        easing:        'easeOutQuart',
      },
      plugins: {
        legend:  { display: false },
        tooltip: { enabled: false },
      },
    },
  }
}

// ─── Radar chart config factory ──────────────────────────────────────────────

/**
 * Builds a Chart.js Radar config for section-level scores.
 * @param {Object} sectionScores - { skills, experience, education, formatting, keywords }
 */
export function buildRadarConfig(sectionScores) {
  const labels = ['Skills', 'Experience', 'Education', 'Formatting', 'Keywords']
  const values = labels.map((l) => Math.round((sectionScores[l.toLowerCase()] ?? 0) * 100))

  return {
    data: {
      labels,
      datasets: [
        {
          label:              'Your Resume',
          data:               values,
          backgroundColor:    'rgba(34,211,238,0.10)',
          borderColor:        '#22D3EE',
          pointBackgroundColor: '#22D3EE',
          pointBorderColor:   'transparent',
          pointRadius:        4,
          borderWidth:        2,
          fill:               true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 900, easing: 'easeOutQuart' },
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: {
            stepSize:   25,
            color:      '#334155',
            backdropColor: 'transparent',
            font: { size: 10 },
          },
          grid:         { color: 'rgba(255,255,255,0.05)' },
          angleLines:   { color: 'rgba(255,255,255,0.07)' },
          pointLabels: {
            color: '#94A3B8',
            font:  { size: 12, family: '"Inter", system-ui' },
          },
        },
      },
      plugins: {
        legend:  { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.raw}%`,
          },
          backgroundColor: '#1A2236',
          borderColor:     '#1F2D45',
          borderWidth:     1,
          titleColor:      '#F1F5F9',
          bodyColor:       '#94A3B8',
          padding:         10,
        },
      },
    },
  }
}

// ─── Horizontal bar config factory ───────────────────────────────────────────

/**
 * Builds a horizontal bar chart for section-score breakdown.
 * @param {Object} sectionScores
 */
export function buildBarConfig(sectionScores) {
  const entries = Object.entries(sectionScores).map(([k, v]) => ({
    label: k.charAt(0).toUpperCase() + k.slice(1),
    value: Math.round(v * 100),
  }))

  const colours = entries.map(({ value }) => {
    if (value >= 75) return '#10B981'
    if (value >= 50) return '#F59E0B'
    return '#F43F5E'
  })

  return {
    data: {
      labels:   entries.map((e) => e.label),
      datasets: [
        {
          data:            entries.map((e) => e.value),
          backgroundColor: colours,
          borderRadius:    4,
          borderSkipped:   false,
          barThickness:    16,
        },
      ],
    },
    options: {
      indexAxis:   'y',
      responsive:  true,
      maintainAspectRatio: false,
      animation:   { duration: 900, easing: 'easeOutQuart' },
      scales: {
        x: {
          min: 0, max: 100,
          grid:   { color: 'rgba(255,255,255,0.04)' },
          ticks:  { color: '#64748B', callback: (v) => `${v}%` },
          border: { display: false },
        },
        y: {
          grid:   { display: false },
          ticks:  { color: '#94A3B8', font: { size: 12 } },
          border: { display: false },
        },
      },
      plugins: {
        legend:  { display: false },
        tooltip: {
          callbacks: { label: (ctx) => ` ${ctx.raw}%` },
          backgroundColor: '#1A2236',
          borderColor:     '#1F2D45',
          borderWidth:     1,
          titleColor:      '#F1F5F9',
          bodyColor:       '#94A3B8',
          padding:         10,
        },
      },
    },
  }
}
