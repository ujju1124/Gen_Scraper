/**
 * Job History Table Component
 * Displays paginated list of user's scraping jobs with status badges
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import * as jobService from '../../services/jobService'
import { StatusBadge } from '../StatusBadge'

export function JobHistoryTable() {
  const [jobs, setJobs] = useState([])
  const [categories, setCategories] = useState({}) // Category lookup map
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const pageSize = 20
  const navigate = useNavigate()

  // Fetch categories once on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await jobService.getCategories()
        const categoryList = data.items || data
        
        // Create lookup map: { 1: "Hotels", 2: "Hostels", ... }
        const categoryMap = {}
        categoryList.forEach(cat => {
          categoryMap[cat.id] = cat.display_name
        })
        setCategories(categoryMap)
      } catch (err) {
        console.error('Error fetching categories:', err)
      }
    }

    fetchCategories()
  }, [])

  useEffect(() => {
    const fetchJobs = async () => {
      setLoading(true)
      setError('')
      
      try {
        const data = await jobService.getJobs(page, pageSize)
        setJobs(data.items || [])
        setTotalPages(data.pages || 1)
        setTotalCount(data.total || 0)
      } catch (err) {
        setError('Failed to load job history')
        console.error('Error fetching jobs:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchJobs()
  }, [page])

  const handleJobClick = (jobId) => {
    navigate(`/jobs/${jobId}`)
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p className="mt-2 text-sm text-slate-600">Loading jobs...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
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
        <h3 className="mt-2 text-sm font-medium text-slate-900">No jobs yet</h3>
        <p className="mt-1 text-sm text-slate-500">
          Create your first scraping job using the form above
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Job ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Category
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Location
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Created At
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {jobs.map((job) => (
              <tr
                key={job.id}
                className="hover:bg-slate-50 cursor-pointer"
                onClick={() => handleJobClick(job.id)}
              >
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900">
                  #{job.id}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-700">
                  {categories[job.category_id] || 'Unknown'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-700">
                  {job.location}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <StatusBadge status={job.status} />
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                  {formatDate(job.created_at)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleJobClick(job.id)
                    }}
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-200 pt-4">
          <div className="text-sm text-slate-600">
            Showing page {page} of {totalPages} ({totalCount} total jobs)
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
