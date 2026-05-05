/**
 * Job Results Page
 * Displays paginated results table for a completed job
 */
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import * as jobService from '../services/jobService'
import { StatusBadge } from '../components/StatusBadge'
import { ProgressBar } from '../components/ProgressBar'
import { PaginationControls } from '../components/PaginationControls'
import { MapView } from '../components/MapView'

export function JobResultsPage() {
  const { id } = useParams()
  const [results, setResults] = useState([])
  const [jobDetails, setJobDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [activeTab, setActiveTab] = useState('table') // 'table' or 'map'
  const pageSize = 50

  // Fetch job details first to get location
  useEffect(() => {
    const fetchJobDetails = async () => {
      try {
        const data = await jobService.getJobStatus(id)
        setJobDetails(data)
      } catch (err) {
        console.error('Error fetching job details:', err)
      }
    }

    fetchJobDetails()
  }, [id])

  useEffect(() => {
    const fetchResults = async () => {
      setLoading(true)
      setError('')

      try {
        const data = await jobService.getJobResults(id, page, pageSize)
        setResults(data.items || [])
        setTotalPages(data.pages || 1)
        setTotalCount(data.total || 0)
      } catch (err) {
        setError('Failed to load results')
        console.error('Error fetching results:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [id, page])

  const formatRating = (rating) => {
    if (!rating) return 'N/A'
    return `${parseFloat(rating).toFixed(1)} / 10`
  }

  const formatPrice = (price) => {
    if (!price) return 'N/A'
    // Assuming NPR currency
    return `NPR ${parseFloat(price).toLocaleString()}`
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">
            Results for {jobDetails?.location || 'unspecified location'}
          </h1>
          <Link to={`/jobs/${id}`} className="btn btn-secondary">
            Back to Job Status
          </Link>
        </div>
        <div className="card p-8">
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <p className="mt-4 text-sm text-slate-600">Loading results...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">
            Results for {jobDetails?.location || 'unspecified location'}
          </h1>
          <Link to={`/jobs/${id}`} className="btn btn-secondary">
            Back to Job Status
          </Link>
        </div>
        <div className="card p-8 text-center">
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Results for {jobDetails?.location || 'unspecified location'}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Viewing results for job #{id}
          </p>
        </div>
        <Link to={`/jobs/${id}`} className="btn btn-secondary">
          Back to Job Status
        </Link>
      </div>

      {/* Results Table */}
      <div className="card p-6">
        {/* Tab Navigation */}
        <div className="border-b border-slate-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('table')}
              className={`${
                activeTab === 'table'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
            >
              <svg
                className="inline-block w-5 h-5 mr-2 -mt-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              Table View
            </button>
            <button
              onClick={() => setActiveTab('map')}
              className={`${
                activeTab === 'map'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
            >
              <svg
                className="inline-block w-5 h-5 mr-2 -mt-1"
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
              Map View
            </button>
          </nav>
        </div>

        {results.length === 0 ? (
          <div className="text-center py-12">
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-slate-900">No results found</h3>
            <p className="mt-1 text-sm text-slate-500">
              This job did not return any results
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Table View */}
            {activeTab === 'table' && (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Name
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          City
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Address
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Rating
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Price
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Completeness
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-200">
                      {results.map((result) => (
                        <tr key={result.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 text-sm font-medium text-slate-900">
                            {result.name || 'N/A'}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-700">
                            {result.city || 'N/A'}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-700 max-w-xs truncate">
                            {result.address || 'N/A'}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-700">
                            {formatRating(result.rating_overall)}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-700">
                            {formatPrice(result.price_min)}
                          </td>
                          <td className="px-4 py-3">
                            <div className="w-32">
                              <ProgressBar percentage={result.data_completeness || 0} />
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge status={result.status} />
                          </td>
                          <td className="px-4 py-3">
                            <Link
                              to={`/results/${result.id}`}
                              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                            >
                              View Details
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <PaginationControls
                  currentPage={page}
                  totalPages={totalPages}
                  totalCount={totalCount}
                  onPageChange={setPage}
                />
              </>
            )}

            {/* Map View */}
            {activeTab === 'map' && <MapView results={results} height={600} />}
          </div>
        )}
      </div>
    </div>
  )
}
