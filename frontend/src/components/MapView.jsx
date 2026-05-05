/**
 * MapView Component
 * Displays business locations on an interactive Leaflet map with clustering
 */
import { useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default marker icons in Leaflet with Webpack/Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
})

/**
 * Component to auto-fit map bounds to markers
 */
function FitBounds({ positions }) {
  const map = useMap()

  useEffect(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(positions)
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 })
    }
  }, [positions, map])

  return null
}

/**
 * MapView Component
 * @param {Object} props
 * @param {Array} props.results - Array of result objects with latitude/longitude
 * @param {number} props.height - Map height in pixels (default: 600)
 */
export function MapView({ results = [], height = 600 }) {
  // Filter results that have valid coordinates
  const validResults = useMemo(() => {
    return results.filter(
      (result) =>
        result.latitude != null &&
        result.longitude != null &&
        !isNaN(result.latitude) &&
        !isNaN(result.longitude) &&
        result.latitude >= -90 &&
        result.latitude <= 90 &&
        result.longitude >= -180 &&
        result.longitude <= 180
    )
  }, [results])

  const skippedCount = results.length - validResults.length

  // Extract positions for bounds fitting
  const positions = useMemo(() => {
    return validResults.map((result) => [result.latitude, result.longitude])
  }, [validResults])

  // Default center (Kathmandu, Nepal)
  const defaultCenter = [27.7172, 85.324]
  const center = positions.length > 0 ? positions[0] : defaultCenter

  if (results.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-slate-50 border-2 border-dashed border-slate-300 rounded-lg"
        style={{ height: `${height}px` }}
      >
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-slate-900">No data to display</h3>
          <p className="mt-1 text-sm text-slate-500">
            No results available to show on the map
          </p>
        </div>
      </div>
    )
  }

  if (validResults.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-slate-50 border-2 border-dashed border-slate-300 rounded-lg"
        style={{ height: `${height}px` }}
      >
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-slate-900">
            No coordinates available
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {skippedCount} result{skippedCount !== 1 ? 's' : ''} without valid location data
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {skippedCount > 0 && (
        <div className="text-sm text-slate-600 bg-slate-50 px-4 py-2 rounded-md">
          Showing {validResults.length} location{validResults.length !== 1 ? 's' : ''} on map
          ({skippedCount} result{skippedCount !== 1 ? 's' : ''} without coordinates)
        </div>
      )}
      <div style={{ height: `${height}px` }} className="rounded-lg overflow-hidden shadow-sm">
        <MapContainer
          center={center}
          zoom={13}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MarkerClusterGroup
            chunkedLoading
            maxClusterRadius={50}
            spiderfyOnMaxZoom={true}
            showCoverageOnHover={false}
          >
            {validResults.map((result) => (
              <Marker
                key={result.id}
                position={[result.latitude, result.longitude]}
                title={result.name || 'Unknown'}
              >
                <Popup maxWidth={300}>
                  <div className="p-2">
                    <h3 className="font-semibold text-slate-900 mb-2">
                      {result.name || 'Unknown Business'}
                    </h3>
                    {result.address && (
                      <p className="text-sm text-slate-600 mb-1">
                        <span className="font-medium">Address:</span> {result.address}
                      </p>
                    )}
                    {result.city && (
                      <p className="text-sm text-slate-600 mb-1">
                        <span className="font-medium">City:</span> {result.city}
                      </p>
                    )}
                    {result.phone_primary && (
                      <p className="text-sm text-slate-600 mb-1">
                        <span className="font-medium">Phone:</span> {result.phone_primary}
                      </p>
                    )}
                    {result.rating_overall && (
                      <p className="text-sm text-slate-600 mb-1">
                        <span className="font-medium">Rating:</span>{' '}
                        {parseFloat(result.rating_overall).toFixed(1)} / 10
                      </p>
                    )}
                    {result.price_min && (
                      <p className="text-sm text-slate-600">
                        <span className="font-medium">Price:</span> NPR{' '}
                        {parseFloat(result.price_min).toLocaleString()}
                      </p>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MarkerClusterGroup>

          <FitBounds positions={positions} />
        </MapContainer>
      </div>
    </div>
  )
}
