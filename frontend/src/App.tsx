import { useEffect, useState } from 'react'

type Hospital = {
  location_id: string
  name: string
  address: string | null
  city: string | null
}

function App() {
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadHospitals() {
      try {
        const response = await fetch(
          'http://127.0.0.1:8000/hospitals?limit=5',
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }

        const data: { hospitals: Hospital[] } = await response.json()

        setHospitals(data.hospitals)
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
  }, [])

  return (
    <main>
      <h1>CareCompass</h1>
      <p>Find and compare hospitals in California.</p>

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
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}

export default App