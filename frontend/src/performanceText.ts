import type { PerformanceMeasure } from './types'

export function measureText(measure: PerformanceMeasure) {
  if (measure.rating !== null) return measure.rating
  return measure.availability === 'not_reported'
    ? 'Rating not reported in source'
    : 'No verified result available'
}
