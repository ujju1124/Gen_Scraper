import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { scraperApi, ScrapeRequest } from '../lib/api'
import { Loader, MapPin, Info, Sparkles, Zap, Mail, MessageSquare, Clock } from 'lucide-react'

export default function NewJob() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showTwoPointMode, setShowTwoPointMode] = useState(false)
  const [point1, setPoint1] = useState({ lat: '', lon: '' })
  const [point2, setPoint2] = useState({ lat: '', lon: '' })
  
  const [formData, setFormData] = useState<ScrapeRequest>({
    keyword: '',
    lang: 'en',
    max_depth: 1,
    email: false,
    geo_coordinates: '',
    zoom: 14,
    radius: 5000,
    fast_mode: false,
    extra_reviews: false,
    timeout: 300,
  })

  // Calculate distance between two points using Haversine formula
  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371 // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon/2) * Math.sin(dLon/2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    return R * c
  }

  // Calculate midpoint and radius from two points
  const calculateFromTwoPoints = () => {
    const lat1 = parseFloat(point1.lat)
    const lon1 = parseFloat(point1.lon)
    const lat2 = parseFloat(point2.lat)
    const lon2 = parseFloat(point2.lon)

    if (isNaN(lat1) || isNaN(lon1) || isNaN(lat2) || isNaN(lon2)) {
      setError('Please enter valid coordinates for both points')
      return
    }

    // Calculate midpoint
    const midLat = (lat1 + lat2) / 2
    const midLon = (lon1 + lon2) / 2

    // Calculate distance and set radius to half (to cover both points)
    const distance = calculateDistance(lat1, lon1, lat2, lon2)
    const radius = Math.ceil((distance / 2) * 1000) // Convert to meters and round up

    // Update form
    setFormData(prev => ({
      ...prev,
      geo_coordinates: `${midLat.toFixed(6)},${midLon.toFixed(6)}`,
      radius: radius
    }))

    setError(null)
    setShowTwoPointMode(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // Clean up the request - only send non-empty values
      const cleanedData: any = {
        keyword: formData.keyword,
        lang: formData.lang,
        max_depth: formData.max_depth,
      }

      // Only add optional fields if they have values
      if (formData.geo_coordinates && formData.geo_coordinates.trim()) {
        cleanedData.geo_coordinates = formData.geo_coordinates.trim()
      }
      
      if (formData.zoom) {
        cleanedData.zoom = formData.zoom
      }
      
      // Convert radius from meters to kilometers for backend
      if (formData.radius) {
        cleanedData.radius = formData.radius / 1000 // Backend expects kilometers
      }
      
      if (formData.timeout) {
        cleanedData.timeout = formData.timeout
      }
      
      if (formData.email) {
        cleanedData.email = true
      }
      
      if (formData.extra_reviews) {
        cleanedData.extra_reviews = true
      }
      
      if (formData.fast_mode) {
        cleanedData.fast_mode = true
      }

      console.log('Submitting job with data:', cleanedData)
      
      const response = await scraperApi.submitJob(cleanedData)
      navigate(`/jobs/${response.job_id}`)
    } catch (err: any) {
      console.error('Submit error:', err)
      const errorMsg = err.response?.data?.message || err.response?.data?.error || err.message || 'Failed to submit job'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : 
              type === 'number' || type === 'range' ? Number(value) : 
              value
    }))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl mb-4 shadow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Create New Scraping Job
          </h1>
          <p className="text-lg text-gray-600">
            Extract valuable business data from Google Maps in minutes
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 text-red-700 px-6 py-4 rounded-lg shadow-sm">
              <div className="flex items-center">
                <Info className="h-5 w-5 mr-2" />
                <span className="font-medium">{error}</span>
              </div>
            </div>
          )}

          {/* Main Search Section */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
            <div className="flex items-center mb-6">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                <MapPin className="h-5 w-5 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Search Configuration</h2>
            </div>

            <div className="space-y-6">
              {/* Keyword */}
              <div>
                <label htmlFor="keyword" className="block text-sm font-semibold text-gray-900 mb-2">
                  Search Keyword *
                </label>
                <input
                  type="text"
                  name="keyword"
                  id="keyword"
                  required
                  value={formData.keyword}
                  onChange={handleChange}
                  placeholder="e.g., restaurants in New York, hotels in Paris"
                  className="block w-full px-4 py-3 rounded-lg border-2 border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-base"
                />
                <div className="mt-2 flex items-start">
                  <Info className="h-4 w-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-gray-600">
                    Enter what you want to search on Google Maps. Be specific for better results.
                  </p>
                </div>
              </div>

              {/* Language */}
              <div>
                <label htmlFor="lang" className="block text-sm font-semibold text-gray-900 mb-2">
                  Language
                </label>
                <select
                  name="lang"
                  id="lang"
                  value={formData.lang}
                  onChange={handleChange}
                  className="block w-full px-4 py-3 rounded-lg border-2 border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-base"
                >
                  <option value="en">🇬🇧 English</option>
                  <option value="es">🇪🇸 Spanish</option>
                  <option value="fr">🇫🇷 French</option>
                  <option value="de">🇩🇪 German</option>
                  <option value="it">🇮🇹 Italian</option>
                  <option value="pt">🇵🇹 Portuguese</option>
                </select>
                <div className="mt-2 flex items-start">
                  <Info className="h-4 w-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-gray-600">
                    Results will be shown in this language
                  </p>
                </div>
              </div>

              {/* Max Depth */}
              <div>
                <label htmlFor="max_depth" className="block text-sm font-semibold text-gray-900 mb-2">
                  Max Depth (Scroll Depth) - Currently: {formData.max_depth}
                </label>
                <input
                  type="range"
                  name="max_depth"
                  id="max_depth"
                  min="1"
                  max="100"
                  value={formData.max_depth}
                  onChange={handleChange}
                  className="block w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1 (~20 results)</span>
                  <span>50 (~1000 results)</span>
                  <span>100 (~2000 results)</span>
                </div>
                <div className="mt-2 flex items-start bg-blue-50 p-3 rounded-lg">
                  <Info className="h-4 w-4 text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-blue-900">
                    <strong>How it works:</strong> The scraper scrolls through Google Maps results. Each scroll loads ~20 more places. 
                    <br />
                    <strong>Recommendation:</strong> Use 10-20 for quick tests, 50+ for comprehensive data.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Location Settings */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
            <div className="flex items-center mb-6">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mr-3">
                <MapPin className="h-5 w-5 text-purple-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Location Settings</h2>
            </div>

            <div className="space-y-6">
              {/* Geo Coordinates */}
              <div>
                <label htmlFor="geo_coordinates" className="block text-sm font-semibold text-gray-900 mb-2">
                  Geographic Coordinates (Optional)
                </label>
                <input
                  type="text"
                  name="geo_coordinates"
                  id="geo_coordinates"
                  value={formData.geo_coordinates}
                  onChange={handleChange}
                  placeholder="27.7172,85.3240"
                  className="block w-full px-4 py-3 rounded-lg border-2 border-gray-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all text-base font-mono"
                />
                <div className="mt-2 flex items-start bg-purple-50 p-3 rounded-lg">
                  <Info className="h-4 w-4 text-purple-600 mr-2 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-purple-900">
                    <strong>Format:</strong> latitude,longitude (e.g., 27.7172,85.3240 for Kathmandu)
                    <br />
                    <strong>Use case:</strong> Search within a specific area or between two cities. Find coordinates on Google Maps by right-clicking.
                  </div>
                </div>

                {/* Two Point Calculator Button */}
                <button
                  type="button"
                  onClick={() => setShowTwoPointMode(!showTwoPointMode)}
                  className="mt-3 inline-flex items-center px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all shadow-md hover:shadow-lg"
                >
                  <MapPin className="h-4 w-4 mr-2" />
                  {showTwoPointMode ? 'Hide' : 'Search Between Two Locations'}
                </button>

                {/* Two Point Calculator */}
                {showTwoPointMode && (
                  <div className="mt-4 p-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border-2 border-purple-200">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                      <MapPin className="h-5 w-5 mr-2 text-purple-600" />
                      Calculate Search Area Between Two Locations
                    </h3>
                    <p className="text-sm text-gray-700 mb-4">
                      Enter coordinates for two locations (e.g., Kalanki and Dhulikhel). We'll automatically calculate the midpoint and radius to cover both areas.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      {/* Point 1 */}
                      <div className="bg-white p-4 rounded-lg border-2 border-purple-300">
                        <label className="block text-sm font-semibold text-gray-900 mb-2">
                          📍 Location 1 (e.g., Kalanki)
                        </label>
                        <input
                          type="text"
                          placeholder="Latitude (e.g., 27.693444)"
                          value={point1.lat}
                          onChange={(e) => setPoint1({ ...point1, lat: e.target.value })}
                          className="block w-full px-3 py-2 rounded-md border-2 border-gray-200 focus:border-purple-500 mb-2 text-sm font-mono"
                        />
                        <input
                          type="text"
                          placeholder="Longitude (e.g., 85.281924)"
                          value={point1.lon}
                          onChange={(e) => setPoint1({ ...point1, lon: e.target.value })}
                          className="block w-full px-3 py-2 rounded-md border-2 border-gray-200 focus:border-purple-500 text-sm font-mono"
                        />
                      </div>

                      {/* Point 2 */}
                      <div className="bg-white p-4 rounded-lg border-2 border-pink-300">
                        <label className="block text-sm font-semibold text-gray-900 mb-2">
                          📍 Location 2 (e.g., Dhulikhel)
                        </label>
                        <input
                          type="text"
                          placeholder="Latitude (e.g., 27.625300)"
                          value={point2.lat}
                          onChange={(e) => setPoint2({ ...point2, lat: e.target.value })}
                          className="block w-full px-3 py-2 rounded-md border-2 border-gray-200 focus:border-pink-500 mb-2 text-sm font-mono"
                        />
                        <input
                          type="text"
                          placeholder="Longitude (e.g., 85.554838)"
                          value={point2.lon}
                          onChange={(e) => setPoint2({ ...point2, lon: e.target.value })}
                          className="block w-full px-3 py-2 rounded-md border-2 border-gray-200 focus:border-pink-500 text-sm font-mono"
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={calculateFromTwoPoints}
                      className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all shadow-md hover:shadow-lg font-semibold"
                    >
                      ✨ Calculate Midpoint & Radius
                    </button>

                    <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                      <p className="text-xs text-blue-900">
                        <strong>💡 Tip:</strong> Right-click on Google Maps to get coordinates. The format is: latitude, longitude
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Zoom Level */}
                <div>
                  <label htmlFor="zoom" className="block text-sm font-semibold text-gray-900 mb-2">
                    Zoom Level - {formData.zoom}
                  </label>
                  <input
                    type="range"
                    name="zoom"
                    id="zoom"
                    min="1"
                    max="21"
                    value={formData.zoom}
                    onChange={handleChange}
                    className="block w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1 (World)</span>
                    <span>14 (City)</span>
                    <span>21 (Street)</span>
                  </div>
                  <div className="mt-2 flex items-start">
                    <Info className="h-4 w-4 text-purple-500 mr-2 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-gray-600">
                      Higher = more zoomed in. Use 10-14 for cities, 15-18 for neighborhoods.
                    </p>
                  </div>
                </div>

                {/* Radius */}
                <div>
                  <label htmlFor="radius" className="block text-sm font-semibold text-gray-900 mb-2">
                    Search Radius - {((formData.radius || 5000) / 1000).toFixed(1)}km
                  </label>
                  <input
                    type="range"
                    name="radius"
                    id="radius"
                    min="1000"
                    max="100000"
                    step="1000"
                    value={formData.radius}
                    onChange={handleChange}
                    className="block w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1km</span>
                    <span>50km</span>
                    <span>100km</span>
                  </div>
                  <div className="mt-2 flex items-start">
                    <Info className="h-4 w-4 text-purple-500 mr-2 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-gray-600">
                      Search area around coordinates. Larger radius = more results but slower.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
            <div className="flex items-center mb-6">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                <Zap className="h-5 w-5 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Advanced Options</h2>
            </div>

            <div className="space-y-6">
              {/* Timeout */}
              <div>
                <label htmlFor="timeout" className="block text-sm font-semibold text-gray-900 mb-2">
                  Timeout - {formData.timeout} seconds
                </label>
                <input
                  type="range"
                  name="timeout"
                  id="timeout"
                  min="60"
                  max="600"
                  step="30"
                  value={formData.timeout}
                  onChange={handleChange}
                  className="block w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-600"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1 min</span>
                  <span>5 min</span>
                  <span>10 min</span>
                </div>
                <div className="mt-2 flex items-start">
                  <Clock className="h-4 w-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-gray-600">
                    Maximum time allowed for the job. Increase for large searches.
                  </p>
                </div>
              </div>

              {/* Feature Toggles */}
              <div className="space-y-4">
                {/* Extract Emails */}
                <div className="flex items-start p-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-xl border-2 border-blue-200 hover:border-blue-300 transition-all cursor-pointer">
                  <div className="flex items-center h-5 mt-1">
                    <input
                      id="email"
                      name="email"
                      type="checkbox"
                      checked={formData.email}
                      onChange={handleChange}
                      className="focus:ring-blue-500 h-5 w-5 text-blue-600 border-gray-300 rounded cursor-pointer"
                    />
                  </div>
                  <div className="ml-4 flex-1">
                    <label htmlFor="email" className="font-semibold text-gray-900 cursor-pointer flex items-center">
                      <Mail className="h-5 w-5 mr-2 text-blue-600" />
                      Extract Email Addresses
                    </label>
                    <p className="text-sm text-gray-700 mt-1">
                      Crawls business websites to find contact emails. <strong>Note:</strong> Makes scraping slower but provides valuable contact info.
                    </p>
                  </div>
                </div>

                {/* Extended Reviews */}
                <div className="flex items-start p-4 bg-gradient-to-r from-purple-50 to-purple-100 rounded-xl border-2 border-purple-200 hover:border-purple-300 transition-all cursor-pointer">
                  <div className="flex items-center h-5 mt-1">
                    <input
                      id="extra_reviews"
                      name="extra_reviews"
                      type="checkbox"
                      checked={formData.extra_reviews}
                      onChange={handleChange}
                      className="focus:ring-purple-500 h-5 w-5 text-purple-600 border-gray-300 rounded cursor-pointer"
                    />
                  </div>
                  <div className="ml-4 flex-1">
                    <label htmlFor="extra_reviews" className="font-semibold text-gray-900 cursor-pointer flex items-center">
                      <MessageSquare className="h-5 w-5 mr-2 text-purple-600" />
                      Extract Extended Reviews
                    </label>
                    <p className="text-sm text-gray-700 mt-1">
                      Collects up to ~300 reviews per place instead of just a few. <strong>Great for:</strong> Sentiment analysis and detailed feedback.
                    </p>
                  </div>
                </div>

                {/* Fast Mode */}
                <div className="flex items-start p-4 bg-gradient-to-r from-green-50 to-green-100 rounded-xl border-2 border-green-200 hover:border-green-300 transition-all cursor-pointer">
                  <div className="flex items-center h-5 mt-1">
                    <input
                      id="fast_mode"
                      name="fast_mode"
                      type="checkbox"
                      checked={formData.fast_mode}
                      onChange={handleChange}
                      className="focus:ring-green-500 h-5 w-5 text-green-600 border-gray-300 rounded cursor-pointer"
                    />
                  </div>
                  <div className="ml-4 flex-1">
                    <label htmlFor="fast_mode" className="font-semibold text-gray-900 cursor-pointer flex items-center">
                      <Zap className="h-5 w-5 mr-2 text-green-600" />
                      Fast Mode (Beta)
                    </label>
                    <p className="text-sm text-gray-700 mt-1">
                      Uses HTTP requests instead of browser for faster scraping. <strong>Requires:</strong> Geographic coordinates. <strong>Trade-off:</strong> Speed vs. detail.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="flex justify-end gap-4">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="px-8 py-3 border-2 border-gray-300 rounded-xl text-base font-semibold text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-400 transition-all shadow-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-8 py-3 border-2 border-transparent rounded-xl text-base font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
            >
              {loading && <Loader className="animate-spin h-5 w-5 mr-2" />}
              {loading ? 'Submitting Job...' : '🚀 Start Scraping'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
