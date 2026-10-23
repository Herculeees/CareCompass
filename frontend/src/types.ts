export type PerformanceMeasure = {
  code: string
  category: string
  label: string
  rating: 'Better' | 'As Expected' | 'Worse' | null
  case_count: number | null
  availability: 'rated' | 'not_reported' | 'no_verified_result'
}

export type Hospital = {
  location_id: string
  name: string
  address: string | null
  city: string | null
  overall_rating: number | null
  emergency_services: boolean | null
  latitude: number | null
  longitude: number | null
  hcai_performance: {
    year: number
    source: string
    source_url: string
    match_status: string
    match_note: string
    source_hospital_name: string | null
    measures: PerformanceMeasure[]
  }
}
