import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { scraperApi, JobStatusResponse } from '../lib/api'
import { ArrowLeft, Download, RefreshCw, Loader, CheckCircle, XCircle, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function JobDetails() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadJob = async () => {
    if (!jobId) return
    
    try {
      setLoading(true)
      setError(null)
      const response = await scraperApi.getJob(jobId)
      setJob(response)
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load job')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJob()
    // Auto-refresh every 3 seconds if job is running
    const interval = setInterval(() => {
      if (job?.status === 'running' || job?.status === 'pending') {
        loadJob()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [jobId, job?.status])

  const downloadResults = () => {
    if (!job?.results) return
    
    const dataStr = JSON.stringify(job.results, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `job-${jobId}-results.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-8 w-8 text-green-500" />
      case 'failed':
        return <XCircle className="h-8 w-8 text-red-500" />
      case 'running':
        return <Loader className="h-8 w-8 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-8 w-8 text-yellow-500" />
    }
  }

  if (loading && !job) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    )
  }

  if (!job) return null

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Jobs
        </button>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {getStatusIcon(job.status)}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{job.keyword}</h1>
              <p className="text-sm text-gray-500">Job ID: {job.job_id}</p>
            </div>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={loadJob}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </button>
            {job.results && (
              <button
                onClick={downloadResults}
                className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <Download className="h-4 w-4 mr-1" />
                Download JSON
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Job Info */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Job Information</h3>
        </div>
        <div className="border-t border-gray-200">
          <dl>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  job.status === 'completed' ? 'bg-green-100 text-green-800' :
                  job.status === 'failed' ? 'bg-red-100 text-red-800' :
                  job.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {job.status}
                </span>
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Created</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {new Date(job.created_at).toLocaleString()} ({formatDistanceToNow(new Date(job.created_at), { addSuffix: true })})
              </dd>
            </div>
            {job.started_at && (
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Started</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {new Date(job.started_at).toLocaleString()}
                </dd>
              </div>
            )}
            {job.completed_at && (
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Completed</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {new Date(job.completed_at).toLocaleString()}
                </dd>
              </div>
            )}
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Results Count</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {job.result_count > 0 ? (
                  <span className="font-semibold text-green-600">{job.result_count} places</span>
                ) : (
                  <span className="text-gray-400">No results yet</span>
                )}
              </dd>
            </div>
            {job.scraper_source && (
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Scraper Source</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                    job.scraper_source === 'gosom' 
                      ? 'bg-blue-100 text-blue-800 border border-blue-300' 
                      : job.scraper_source === 'dual'
                      ? 'bg-gradient-to-r from-blue-100 to-purple-100 text-purple-800 border border-purple-300'
                      : 'bg-green-100 text-green-800 border border-green-300'
                  }`}>
                    {job.scraper_source === 'gosom' 
                      ? '🔍 Gosom Scraper' 
                      : job.scraper_source === 'dual'
                      ? '⚡ Dual Scraper (Gosom + Python)'
                      : '🌐 SerpApi Fallback'}
                  </span>
                </dd>
              </div>
            )}
            {job.error && (
              <div className="bg-red-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-red-500">Error</dt>
                <dd className="mt-1 text-sm text-red-700 sm:mt-0 sm:col-span-2">
                  {job.error}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Results Preview */}
      {job.results && Array.isArray(job.results) && job.results.length > 0 && (
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Results Preview ({job.results.length} places)
            </h3>
          </div>
          <div className="border-t border-gray-200">
            <div className="space-y-6 p-6">
              {job.results.slice(0, 10).map((result: any, idx: number) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                  {/* Header with image and basic info */}
                  <div className="flex gap-4 mb-4">
                    {result.thumbnail && (
                      <img 
                        src={result.thumbnail} 
                        alt={result.title}
                        className="w-24 h-24 object-cover rounded-lg flex-shrink-0"
                      />
                    )}
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-gray-900 mb-1">{result.title || 'Untitled'}</h4>
                      <div className="flex items-center gap-2 mb-2">
                        {result.review_rating && (
                          <span className="inline-flex items-center px-2 py-1 rounded-md bg-yellow-50 text-yellow-800 text-sm font-medium">
                            ⭐ {result.review_rating} ({result.review_count || 0} reviews)
                          </span>
                        )}
                        {result.category && (
                          <span className="inline-flex items-center px-2 py-1 rounded-md bg-blue-50 text-blue-700 text-sm">
                            {result.category}
                          </span>
                        )}
                      </div>
                      {result.address && (
                        <p className="text-sm text-gray-600 mb-1">📍 {result.address}</p>
                      )}
                      {result.phone && (
                        <p className="text-sm text-gray-600 mb-1">📞 {result.phone}</p>
                      )}
                    </div>
                  </div>

                  {/* Additional details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-100">
                    {result.web_site && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase">Website</span>
                        <a 
                          href={result.web_site} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="block text-sm text-blue-600 hover:underline truncate"
                        >
                          {result.web_site}
                        </a>
                      </div>
                    )}
                    {result.latitude && result.longtitude && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase">Coordinates</span>
                        <a 
                          href={`https://www.google.com/maps?q=${result.latitude},${result.longtitude}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-sm text-blue-600 hover:underline"
                        >
                          {result.latitude.toFixed(6)}, {result.longtitude.toFixed(6)}
                        </a>
                      </div>
                    )}
                    {result.price_range && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase">Price Range</span>
                        <p className="text-sm text-gray-900">{result.price_range}</p>
                      </div>
                    )}
                    {result.status && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase">Status</span>
                        <p className="text-sm text-gray-900">{result.status}</p>
                      </div>
                    )}
                  </div>

                  {/* Reviews preview */}
                  {result.user_reviews && result.user_reviews.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <span className="text-xs font-medium text-gray-500 uppercase mb-2 block">Recent Reviews</span>
                      <div className="space-y-2">
                        {result.user_reviews.slice(0, 2).map((review: any, reviewIdx: number) => (
                          <div key={reviewIdx} className="bg-gray-50 rounded p-3">
                            <div className="flex items-center gap-2 mb-1">
                              {review.ProfilePicture && (
                                <img src={review.ProfilePicture} alt={review.Name} className="w-6 h-6 rounded-full" />
                              )}
                              <span className="text-sm font-medium text-gray-900">{review.Name}</span>
                              {review.Rating > 0 && (
                                <span className="text-xs text-yellow-600">{'⭐'.repeat(review.Rating)}</span>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 line-clamp-2">{review.Description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* View on Google Maps link */}
                  {result.link && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <a 
                        href={result.link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View on Google Maps →
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
            {job.results.length > 10 && (
              <div className="px-4 py-3 bg-gray-50 text-sm text-gray-500 text-center border-t border-gray-200">
                Showing 10 of {job.results.length} results. Download JSON for complete data including all reviews, images, and details.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
