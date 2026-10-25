import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Hospital } from '../types'

type HospitalMapProps = {
  hospitals: Hospital[]
  comparison: Hospital[]
  onAddToComparison: (hospital: Hospital) => void
}

export default function HospitalMap({ hospitals, comparison, onAddToComparison }: HospitalMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const compareButtons = useRef(new Map<string, HTMLButtonElement>())

  useEffect(() => {
    if (!containerRef.current) return

    const map = L.map(containerRef.current).setView(
      [36.7, -119.5],
      6,
    )
    mapRef.current = map

    L.tileLayer(
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    ).addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current

    if (!map) return

    const markers = L.featureGroup().addTo(map)
    const buttons = compareButtons.current
    buttons.clear()

    for (const hospital of hospitals) {
      const { latitude, longitude } = hospital

      if (
        latitude === null ||
        longitude === null ||
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        Math.abs(latitude) > 90 ||
        Math.abs(longitude) > 180
      ) {
        continue
      }

      const popup = document.createElement('div')
      const name = document.createElement('strong')
      name.textContent = hospital.name
      const details = document.createElement('details')
      const summary = document.createElement('summary')
      summary.textContent = 'View details'
      const address = document.createElement('p')
      address.textContent = [hospital.address, hospital.city].filter(Boolean).join(', ') || 'Address unavailable'
      const rating = document.createElement('p')
      rating.textContent = `CMS overall rating: ${hospital.overall_rating === null ? 'Not available' : `${hospital.overall_rating} / 5`}`
      const emergency = document.createElement('p')
      emergency.textContent = `Emergency services: ${hospital.emergency_services === null ? 'Unknown' : hospital.emergency_services ? 'Yes' : 'No'}`
      const compareButton = document.createElement('button')
      compareButton.type = 'button'
      compareButton.textContent = 'Add to comparison'
      compareButton.setAttribute('aria-label', `Add ${hospital.name} to comparison`)
      compareButton.addEventListener('click', () => {
        onAddToComparison(hospital)
      })
      buttons.set(hospital.location_id, compareButton)
      details.append(summary, address, rating, emergency)
      if (hospital.distance_miles !== null) {
        const distance = document.createElement('p')
        distance.textContent = `${hospital.distance_miles.toFixed(1)} miles (straight-line distance from search location)`
        details.append(distance)
      }
      details.append(compareButton)
      popup.append(name, details)

      const marker = L.circleMarker([latitude, longitude], {
        radius: 8,
        color: '#075985',
        fillColor: '#0ea5e9',
        fillOpacity: 0.85,
        weight: 2,
      })
        .bindPopup(popup, { autoPan: false, maxHeight: 260 })
        .addTo(markers)
      details.addEventListener('toggle', () => marker.getPopup()?.update())
    }

    if (markers.getLayers().length > 0) {
      map.fitBounds(markers.getBounds(), {
        padding: [30, 30],
        maxZoom: 13,
      })
    } else {
      map.setView([36.7, -119.5], 6)
    }

    return () => {
      markers.remove()
      buttons.clear()
    }
  }, [hospitals, onAddToComparison])

  useEffect(() => {
    compareButtons.current.forEach((button, locationId) => {
      const alreadyAdded = comparison.some((hospital) => hospital.location_id === locationId)
      button.disabled = alreadyAdded || comparison.length >= 3
      button.textContent = alreadyAdded
        ? 'Added to comparison'
        : comparison.length >= 3 ? 'Comparison full (3 of 3)' : 'Add to comparison'
    })
  }, [comparison, hospitals, onAddToComparison])

  return (
    <div
      data-hospital-count={hospitals.length}
      ref={containerRef}
      style={{ height: '400px', width: '100%' }}
      aria-label="Hospital map"
    />
  )
}
