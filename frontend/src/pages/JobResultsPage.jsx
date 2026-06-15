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
  const [filterType, setFilterType] = useState('all') // 'all', 'new', 'updated', 'duplicates'
  const [filterStats, setFilterStats] = useState({ all: 0, new: 0, updated: 0, duplicates: 0 })
  const [duplicateDetailModal, setDuplicateDetailModal] = useState(null)
  const [loadingDuplicateDetail, setLoadingDuplicateDetail] = useState(false)
  const pageSize = 50

  // Fetch all filter stats on initial load
  useEffect(() => {
    const fetchFilterStats = async () => {
      try {
        const [allData, newData, updatedData, duplicatesData] = await Promise.all([
          jobService.getJobResults(id, 1, 1, 'all'),
          jobService.getJobResults(id, 1, 1, 'new'),
          jobService.getJobResults(id, 1, 1, 'updated'),
          jobService.getJobResults(id, 1, 1, 'duplicates')
        ])
        
        setFilterStats({
          all: allData.total || 0,
          new: newData.total || 0,
          updated: updatedData.total || 0,
          duplicates: duplicatesData.total || 0
        })
      } catch (err) {
        console.error('Error fetching filter stats:', err)
      }
    }

    fetchFilterStats()
  }, [id])

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
        const data = await jobService.getJobResults(id, page, pageSize, filterType)
        setResults(data.items || [])
        setTotalPages(data.pages || 1)
        setTotalCount(data.total || 0)
        
        // Update filter stats
        setFilterStats(prev => ({
          ...prev,
          [filterType]: data.total || 0
        }))
      } catch (err) {
        setError('Failed to load results')
        console.error('Error fetching results:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [id, page, filterType])

  const formatRating = (rating) => {
    if (!rating) return 'N/A'
    return `${parseFloat(rating).toFixed(1)} / 10`
  }

  const formatPrice = (price) => {
    if (!price) return 'N/A'
    // Assuming NPR currency
    return `NPR ${parseFloat(price).toLocaleString()}`
  }

  const handleShowDuplicateDetail = async (resultId) => {
    setLoadingDuplicateDetail(true)
    try {
      const history = await jobService.getDuplicateHistory(resultId)
      setDuplicateDetailModal(history)
    } catch (err) {
      console.error('Failed to load duplicate history:', err)
      // Show error toast
      const toast = document.createElement('div')
      toast.className = 'fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 bg-red-600'
      toast.textContent = 'Failed to load duplicate history'
      document.body.appendChild(toast)
      setTimeout(() => toast.remove(), 3000)
    } finally {
      setLoadingDuplicateDetail(false)
    }
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
        {/* Filter Buttons */}
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => { setFilterType('all'); setPage(1); }}
            className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
              filterType === 'all'
                ? 'bg-slate-600 text-white border-slate-600'
                : 'bg-white text-slate-600 border-slate-300 hover:border-slate-400'
            }`}
          >
            All ({filterStats.all})
          </button>
          <button
            onClick={() => { setFilterType('new'); setPage(1); }}
            className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
              filterType === 'new'
                ? 'bg-green-600 text-white border-green-600'
                : 'bg-white text-green-600 border-green-300 hover:border-green-400'
            }`}
          >
            New ({filterStats.new})
          </button>
          <button
            onClick={() => { setFilterType('updated'); setPage(1); }}
            className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
              filterType === 'updated'
                ? 'bg-orange-600 text-white border-orange-600'
                : 'bg-white text-orange-600 border-orange-300 hover:border-orange-400'
            }`}
          >
            Updated ({filterStats.updated})
          </button>
          <button
            onClick={() => { setFilterType('duplicates'); setPage(1); }}
            className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
              filterType === 'duplicates'
                ? 'bg-red-600 text-white border-red-600'
                : 'bg-white text-red-600 border-red-300 hover:border-red-400'
            }`}
          >
            Duplicates ({filterStats.duplicates})
          </button>
        </div>

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
                          Source
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
                            <div className="flex items-center gap-2">
                              <span>{result.name || 'N/A'}</span>
                              {result.is_new_record === false && result.is_updated_record === false && (
                                <button
                                  onClick={() => handleShowDuplicateDetail(result.id)}
                                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 hover:bg-red-200 transition-colors cursor-pointer"
                                  title="Click to see original job that scraped this record"
                                >
                                  🔁 Duplicate
                                  <svg className="ml-1 w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                </button>
                              )}
                              {result.is_new_record === true && (
                                <span 
                                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                                  title="This is a new record - first time scraped"
                                >
                                  ✨ New
                                </span>
                              )}
                              {result.is_updated_record === true && (
                                <span 
                                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800"
                                  title="This record was updated with new data"
                                >
                                  📝 Updated
                                </span>
                              )}
                            </div>
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
                            {result.scraper_source ? (
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                result.scraper_source === 'go_scraper' 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-blue-100 text-blue-800'
                              }`}>
                                {result.scraper_source === 'go_scraper' ? '⚡ Go' : '🎭 ' + result.scraper_source}
                              </span>
                            ) : (
                              <span className="text-xs text-slate-400">Unknown</span>
                            )}
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

      {/* Duplicate Detail Modal */}
      {duplicateDetailModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-900">
                🔁 Duplicate Record Details
              </h3>
              <button
                onClick={() => setDuplicateDetailModal(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {duplicateDetailModal.is_duplicate ? (
              <div className="space-y-4">
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800 mb-2">
                    ⚠️ This record was already scraped in a previous job.
                  </p>
                  <p className="text-xs text-yellow-700">
                    It appears in this job's results for visibility, but was not saved as a new record.
                  </p>
                </div>
                
                <div>
                  <label className="text-xs font-medium text-slate-600">Original Job ID</label>
                  <p className="text-sm font-mono text-slate-900 mt-1">
                    #{duplicateDetailModal.original_job_id?.substring(0, 8)}...
                  </p>
                </div>
                
                <div>
                  <label className="text-xs font-medium text-slate-600">Original Scrape Date</label>
                  <p className="text-sm text-slate-900 mt-1">
                    {duplicateDetailModal.original_job_date 
                      ? new Date(duplicateDetailModal.original_job_date).toLocaleString()
                      : 'Unknown'}
                  </p>
                </div>
                
                <div>
                  <label className="text-xs font-medium text-slate-600">Original Job Location</label>
                  <p className="text-sm text-slate-900 mt-1">
                    {duplicateDetailModal.original_job_location || 'Unknown'}
                  </p>
                </div>
                
                <div className="flex gap-3 pt-3 border-t border-slate-200">
                  <Link
                    to={`/jobs/${duplicateDetailModal.original_job_id}`}
                    className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium text-center"
                    onClick={() => setDuplicateDetailModal(null)}
                  >
                    View Original Job
                  </Link>
                  <button
                    onClick={() => setDuplicateDetailModal(null)}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 text-sm font-medium"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800">
                  ✅ This is not a duplicate. This record was first scraped in this job.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
