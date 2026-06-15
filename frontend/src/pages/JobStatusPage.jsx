/**
 * Job Status Page
 * Real-time job monitoring with SSE and polling fallback
 */
import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import * as jobService from '../services/jobService'
import * as sseService from '../services/sseService'
import { StatusBadge } from '../components/StatusBadge'

// Cancel Button Component with double confirmation
function CancelButton({ jobId, onCancel }) {
  const [showFirstModal, setShowFirstModal] = useState(false)
  const [showSecondModal, setShowSecondModal] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)

  const handleFirstConfirm = () => {
    setShowFirstModal(false)
    setShowSecondModal(true)
  }

  const handleFinalCancel = async () => {
    setIsCancelling(true)
    try {
      await jobService.cancelJob(jobId)
      
      // Show success toast
      const toast = document.createElement('div')
      toast.className = 'fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 bg-green-600'
      toast.textContent = 'Job cancelled successfully. Partial results have been saved.'
      document.body.appendChild(toast)

      setTimeout(() => {
        toast.remove()
        setShowSecondModal(false)
        onCancel() // Refresh job status
      }, 2000)
    } catch (err) {
      setIsCancelling(false)
      
      // Show error toast
      const toast = document.createElement('div')
      toast.className = 'fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 bg-red-600'
      toast.textContent = err.response?.data?.detail || 'Failed to cancel job'
      document.body.appendChild(toast)

      setTimeout(() => {
        toast.remove()
      }, 3000)
    }
  }

  return (
    <>
      <button
        onClick={() => setShowFirstModal(true)}
        className="btn bg-red-600 hover:bg-red-700 text-white flex items-center gap-2"
        aria-label="Cancel job"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
        Cancel Job
      </button>

      {/* First Confirmation Modal */}
      {showFirstModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-slate-900 mb-4">⚠️ Cancel Scraping Job?</h3>
            <p className="text-slate-700 mb-4">
              Are you sure you want to cancel this job?
            </p>
            <p className="text-sm text-slate-600 mb-6">
              Progress will be lost but results collected so far will be saved.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowFirstModal(false)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
              >
                No, Continue Job
              </button>
              <button
                onClick={handleFirstConfirm}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
              >
                Yes, Cancel Job
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Second Confirmation Modal */}
      {showSecondModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-red-600 mb-4">🛑 Final Confirmation</h3>
            <p className="text-slate-900 font-semibold mb-2">
              This action cannot be undone!
            </p>
            <p className="text-slate-700 mb-6">
              The job will be marked as CANCELLED and the scraping process will stop immediately.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowSecondModal(false)}
                disabled={isCancelling}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Go Back
              </button>
              <button
                onClick={handleFinalCancel}
                disabled={isCancelling}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold disabled:opacity-50 flex items-center gap-2"
              >
                {isCancelling ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Cancelling...
                  </>
                ) : (
                  'Confirm Cancellation'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export function JobStatusPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [jobStatus, setJobStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [usePolling, setUsePolling] = useState(true)  // Start with polling enabled
  const [isRetrying, setIsRetrying] = useState(false)
  const eventSourceRef = useRef(null)
  const pollingIntervalRef = useRef(null)
  const sseInitializedRef = useRef(false)  // Track if SSE was already set up
  
  // Extract status for stable dependency
  const currentStatus = jobStatus?.status

  // Fetch initial job status
  useEffect(() => {
    const fetchInitialStatus = async () => {
      try {
        const data = await jobService.getJobStatus(id)
        setJobStatus(data)
        setLoading(false)
      } catch (err) {
        setError('Failed to load job status')
        console.error('Error fetching job status:', err)
        setLoading(false)
      }
    }

    fetchInitialStatus()
  }, [id])

  // Set up SSE connection with polling fallback
  useEffect(() => {
    // Only set up SSE if we have job data and job is running/queued
    if (!jobStatus) return
    if (jobStatus.status === 'DONE' || jobStatus.status === 'FAILED') return
    
    // Don't create SSE if polling is already active
    if (usePolling) return
    
    // Don't create duplicate SSE connections
    if (eventSourceRef.current) return

    // Try SSE first
    const handleSSEMessage = (data) => {
      // Merge SSE updates with existing job data to preserve fields like location
      setJobStatus(prev => ({ ...prev, ...data }))
    }

    const handleSSEError = (_error) => {
      console.log('SSE failed, falling back to polling')
      setUsePolling(true)
    }

    try {
      eventSourceRef.current = sseService.createJobStatusStream(
        id,
        handleSSEMessage,
        handleSSEError
      )
    } catch (err) {
      console.log('SSE not supported, using polling')
      setUsePolling(true)
    }

    // Cleanup SSE on unmount
    return () => {
      if (eventSourceRef.current) {
        sseService.closeStream(eventSourceRef.current)
        eventSourceRef.current = null
      }
    }
  }, [id, currentStatus, usePolling])  // Use extracted status value for stable dependency

  // Polling fallback
  useEffect(() => {
    if (!usePolling || !jobStatus) return

    // Don't poll if job is done or failed
    if (jobStatus.status === 'DONE' || jobStatus.status === 'FAILED') {
      // Clear any existing interval
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      return
    }

    const pollStatus = async () => {
      try {
        const data = await jobService.getJobStatus(id)
        setJobStatus(data)
      } catch (err) {
        console.error('Polling error:', err)
      }
    }

    // Clear any existing interval before creating new one
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    // Poll every 2 seconds for faster phase updates
    pollingIntervalRef.current = setInterval(pollStatus, 2000)

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [id, usePolling, currentStatus])  // Use extracted status value for stable dependency

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleRetry = async () => {
    setIsRetrying(true)
    try {
      const response = await jobService.retryJob(id)
      
      // Show success toast
      const toast = document.createElement('div')
      toast.className = 'fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 bg-green-600'
      toast.textContent = 'Job retried successfully. Redirecting to new job...'
      document.body.appendChild(toast)

      // Wait 2 seconds before redirecting
      setTimeout(() => {
        toast.remove()
        navigate(`/jobs/${response.id}`)
      }, 2000)
    } catch (err) {
      setIsRetrying(false)
      
      // Show error toast
      const toast = document.createElement('div')
      toast.className = 'fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 bg-red-600'
      toast.textContent = err.response?.data?.detail || 'Failed to retry job'
      document.body.appendChild(toast)

      setTimeout(() => {
        toast.remove()
      }, 3000)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        <p className="mt-4 text-sm text-slate-600">Loading job status...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-600">{error}</p>
        <Link to="/dashboard" className="btn btn-primary mt-4 inline-block">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  if (!jobStatus) {
    return (
      <div className="card p-8 text-center">
        <p className="text-slate-600">Job not found</p>
        <Link to="/dashboard" className="btn btn-primary mt-4 inline-block">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Job Status</h1>
          <p className="mt-1 text-sm text-slate-600">
            Monitoring job #{jobStatus.id}
          </p>
          <p className="mt-1 text-base font-medium text-slate-700">
            Location: {jobStatus.location || 'Not specified'}
          </p>
        </div>
        <Link to="/dashboard" className="btn btn-secondary">
          Back to Dashboard
        </Link>
      </div>

      {/* Status Card */}
      <div className="card p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Job ID */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Job ID</label>
            <p className="text-lg font-semibold text-slate-900">#{jobStatus.id}</p>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
            <StatusBadge status={jobStatus.status} />
          </div>

          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Location</label>
            <p className="text-slate-900">{jobStatus.location || 'N/A'}</p>
          </div>

          {/* Created At */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Created At</label>
            <p className="text-slate-900">{formatDate(jobStatus.created_at)}</p>
          </div>

          {/* Started At */}
          {jobStatus.started_at && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Started At</label>
              <p className="text-slate-900">{formatDate(jobStatus.started_at)}</p>
            </div>
          )}

          {/* Completed At */}
          {jobStatus.completed_at && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Completed At</label>
              <p className="text-slate-900">{formatDate(jobStatus.completed_at)}</p>
            </div>
          )}

          {/* Result Count */}
          {jobStatus.status === 'DONE' && jobStatus.result_count !== undefined && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Results Found</label>
              <p className="text-lg font-semibold text-green-600">{jobStatus.result_count}</p>
            </div>
          )}
        </div>

        {/* Statistics Section */}
        {jobStatus.status === 'DONE' && jobStatus.statistics && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="text-sm font-semibold text-blue-900 mb-3">📊 Scraping Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-blue-700 font-medium">Total Scraped</p>
                <p className="text-2xl font-bold text-blue-900">{jobStatus.statistics.raw_scraped || 0}</p>
              </div>
              <div>
                <p className="text-xs text-green-700 font-medium">New Records</p>
                <p className="text-2xl font-bold text-green-600">{jobStatus.statistics.new_records || 0}</p>
              </div>
              <div>
                <p className="text-xs text-orange-700 font-medium">Duplicates</p>
                <p className="text-2xl font-bold text-orange-600">{jobStatus.statistics.duplicates || 0}</p>
              </div>
              <div className="relative group">
                <p className="text-xs text-purple-700 font-medium flex items-center gap-1">
                  Enhanced
                  <span className="inline-block cursor-help">ℹ️</span>
                </p>
                <p className="text-2xl font-bold text-purple-600">{jobStatus.statistics.updated_records || 0}</p>
                {/* Tooltip */}
                <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block w-64 p-2 bg-slate-800 text-white text-xs rounded shadow-lg z-10">
                  Existing records from previous jobs that were improved with better data (e.g., added coordinates, reviews, or contact info)
                </div>
              </div>
            </div>
            
            {/* By Source Breakdown */}
            {jobStatus.statistics.by_source_name && Object.keys(jobStatus.statistics.by_source_name).length > 0 && (
              <div className="mt-4 pt-4 border-t border-blue-200">
                <p className="text-xs text-blue-700 font-medium mb-2">Results by Source:</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(jobStatus.statistics.by_source_name).map(([sourceName, count]) => (
                    <span key={sourceName} className="px-3 py-1 bg-white border border-blue-300 rounded-full text-xs font-medium text-blue-900">
                      {sourceName}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error Message */}
        {jobStatus.status === 'FAILED' && jobStatus.error_message && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm font-medium text-red-800">Error:</p>
            <p className="text-sm text-red-700 mt-1">{jobStatus.error_message}</p>
          </div>
        )}

        {/* Progress Indicator for RUNNING status */}
        {jobStatus.status === 'RUNNING' && (
          <div className="mt-6">
            {/* Live Progress Panel */}
            {jobStatus.statistics && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg mb-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-3">🔄 Live Progress</h3>
                
                {/* Progress Bar with Percentage */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-blue-700 mb-1">
                    <span>Progress</span>
                    <span className="font-semibold">{jobStatus.statistics.progress_percentage || 0}%</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
                    <div 
                      className="bg-blue-600 h-3 rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                      style={{ width: `${jobStatus.statistics.progress_percentage || 0}%` }}
                    >
                      {jobStatus.statistics.progress_percentage >= 15 && (
                        <span className="text-xs font-bold text-white">
                          {jobStatus.statistics.progress_percentage}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Current Phase Message */}
                <div className="p-4 bg-white rounded-lg border border-blue-300">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="animate-pulse h-3 w-3 bg-blue-500 rounded-full" />
                      <p className="text-base font-medium text-blue-900">
                        {jobStatus.statistics.progress_message || jobStatus.scraping_progress || 'Processing...'}
                      </p>
                    </div>
                    <span className="text-xs text-blue-600 font-medium">Live</span>
                  </div>
                </div>
              </div>
            )}
            
            {/* Fallback Progress (if statistics not available) */}
            {!jobStatus.statistics && (
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="animate-spin h-4 w-4 border-2 border-primary-600 border-t-transparent rounded-full"/>
                  <span className="text-sm font-medium text-slate-700">
                    {jobStatus.scraping_progress || 'Scraping in progress...'}
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2.5 mb-2">
                  <div className="bg-primary-600 h-2.5 rounded-full animate-pulse" style={{ width: '75%' }}/>
                </div>
                <p className="text-xs text-slate-500">
                  Extracting data from {jobStatus.location || 'target location'}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Progress Indicator for QUEUED status */}
        {jobStatus.status === 'QUEUED' && (
          <div className="mt-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="animate-pulse h-4 w-4 bg-slate-400 rounded-full"/>
              <span className="text-sm font-medium text-slate-700">Job queued, waiting to start...</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2.5">
              <div className="bg-slate-400 h-2.5 rounded-full" style={{ width: '10%' }}/>
            </div>
          </div>
        )}

        {/* Progress Indicator for DONE status */}
        {jobStatus.status === 'DONE' && (
          <div className="mt-6">
            <div className="w-full bg-slate-200 rounded-full h-2.5 mb-2">
              <div className="bg-green-500 h-2.5 rounded-full transition-all duration-500" style={{ width: '100%' }}/>
            </div>
            <p className="text-sm text-green-600 font-medium">
              ✅ Complete — {jobStatus.statistics?.new_records || 0} new records added
              {jobStatus.statistics?.updated_records > 0 && `, ${jobStatus.statistics.updated_records} existing records enhanced`}
            </p>
          </div>
        )}

        {/* Retry Button */}
        {jobStatus.status === 'FAILED' && (
          <div className="mt-6">
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
              aria-label="Retry failed job"
            >
              {isRetrying ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Retrying...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Retry Job
                </>
              )}
            </button>
          </div>
        )}

        {/* Cancel Button */}
        {(jobStatus.status === 'QUEUED' || jobStatus.status === 'RUNNING') && (
          <div className="mt-6">
            <CancelButton jobId={id} onCancel={() => loadJob()} />
          </div>
        )}

        {/* View Results Button */}
        {jobStatus.status === 'DONE' && (
          <div className="mt-6">
            <button
              onClick={() => navigate(`/jobs/${id}/results`)}
              className="btn btn-primary"
            >
              View Results ({jobStatus.statistics?.new_records || 0} new)
            </button>
          </div>
        )}

        {/* Real-time indicator */}
        {(jobStatus.status === 'QUEUED' || jobStatus.status === 'RUNNING') && (
          <div className="mt-6 flex items-center text-sm text-slate-600">
            <div className="animate-pulse h-2 w-2 bg-green-500 rounded-full mr-2"></div>
            {usePolling ? 'Polling for updates...' : 'Real-time updates active'}
          </div>
        )}
      </div>
    </div>
  )
}
