/**
 * Source Manager Page
 * Admin page for managing source activation status
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

// ToggleSwitch Component
function ToggleSwitch({ enabled, onChange, disabled }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      disabled={disabled}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${enabled ? 'bg-primary-600' : 'bg-slate-300'}
      `}
      aria-label={enabled ? 'Disable source' : 'Enable source'}
    >
      <span
        className={`
          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          ${enabled ? 'translate-x-6' : 'translate-x-1'}
        `}
      />
    </button>
  )
}

export function SourceManagerPage() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updatingIds, setUpdatingIds] = useState(new Set())

  useEffect(() => {
    fetchSources()
  }, [])

  const fetchSources = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch('/api/v1/admin/sources', {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to fetch sources')
      }

      const data = await response.json()
      setSources(data)
    } catch (err) {
      setError('Failed to load sources')
      console.error('Error fetching sources:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async (sourceId, currentStatus) => {
    // Add to updating set to disable toggle during request
    setUpdatingIds(prev => new Set(prev).add(sourceId))

    try {
      const response = await fetch(`/api/v1/admin/sources/${sourceId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ is_active: !currentStatus })
      })

      if (!response.ok) {
        throw new Error('Failed to update source')
      }

      // Update local state
      setSources(prevSources =>
        prevSources.map(source =>
          source.id === sourceId
            ? { ...source, is_active: !currentStatus }
            : source
        )
      )

      // Show success toast (simple implementation)
      showToast('Source updated successfully', 'success')
    } catch (err) {
      console.error('Error updating source:', err)
      showToast('Failed to update source', 'error')
    } finally {
      // Remove from updating set
      setUpdatingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(sourceId)
        return newSet
      })
    }
  }

  const showToast = (message, type) => {
    // Simple toast implementation - could be replaced with a toast library
    const toast = document.createElement('div')
    toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${
      type === 'success' ? 'bg-green-600' : 'bg-red-600'
    }`
    toast.textContent = message
    document.body.appendChild(toast)

    setTimeout(() => {
      toast.remove()
    }, 3000)
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Source Manager</h1>
          <Link to="/admin" className="btn btn-secondary">
            Back to Admin Panel
          </Link>
        </div>
        <div className="card p-8">
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <p className="mt-4 text-sm text-slate-600">Loading sources...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Source Manager</h1>
          <Link to="/admin" className="btn btn-secondary">
            Back to Admin Panel
          </Link>
        </div>
        <div className="card p-8 text-center">
          <p className="text-red-600">{error}</p>
          <button onClick={fetchSources} className="btn btn-primary mt-4">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Source Manager</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage source activation status for all categories
          </p>
        </div>
        <Link to="/admin" className="btn btn-secondary">
          Back to Admin Panel
        </Link>
      </div>

      {/* Sources Table */}
      <div className="card p-6">
        {sources.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-slate-600">No sources found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Source Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {sources.map((source) => (
                  <tr key={source.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-900">
                        {source.display_name}
                      </div>
                      <div className="text-sm text-slate-500">{source.name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">
                      {source.category_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          source.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-slate-100 text-slate-800'
                        }`}
                      >
                        {source.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <ToggleSwitch
                        enabled={source.is_active}
                        onChange={() => handleToggle(source.id, source.is_active)}
                        disabled={updatingIds.has(source.id)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
