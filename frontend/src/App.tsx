import { useEffect, useState } from 'react'
import type { Hospital } from './types'
import HospitalPerformance from './components/HospitalPerformance'
import HospitalComparison from './components/HospitalComparison'

function App() {
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [comparison, setComparison] = useState<Hospital[]>([])
  const [name, setName] = useState('')
  const [city, setCity] = useState('')
  const [zipCode, setZipCode] = useState('')
  const [emergencyOnly, setEmergencyOnly] = useState(false)
  const [searchFilters, setSearchFilters] = useState({
    name: '',
    city: '',
    zipCode: '',
    emergencyOnly: false,
  })

  useEffect(() => {
    const controller = new AbortController()

    const params = new URLSearchParams()
    params.set('limit', '20')

    if (searchFilters.name.trim()) {
      params.set('name', searchFilters.name.trim())
    }

    if (searchFilters.city.trim()) {
      params.set('city', searchFilters.city.trim())
    }

    if (searchFilters.zipCode.trim()) {
      params.set('zip_code', searchFilters.zipCode.trim())
    }

    if (searchFilters.emergencyOnly) {
      params.set('emergency_services', 'true')
    }

    async function loadHospitals() {
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/hospitals?${params.toString()}`,
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }

        const data: { hospitals: Hospital[] } = await response.json()

        if (!controller.signal.aborted) {
          setHospitals(data.hospitals)
        }
      } catch {
        if (!controller.signal.aborted) {
          setError('Unable to load hospitals. Please try again later.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadHospitals()

    return () => controller.abort()
  }, [searchFilters])

  return (
    <main>
      <h1>CareCompass</h1>
      <p>Find and compare hospitals in California.</p>
      <HospitalComparison
        hospitals={comparison}
        onRemove={(locationId) => setComparison((previous) => previous.filter((item) => item.location_id !== locationId))}
      />

      <form
        onSubmit={(event) => {
          event.preventDefault()
          setLoading(true)
          setError(null)
          setSearchFilters({ name, city, zipCode, emergencyOnly })
        }}
      >
      <div>
        <label htmlFor="hospital-name">Hospital name</label>
        <input
          id="hospital-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      <div>
        <label htmlFor="city">City</label>
        <input
          id="city"
          type="text"
          value={city}
          onChange={(event) => setCity(event.target.value)}
        />
      </div>

      <div>
        <label htmlFor="zip-code">ZIP code</label>
        <input
          id="zip-code"
          type="text"
          inputMode="numeric"
          value={zipCode}
          onChange={(event) => setZipCode(event.target.value)}
        />
      </div>

      <div>
        <label>
          <input
            type="checkbox"
            checked={emergencyOnly}
            onChange={(event) => setEmergencyOnly(event.target.checked)}
          />
          Emergency services only
        </label>
      </div>

      <button type="submit">Search</button>
    </form>

      {loading && <p>Loading hospitals…</p>}

      {error && <p role="alert">{error}</p>}

      {!loading && !error && hospitals.length === 0 && (
        <p>No hospitals found.</p>
      )}

      {!loading && !error && (
        <ul>
          {hospitals.map((hospital) => (
            <li key={hospital.location_id}>
              <h2>{hospital.name}</h2>
              <p>
                {hospital.address ?? 'Address unavailable'}
                {hospital.city ? `, ${hospital.city}` : ''}
              </p>
              <p>
                CMS overall rating: {hospital.overall_rating === null ? 'Not available' : `${hospital.overall_rating} / 5`}
              </p>
              <p>
                Emergency services: {hospital.emergency_services === null ? 'Unknown': hospital.emergency_services ? 'Yes' : 'No'}
              </p>
              <p>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([hospital.name, hospital.address, hospital.city, 'CA'].filter(Boolean).join(', '))}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View hospital on Google Maps
                </a>
              </p>
              <HospitalPerformance hospital={hospital} />
              <button
                type="button"
                disabled={comparison.length >= 3 || comparison.some((item) => item.location_id === hospital.location_id)}
                onClick={() => setComparison((previous) => (
                  previous.length >= 3 || previous.some((item) => item.location_id === hospital.location_id)
                    ? previous : [...previous, hospital]
                ))}
              >
                {comparison.some((item) => item.location_id === hospital.location_id) ? 'Added to comparison' : 'Add to comparison'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}

export default App
