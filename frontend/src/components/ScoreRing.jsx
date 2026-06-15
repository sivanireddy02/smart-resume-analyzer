/**
 * components/ScoreRing.jsx
 *
 * Hero metric: animated doughnut chart showing the overall match score.
 * Renders a Chart.js Doughnut with a centred score label overlay.
 */

import { Doughnut } from 'react-chartjs-2'
import { buildScoreDoughnutConfig, scoreColour } from '../utils/chartConfig'

export default function ScoreRing({ score }) {
  const { primary, label } = scoreColour(score)
  const config = buildScoreDoughnutConfig(score)

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Chart wrapper — relative so the centred label can be absolutely positioned */}
      <div className="relative w-52 h-52">
        <Doughnut data={config.data} options={config.options} />

        {/* Centred score overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
             style={{ paddingTop: '10px' }}>
          <span
            className="text-5xl font-display font-bold leading-none tabular-nums"
            style={{ color: primary }}
          >
            {Math.round(score)}
          </span>
          <span className="text-muted text-sm font-mono mt-1">/ 100</span>
        </div>
      </div>

      {/* Label badge */}
      <div
        className="px-4 py-1.5 rounded-full text-sm font-medium border"
        style={{
          color:            primary,
          borderColor:      `${primary}40`,
          backgroundColor:  `${primary}10`,
        }}
      >
        {label}
      </div>
    </div>
  )
}
