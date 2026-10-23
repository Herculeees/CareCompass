import type { Hospital } from '../types'
import { measureText } from '../performanceText'

export function PerformanceExplanation() {
  return (
    <p>
      These are selected condition and procedure outcomes, not overall hospital
      or specialty ratings. Better, As Expected, and Worse describe risk-adjusted
      performance relative to the state benchmark. As Expected does not mean poor
      care. Missing results do not indicate poor quality. The year is the source
      report label; underlying measurement periods can differ.
    </p>
  )
}

export default function HospitalPerformance({ hospital }: { hospital: Hospital }) {
  const performance = hospital.hcai_performance
  return (
    <details>
      <summary>Advanced comparison — HCAI {performance.year}</summary>
      <PerformanceExplanation />
      {performance.match_status !== 'matched' && <p>{performance.match_note}</p>}
      {performance.source_hospital_name && (
        <p>Source facility: {performance.source_hospital_name}</p>
      )}
      <dl>
        {performance.measures.map((measure) => (
          <div key={measure.code}>
            <dt>{measure.category}: {measure.label}</dt>
            <dd>
              {measureText(measure)}
              {measure.case_count !== null && ` · ${measure.case_count.toLocaleString()} reported cases`}
            </dd>
          </div>
        ))}
      </dl>
      <a href={performance.source_url} target="_blank" rel="noopener noreferrer">
        HCAI source and methodology
      </a>
    </details>
  )
}
