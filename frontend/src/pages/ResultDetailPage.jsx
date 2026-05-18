/**
 * Result Detail Page
 * Displays full details for a single cleaned result
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as jobService from '../services/jobService'
import { StatusBadge } from '../components/StatusBadge'
import { ProgressBar } from '../components/ProgressBar'
import { MapView } from '../components/MapView'

export function ResultDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Category-specific field groups
  const CATEGORY_FIELDS = {
    hotels: ['name', 'brand', 'property_type', 'star_rating', 'address', 'street_address', 'city', 'district', 'latitude', 'longitude', 'phone_primary', 'phone_secondary', 'email', 'website', 'price_min', 'price_max', 'currency', 'includes_breakfast', 'rating_overall', 'review_count', 'rating_cleanliness', 'rating_location', 'rating_facilities', 'amenities', 'pets_allowed', 'checkin_time', 'checkout_time'],
    restaurants: ['name', 'address', 'city', 'district', 'latitude', 'longitude', 'phone_primary', 'phone_secondary', 'email', 'website', 'price_min', 'price_max', 'currency', 'rating_overall', 'review_count', 'cuisine_type', 'opening_hours', 'amenities'],
    pharmacies: ['name', 'address', 'city', 'district', 'latitude', 'longitude', 'phone_primary', 'phone_secondary', 'email', 'website', 'opening_hours', 'description_short'],
    hospitals: ['name', 'address', 'city', 'district', 'latitude', 'longitude', 'phone_primary', 'phone_secondary', 'email', 'website', 'description_short', 'amenities'],
    banks: ['name', 'address', 'city', 'district', 'latitude', 'longitude', 'phone_primary', 'phone_secondary', 'email', 'website', 'opening_hours'],
    // default: show only non-null fields
    default: null
  }

  // Helper to check if field should be displayed
  const shouldDisplayField = (fieldName, categoryName) => {
    if (!result) return false
    
    // Get category-specific fields or use default (all non-null)
    const categoryFields = CATEGORY_FIELDS[categoryName?.toLowerCase()] || CATEGORY_FIELDS.default
    
    if (categoryFields === null) {
      // Default: show only non-null fields
      return result[fieldName] !== null && result[fieldName] !== undefined && result[fieldName] !== ''
    }
    
    // Show field if it's in the category's field list
    return categoryFields.includes(fieldName)
  }

  useEffect(() => {
    const fetchResult = async () => {
      setLoading(true)
      setError('')

      try {
        const data = await jobService.getResultDetail(id)
        setResult(data)
      } catch (err) {
        if (err.status === 404) {
          setError('Result not found')
        } else {
          setError('Failed to load result details')
        }
        console.error('Error fetching result:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchResult()
  }, [id])

  const formatValue = (value) => {
    if (value === null || value === undefined || value === '') {
      return 'Not available'
    }
    return value
  }

  const formatPrice = (price, currency = 'NPR') => {
    if (!price) return 'Not available'
    return `${currency} ${parseFloat(price).toLocaleString()}`
  }

  const formatRating = (rating) => {
    if (!rating) return 'Not available'
    return `${parseFloat(rating).toFixed(1)} / 10`
  }

  const formatBoolean = (value) => {
    if (value === null || value === undefined) return 'Not available'
    return value ? 'Yes' : 'No'
  }

  const formatArray = (arr) => {
    if (!arr || !Array.isArray(arr) || arr.length === 0) {
      return 'Not available'
    }
    return arr
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Result Details</h1>
          <button onClick={() => navigate(-1)} className="btn btn-secondary">
            Back to Results
          </button>
        </div>
        <div className="card p-8">
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <p className="mt-4 text-sm text-slate-600">Loading details...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Result Details</h1>
          <button onClick={() => navigate(-1)} className="btn btn-secondary">
            Back to Results
          </button>
        </div>
        <div className="card p-8 text-center">
          <svg
            className="mx-auto h-12 w-12 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <p className="mt-4 text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return null
  }

  const hasCoordinates = result.latitude && result.longitude
  
  // Get category name for field filtering
  const categoryName = result.category_name || result.category || 'default'

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {formatValue(result.name)}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Result ID: {id} • Category: {categoryName}
          </p>
        </div>
        <button onClick={() => navigate(-1)} className="btn btn-secondary">
          Back to Results
        </button>
      </div>

      {/* Identity Section */}
      {(shouldDisplayField('name', categoryName) || shouldDisplayField('brand', categoryName) || shouldDisplayField('property_type', categoryName) || shouldDisplayField('star_rating', categoryName)) && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Identity</h2>
            <StatusBadge status={result.status} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shouldDisplayField('name', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Name</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.name)}</p>
              </div>
            )}
            {shouldDisplayField('brand', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Brand</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.brand)}</p>
              </div>
            )}
            {shouldDisplayField('property_type', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Property Type</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.property_type)}</p>
              </div>
            )}
            {shouldDisplayField('star_rating', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Star Rating</label>
                <p className="mt-1 text-sm text-slate-900">
                  {result.star_rating ? `${result.star_rating} ⭐` : 'Not available'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Location Section */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Location</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm font-medium text-slate-700">Address</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.address)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Street Address</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.street_address)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">City</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.city)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">District</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.district)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Coordinates</label>
            <p className="mt-1 text-sm text-slate-900">
              {hasCoordinates
                ? `${result.latitude}, ${result.longitude}`
                : 'Not available'}
            </p>
          </div>
        </div>
        {hasCoordinates && (
          <div className="mt-4">
            <label className="text-sm font-medium text-slate-700 mb-2 block">Map</label>
            <MapView results={[result]} height={250} />
          </div>
        )}
      </div>

      {/* Contact Section */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Contact</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-slate-700">Primary Phone</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.phone_primary)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Secondary Phone</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.phone_secondary)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Email</label>
            <p className="mt-1 text-sm text-slate-900">{formatValue(result.email)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Website</label>
            <p className="mt-1 text-sm text-slate-900">
              {result.website ? (
                <a
                  href={result.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-700 underline"
                >
                  {result.website}
                </a>
              ) : (
                'Not available'
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Pricing Section */}
      {(shouldDisplayField('price_min', categoryName) || shouldDisplayField('price_max', categoryName) || shouldDisplayField('currency', categoryName) || shouldDisplayField('includes_breakfast', categoryName)) && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Pricing</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shouldDisplayField('price_min', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Minimum Price</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatPrice(result.price_min, result.currency)}
                </p>
              </div>
            )}
            {shouldDisplayField('price_max', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Maximum Price</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatPrice(result.price_max, result.currency)}
                </p>
              </div>
            )}
            {shouldDisplayField('currency', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Currency</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.currency)}</p>
              </div>
            )}
            {shouldDisplayField('includes_breakfast', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Includes Breakfast</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatBoolean(result.includes_breakfast)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reviews Section */}
      {(shouldDisplayField('rating_overall', categoryName) || shouldDisplayField('review_count', categoryName) || shouldDisplayField('rating_cleanliness', categoryName) || shouldDisplayField('rating_location', categoryName) || shouldDisplayField('rating_facilities', categoryName)) && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Reviews</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shouldDisplayField('rating_overall', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Overall Rating</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatRating(result.rating_overall)}
                </p>
              </div>
            )}
            {shouldDisplayField('review_count', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Review Count</label>
                <p className="mt-1 text-sm text-slate-900">
                  {result.review_count ? `${result.review_count} reviews` : 'Not available'}
                </p>
              </div>
            )}
            {shouldDisplayField('rating_cleanliness', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Cleanliness</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatRating(result.rating_cleanliness)}
                </p>
              </div>
            )}
            {shouldDisplayField('rating_location', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Location</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatRating(result.rating_location)}
                </p>
              </div>
            )}
            {shouldDisplayField('rating_facilities', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Facilities</label>
                <p className="mt-1 text-sm text-slate-900">
                  {formatRating(result.rating_facilities)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Facilities Section */}
      {(shouldDisplayField('amenities', categoryName) || shouldDisplayField('pets_allowed', categoryName) || shouldDisplayField('checkin_time', categoryName) || shouldDisplayField('checkout_time', categoryName) || shouldDisplayField('opening_hours', categoryName) || shouldDisplayField('cuisine_type', categoryName) || shouldDisplayField('description_short', categoryName)) && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Facilities & Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shouldDisplayField('amenities', categoryName) && (
              <div className="md:col-span-2">
                <label className="text-sm font-medium text-slate-700">Amenities</label>
                <div className="mt-2">
                  {formatArray(result.amenities) === 'Not available' ? (
                    <p className="text-sm text-slate-900">Not available</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {result.amenities.map((amenity, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary-100 text-primary-800"
                        >
                          {amenity}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            {shouldDisplayField('description_short', categoryName) && (
              <div className="md:col-span-2">
                <label className="text-sm font-medium text-slate-700">Description</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.description_short)}</p>
              </div>
            )}
            {shouldDisplayField('cuisine_type', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Cuisine Type</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.cuisine_type)}</p>
              </div>
            )}
            {shouldDisplayField('opening_hours', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Opening Hours</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.opening_hours)}</p>
              </div>
            )}
            {shouldDisplayField('pets_allowed', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Pets Allowed</label>
                <p className="mt-1 text-sm text-slate-900">{formatBoolean(result.pets_allowed)}</p>
              </div>
            )}
            {shouldDisplayField('checkin_time', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Check-in Time</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.checkin_time)}</p>
              </div>
            )}
            {shouldDisplayField('checkout_time', categoryName) && (
              <div>
                <label className="text-sm font-medium text-slate-700">Check-out Time</label>
                <p className="mt-1 text-sm text-slate-900">{formatValue(result.checkout_time)}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Data Quality Section */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Data Quality</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-slate-700">Data Completeness</label>
            <div className="mt-2">
              <ProgressBar percentage={result.data_completeness || 0} />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Source URL</label>
            <p className="mt-1 text-sm text-slate-900">
              {result.source_url ? (
                <a
                  href={result.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-700 underline break-all"
                >
                  View Source
                </a>
              ) : (
                'Not available'
              )}
            </p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Edited</label>
            <p className="mt-1 text-sm text-slate-900">{formatBoolean(result.is_edited)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Duplicate</label>
            <p className="mt-1 text-sm text-slate-900">{formatBoolean(result.is_duplicate)}</p>
          </div>
          {result.merged_from_sources && result.merged_from_sources.length >= 2 && (
            <div>
              <label className="text-sm font-medium text-slate-700">Merged From</label>
              <p className="mt-1 text-sm text-slate-900">
                {result.merged_from_sources.length} sources
              </p>
            </div>
          )}
          {result.confidence_score != null && (
            <div>
              <label className="text-sm font-medium text-slate-700">Confidence Score</label>
              <p className="mt-1 text-sm text-slate-900">
                {Math.round(result.confidence_score * 100)}%
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
