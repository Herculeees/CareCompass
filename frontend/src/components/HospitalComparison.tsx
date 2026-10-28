import type { Hospital } from '../types'
import { PerformanceExplanation } from './HospitalPerformance'
import { measureText } from '../performanceText'

export default function HospitalComparison({
  hospitals,
  onRemove,
}: {
  hospitals: Hospital[]
  onRemove: (locationId: string) => void
}) {
  if (hospitals.length === 0) return null
  const measures = hospitals[0].hcai_performance.measures
  return (
    <section className="comparison-section" aria-labelledby="comparison-title">
      <h2 id="comparison-title">Compare hospitals ({hospitals.length} of 3)</h2>
      <PerformanceExplanation />
      <div style={{ overflowX: 'auto' }}>
        <table>
          <caption>Selected HCAI outcomes · source year 2023</caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              {hospitals.map((hospital) => (
                <th scope="col" key={hospital.location_id}>
                  {hospital.name}
                  <br />
                  <button type="button" onClick={() => onRemove(hospital.location_id)}>
                    Remove {hospital.name}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">CMS overall rating (separate dataset)</th>
              {hospitals.map((hospital) => (
                <td key={hospital.location_id}>
                  {hospital.overall_rating === null ? 'Not available' : `${hospital.overall_rating} / 5`}
                </td>
              ))}
            </tr>
            {measures.map((measure) => (
              <tr key={measure.code}>
                <th scope="row">{measure.category}: {measure.label}</th>
                {hospitals.map((hospital) => {
                  const result = hospital.hcai_performance.measures.find((item) => item.code === measure.code)
                  return (
                    <td key={hospital.location_id}>
                      {result ? measureText(result) : 'No verified result available'}
                      {result?.case_count != null && <div>{result.case_count.toLocaleString()} reported cases</div>}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p><a href={hospitals[0].hcai_performance.source_url} target="_blank" rel="noopener noreferrer">HCAI source and methodology</a></p>
    </section>
  )
}
