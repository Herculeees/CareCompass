import { useCallback, useEffect, useState } from 'react'
import type { Hospital } from './types'
import HospitalPerformance from './components/HospitalPerformance'
import HospitalComparison from './components/HospitalComparison'
import HospitalMap from './components/HospitalMap'

type UserLocation = {
  latitude: number
  longitude: number
}

function App() {
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [comparison, setComparison] = useState<Hospital[]>([])
  const handleAddToComparison = useCallback((hospital: Hospital) => {
    setComparison((previous) => (
      previous.length >= 3 || previous.some((item) => item.location_id === hospital.location_id)
        ? previous : [...previous, hospital]
    ))
  }, [])
  const [name, setName] = useState('')
  const [city, setCity] = useState('')
  const [zipCode, setZipCode] = useState('')
  const [emergencyOnly, setEmergencyOnly] = useState(false)
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null)
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [searchFilters, setSearchFilters] = useState({
    name: '',
    city: '',
    zipCode: '',
    emergencyOnly: false,
    location: null as UserLocation | null,
  })

function handleUseLocation() {
  if (!navigator.geolocation) {
    setLocationError('Your browser does not support location access.')
    return
  }

  setLocating(true)
  setLocationError(null)

  navigator.geolocation.getCurrentPosition(
    (position) => {
      setUserLocation({latitude: position.coords.latitude, longitude: position.coords.longitude})
      setLocating(false)
    },
    (error) => {
      setLocationError(
        error.code === error.PERMISSION_DENIED
          ? 'Location access was denied. You can still search by city or ZIP.'
          : 'Unable to get your location. Please try again.',
      )
      setLocating(false)
    },
    { timeout: 10000 },
  )
}

  useEffect(() => {
    const controller = new AbortController()

    const params = new URLSearchParams()
    params.set('limit', '20')

    if (searchFilters.name.trim()) {
      params.set('name', searchFilters.name.trim())
    }

    if (searchFilters.city.trim() && !searchFilters.zipCode.trim()) {
      params.set('near_city', searchFilters.city.trim())
    }

    if (searchFilters.zipCode.trim()) {
      params.set('near_zip', searchFilters.zipCode.trim())
    }

    if (searchFilters.emergencyOnly) {
      params.set('emergency_services', 'true')
    }

    if (
      searchFilters.location &&
      !searchFilters.zipCode.trim() &&
      !searchFilters.city.trim()
    ) {
      params.set('latitude', searchFilters.location.latitude.toString(),)
      params.set('longitude',searchFilters.location.longitude.toString(),)
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
          setSearchFilters({ name, city, zipCode, emergencyOnly, location: userLocation})
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
        <label htmlFor="city">Search near California city</label>
        <input
          id="city"
          type="text"
          value={city}
          onChange={(event) => setCity(event.target.value)}
        />
      </div>

      <div>
        <label htmlFor="zip-code">Search near ZIP code</label>
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

    <div>
    <button type="button" onClick={handleUseLocation} disabled={locating}>
      {locating ? 'Getting your location...' : 'Use my location'}
    </button>

    {locationError && <p role="alert">{locationError}</p>}

    {userLocation && (
      <p>
        Your location: {userLocation.latitude.toFixed(4)},{' '}
        {userLocation.longitude.toFixed(4)}
      </p>
    )}
    </div>

      {loading && <p>Loading hospitals…</p>}

      {error && <p role="alert">{error}</p>}

      {!loading && !error && hospitals.length === 0 && (
        <p>No hospitals found.</p>
      )}

      {!loading && !error && (
        <>
          <HospitalMap
            hospitals={hospitals}
            comparison={comparison}
            onAddToComparison={handleAddToComparison}
          />
          <ul>
          {hospitals.map((hospital) => (
            <li key={hospital.location_id}>
              <h2>{hospital.name}</h2>
              {hospital.distance_miles !== null && (
                <p>
                  {hospital.distance_miles.toFixed(1)} miles away
                  {' '}(straight-line distance)
                </p>
              )}
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
                onClick={() => handleAddToComparison(hospital)}
              >
                {comparison.some((item) => item.location_id === hospital.location_id) ? 'Added to comparison' : 'Add to comparison'}
              </button>
            </li>
          ))}
            </ul>
        </>
      )}
    </main>
  )
}

export default App
