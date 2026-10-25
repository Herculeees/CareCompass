import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Hospital } from '../types'

type HospitalMapProps = {
  hospitals: Hospital[]
}

export default function HospitalMap({ hospitals }: HospitalMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)

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
      popup.textContent = hospital.name

      L.circleMarker([latitude, longitude], {
        radius: 8,
        color: '#075985',
        fillColor: '#0ea5e9',
        fillOpacity: 0.85,
        weight: 2,
      })
        .bindPopup(popup)
        .addTo(markers)
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
    }
  }, [hospitals])

  return (
    <div
      data-hospital-count={hospitals.length}
      ref={containerRef}
      style={{ height: '400px', width: '100%' }}
      aria-label="Hospital map"
    />
  )
}
