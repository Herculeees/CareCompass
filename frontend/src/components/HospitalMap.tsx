import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export default function HospitalMap() {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const map = L.map(containerRef.current).setView(
      [36.7, -119.5],
      6,
    )

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
    }
  }, [])

  return (
    <div
      ref={containerRef}
      style={{ height: '400px', width: '100%' }}
      aria-label="Hospital map"
    />
  )
}