/**
 * Admin Panel Page
 * Comprehensive results table with filtering, sorting, pagination, inline editing, and validation
 */
import { useState, useEffect, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender
} from '@tanstack/react-table'
import * as adminService from '../services/adminService'
import * as jobService from '../services/jobService'
import { StatusBadge } from '../components/StatusBadge'
import { ProgressBar } from '../components/ProgressBar'
import { PaginationControls } from '../components/PaginationControls'
import { ExportButton } from '../components/ExportButton'
import { BulkActionBar } from '../components/BulkActionBar'

// Inline Edit Cell Component
function EditableCell({ value, rowId, fieldName, onSave, isEditable }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(value || '')
  const [isSaving, setIsSaving] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isEditing])

  const handleSave = async () => {
    if (editValue === (value || '')) {
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    try {
      await onSave(rowId, fieldName, editValue || null)
      setIsEditing(false)
    } catch (error) {
      console.error('Error saving:', error)
      setEditValue(value || '')
    } finally {
      setIsSaving(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      setEditValue(value || '')
      setIsEditing(false)
    }
  }

  if (!isEditable) {
    return <div className="text-slate-700">{value || 'N/A'}</div>
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        disabled={isSaving}
        className="w-full px-2 py-1 text-sm border border-primary-500 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
      />
    )
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className="cursor-pointer hover:bg-slate-100 px-2 py-1 rounded transition-colors"
      title="Click to edit"
    >
      {value || <span className="text-slate-400 italic">Click to add</span>}
    </div>
  )
}

// Action Buttons Component
function ActionButtons({ result, onApprove, onReject, onSendToValidated, isProcessing }) {
  const canApprove = result.status === 'PENDING' || result.status === 'REJECTED'
  const canReject = result.status === 'PENDING' || result.status === 'APPROVED'
  const canSendToValidated = result.status === 'APPROVED'

  return (
    <div className="flex gap-2">
      {canApprove && (
        <button
          onClick={() => onApprove(result.id)}
          disabled={isProcessing}
          className="px-3 py-1 text-xs font-medium text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Approve this result"
        >
          Approve
        </button>
      )}
      {canReject && (
        <button
          onClick={() => onReject(result.id)}
          disabled={isProcessing}
          className="px-3 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Reject this result"
        >
          Reject
        </button>
      )}
      {canSendToValidated && (
        <button
          onClick={() => onSendToValidated(result.id)}
          disabled={isProcessing}
          className="px-3 py-1 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Send to validated results"
        >
          Send to Validated
        </button>
      )}
    </div>
  )
}

export function AdminPage() {
  // Data state
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  
  // Pagination state
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const pageSize = 50
  
  // Filter state
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  
  // Sort state
  const [sortBy, setSortBy] = useState('created_at')
  
  // Processing state
  const [processingIds, setProcessingIds] = useState(new Set())
  
  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState(new Set())
  
  // Bulk action processing state
  const [isBulkProcessing, setIsBulkProcessing] = useState(false)
  
  // Export state
  const [isExporting, setIsExporting] = useState(false)
  
  // Categories for dropdown
  const [categories, setCategories] = useState([])
  // Sources lookup map
  const [sourcesMap, setSourcesMap] = useState({})

  // Toast notification
  const showToast = (message, type = 'success') => {
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

  // Fetch categories on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await jobService.getCategories()
        setCategories(Array.isArray(data?.items) ? data.items : [])
      } catch (err) {
        console.error('Error fetching categories:', err)
        setCategories([])
      }
    }
    fetchCategories()
  }, [])

  // Fetch sources for all categories on mount
  useEffect(() => {
    const fetchAllSources = async () => {
      try {
        const data = await jobService.getCategories()
        const cats = Array.isArray(data?.items) ? data.items : []
        
        const sourcesLookup = {}
        for (const category of cats) {
          try {
            const sources = await jobService.getSourcesForCategory(category.id)
            if (Array.isArray(sources)) {
              sources.forEach(source => {
                sourcesLookup[source.id] = source.display_name || source.name
              })
            }
          } catch (err) {
            console.error(`Error fetching sources for category ${category.id}:`, err)
          }
        }
        setSourcesMap(sourcesLookup)
      } catch (err) {
        console.error('Error fetching sources:', err)
      }
    }
    fetchAllSources()
  }, [])

  // Fetch results when filters or pagination change
  useEffect(() => {
    const fetchResults = async () => {
      setLoading(true)
      setError('')

      try {
        const params = {
          page,
          page_size: pageSize,
          sort_by: sortBy
        }

        if (statusFilter) params.status = statusFilter
        if (categoryFilter) params.category_id = parseInt(categoryFilter)
        if (cityFilter) params.city = cityFilter

        const data = await adminService.getAdminResults(params)
        setResults(data.items || [])
        setTotalPages(data.pages || 1)
        setTotalCount(data.total || 0)
        
        // Clear selection when results change
        setSelectedIds(new Set())
      } catch (err) {
        setError('Failed to load admin results')
        console.error('Error fetching admin results:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [page, statusFilter, categoryFilter, cityFilter, sortBy])

  // Handle inline edit save
  const handleInlineEdit = async (resultId, fieldName, fieldValue) => {
    try {
      await adminService.inlineEditResult(resultId, fieldName, fieldValue)
      
      // Update local state
      setResults(prevResults =>
        prevResults.map(result =>
          result.id === resultId
            ? { ...result, [fieldName]: fieldValue }
            : result
        )
      )
      
      showToast(`Field '${fieldName}' updated successfully`, 'success')
    } catch (error) {
      showToast(`Failed to update field '${fieldName}'`, 'error')
      throw error
    }
  }

  // Handle approve
  const handleApprove = async (resultId) => {
    setProcessingIds(prev => new Set(prev).add(resultId))
    
    try {
      await adminService.approveResult(resultId)
      
      // Update local state
      setResults(prevResults =>
        prevResults.map(result =>
          result.id === resultId
            ? { ...result, status: 'APPROVED' }
            : result
        )
      )
      
      showToast('Result approved successfully', 'success')
    } catch (error) {
      showToast('Failed to approve result', 'error')
    } finally {
      setProcessingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(resultId)
        return newSet
      })
    }
  }

  // Handle reject
  const handleReject = async (resultId) => {
    setProcessingIds(prev => new Set(prev).add(resultId))
    
    try {
      await adminService.rejectResult(resultId)
      
      // Update local state
      setResults(prevResults =>
        prevResults.map(result =>
          result.id === resultId
            ? { ...result, status: 'REJECTED' }
            : result
        )
      )
      
      showToast('Result rejected successfully', 'success')
    } catch (error) {
      showToast('Failed to reject result', 'error')
    } finally {
      setProcessingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(resultId)
        return newSet
      })
    }
  }

  // Handle send to validated
  const handleSendToValidated = async (resultId) => {
    setProcessingIds(prev => new Set(prev).add(resultId))
    
    try {
      await adminService.sendToValidated(resultId)
      showToast('Result sent to validated_results successfully', 'success')
      
      // Optionally remove from list or mark as sent
      // For now, just show success message
    } catch (error) {
      showToast('Failed to send result to validated_results', 'error')
    } finally {
      setProcessingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(resultId)
        return newSet
      })
    }
  }

  // Handle export
  const handleExport = async (format) => {
    setIsExporting(true)
    
    try {
      // Build filters object
      const filters = {}
      if (statusFilter) filters.status = statusFilter
      if (categoryFilter) filters.category_id = parseInt(categoryFilter)
      if (cityFilter) filters.city = cityFilter
      if (sortBy) filters.sort_by = sortBy
      
      // Call export API
      const blob = await adminService.exportResults(format, filters)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `results_${new Date().toISOString().split('T')[0]}.${format}`
      document.body.appendChild(link)
      link.click()
      
      // Cleanup
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      showToast(`Export completed successfully (${format.toUpperCase()})`, 'success')
    } catch (error) {
      console.error('Export error:', error)
      const errorMessage = error.response?.data?.detail || 'Failed to export results'
      showToast(errorMessage, 'error')
    } finally {
      setIsExporting(false)
    }
  }

  // Handle select all toggle
  const handleSelectAll = () => {
    if (selectedIds.size === results.length) {
      // Deselect all
      setSelectedIds(new Set())
    } else {
      // Select all
      setSelectedIds(new Set(results.map(r => r.id)))
    }
  }

  // Handle individual row selection
  const handleSelectRow = (resultId) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(resultId)) {
        newSet.delete(resultId)
      } else {
        newSet.add(resultId)
      }
      return newSet
    })
  }

  // Handle bulk approve
  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return
    
    setIsBulkProcessing(true)
    
    try {
      const idsArray = Array.from(selectedIds)
      const response = await adminService.bulkActionResults(idsArray, 'approve')
      
      // Update local state
      setResults(prevResults =>
        prevResults.map(result =>
          selectedIds.has(result.id)
            ? { ...result, status: 'APPROVED' }
            : result
        )
      )
      
      // Clear selection
      setSelectedIds(new Set())
      
      showToast(`${response.processed} result(s) approved successfully`, 'success')
    } catch (error) {
      console.error('Bulk approve error:', error)
      showToast('Failed to approve selected results', 'error')
    } finally {
      setIsBulkProcessing(false)
    }
  }

  // Handle bulk reject
  const handleBulkReject = async () => {
    if (selectedIds.size === 0) return
    
    setIsBulkProcessing(true)
    
    try {
      const idsArray = Array.from(selectedIds)
      const response = await adminService.bulkActionResults(idsArray, 'reject')
      
      // Update local state
      setResults(prevResults =>
        prevResults.map(result =>
          selectedIds.has(result.id)
            ? { ...result, status: 'REJECTED' }
            : result
        )
      )
      
      // Clear selection
      setSelectedIds(new Set())
      
      showToast(`${response.processed} result(s) rejected successfully`, 'success')
    } catch (error) {
      console.error('Bulk reject error:', error)
      showToast('Failed to reject selected results', 'error')
    } finally {
      setIsBulkProcessing(false)
    }
  }

  // Define table columns
  const columns = useMemo(
    () => [
      {
        id: 'select',
        header: () => (
          <input
            type="checkbox"
            checked={selectedIds.size === results.length && results.length > 0}
            onChange={handleSelectAll}
            className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
          />
        ),
        cell: (info) => (
          <input
            type="checkbox"
            checked={selectedIds.has(info.row.original.id)}
            onChange={() => handleSelectRow(info.row.original.id)}
            className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
          />
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'name',
        header: 'Name',
        cell: (info) => (
          <EditableCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="name"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'city',
        header: 'City',
        cell: (info) => (
          <EditableCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="city"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'address',
        header: 'Address',
        cell: (info) => (
          <EditableCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="address"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'phone_primary',
        header: 'Phone',
        cell: (info) => (
          <EditableCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="phone_primary"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'phone_secondary',
        header: 'Phone 2',
        cell: (info) => (
          <EditableCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="phone_secondary"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'email',
        header: 'Email',
        cell: (info) => (
          <EditableCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="email"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'website',
        header: 'Website',
        cell: (info) => {
          const website = info.getValue()
          return website ? (
            <a 
              href={website} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-800 underline text-sm truncate block max-w-xs"
              title={website}
            >
              {website}
            </a>
          ) : (
            <EditableCell
              value=""
              rowId={info.row.original.id}
              fieldName="website"
              onSave={handleInlineEdit}
              isEditable={true}
            />
          )
        }
      },
      {
        accessorKey: 'description_short',
        header: 'Description',
        cell: (info) => {
          const desc = info.getValue()
          const truncated = desc && desc.length > 60 ? desc.substring(0, 60) + '...' : desc
          return (
            <div 
              className="text-slate-700 text-sm max-w-xs truncate"
              title={desc || ''}
            >
              {truncated || 'N/A'}
            </div>
          )
        }
      },
      {
        accessorKey: 'latitude',
        header: 'Latitude',
        cell: (info) => {
          const lat = info.getValue()
          return (
            <div className="text-slate-700 font-mono text-xs">
              {lat !== null && lat !== undefined ? lat.toFixed(4) : 'N/A'}
            </div>
          )
        }
      },
      {
        accessorKey: 'longitude',
        header: 'Longitude',
        cell: (info) => {
          const lng = info.getValue()
          return (
            <div className="text-slate-700 font-mono text-xs">
              {lng !== null && lng !== undefined ? lng.toFixed(4) : 'N/A'}
            </div>
          )
        }
      },
      {
        accessorKey: 'category_id',
        header: 'Category',
        cell: (info) => {
          const categoryId = info.getValue()
          const category = categories.find(c => c.id === categoryId)
          return (
            <div className="text-slate-700">
              {category?.display_name || 'Unknown'}
            </div>
          )
        }
      },
      {
        accessorKey: 'source_id',
        header: 'Source',
        cell: (info) => (
          <div className="text-slate-700">
            {sourcesMap[info.getValue()] || 'Unknown'}
          </div>
        )
      },
      {
        accessorKey: 'rating_overall',
        header: 'Rating',
        cell: (info) => (
          <EditableCell
            value={info.getValue() ? String(info.getValue()) : ''}
            rowId={info.row.original.id}
            fieldName="rating_overall"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'price_min',
        header: 'Price',
        cell: (info) => (
          <EditableCell
            value={info.getValue() ? String(info.getValue()) : ''}
            rowId={info.row.original.id}
            fieldName="price_min"
            onSave={handleInlineEdit}
            isEditable={true}
          />
        )
      },
      {
        accessorKey: 'data_completeness',
        header: () => (
          <button
            onClick={() => handleSortChange('data_completeness')}
            className="flex items-center gap-1 hover:text-slate-900"
          >
            Completeness
            {sortBy === 'data_completeness' && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </button>
        ),
        cell: (info) => (
          <div className="w-32">
            <ProgressBar percentage={info.getValue() || 0} />
          </div>
        )
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: (info) => {
          const row = info.row.original
          const isMerged = row.merged_from_sources && row.merged_from_sources.length >= 2
          return (
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={info.getValue()} />
              {isMerged && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {row.merged_from_sources.length} sources
                </span>
              )}
            </div>
          )
        }
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: (info) => (
          <ActionButtons
            result={info.row.original}
            onApprove={handleApprove}
            onReject={handleReject}
            onSendToValidated={handleSendToValidated}
            isProcessing={processingIds.has(info.row.original.id)}
          />
        )
      }
    ],
    [categories, sourcesMap, sortBy, processingIds, selectedIds, results.length, handleSelectAll, handleSelectRow]
  )

  // Initialize TanStack Table with manual pagination
  const table = useReactTable({
    data: results,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    manualPagination: true,
    pageCount: totalPages
  })

  // Handle sort change
  const handleSortChange = (field) => {
    setSortBy(field)
    setPage(1)
  }

  // Handle filter clear
  const handleClearFilters = () => {
    setStatusFilter('')
    setCategoryFilter('')
    setCityFilter('')
    setSortBy('created_at')
    setPage(1)
  }

  // Check if any filters are active
  const hasActiveFilters = statusFilter || categoryFilter || cityFilter || sortBy !== 'created_at'

  if (loading && results.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-slate-900">Admin Panel</h1>
        <div className="card p-8">
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <p className="mt-4 text-sm text-slate-600">Loading results...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Panel</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage and review all scraped results
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/admin/sources" className="btn btn-primary">
            Manage Sources
          </Link>
          <Link to="/admin/users" className="btn btn-secondary">
            Manage Users
          </Link>
          <Link to="/admin/monitoring" className="btn btn-secondary">
            Monitoring
          </Link>
          <Link to="/admin/healing" className="btn btn-secondary">
            🔧 Self-Healing
          </Link>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="card p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Status Filter */}
          <div>
            <label htmlFor="status-filter" className="block text-sm font-medium text-slate-700 mb-1">
              Status
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="input"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label htmlFor="category-filter" className="block text-sm font-medium text-slate-700 mb-1">
              Category
            </label>
            <select
              id="category-filter"
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value)
                setPage(1)
              }}
              className="input"
            >
              <option value="">All Categories</option>
              {Array.isArray(categories) && categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.display_name}
                </option>
              ))}
            </select>
          </div>

          {/* City Filter */}
          <div>
            <label htmlFor="city-filter" className="block text-sm font-medium text-slate-700 mb-1">
              City
            </label>
            <input
              id="city-filter"
              type="text"
              value={cityFilter}
              onChange={(e) => {
                setCityFilter(e.target.value)
                setPage(1)
              }}
              placeholder="Search by city..."
              className="input"
            />
          </div>

          {/* Clear Filters Button */}
          <div className="flex items-end">
            <button
              onClick={handleClearFilters}
              disabled={!hasActiveFilters}
              className="btn btn-secondary w-full disabled:opacity-50"
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Active Filters Display */}
        {hasActiveFilters && (
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="text-sm text-slate-600">Active filters:</span>
            {statusFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Status: {statusFilter}
              </span>
            )}
            {categoryFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Category: {categories.find(c => c.id === parseInt(categoryFilter))?.display_name || categoryFilter}
              </span>
            )}
            {cityFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                City: {cityFilter}
              </span>
            )}
            {sortBy !== 'created_at' && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Sort: {sortBy === 'data_completeness' ? 'Completeness' : 'Created At'}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Results Table */}
      <div className="card p-6">
        {/* Export Button */}
        <div className="mb-4 flex justify-between items-center">
          <div className="text-sm text-slate-600">
            {totalCount > 0 && `${totalCount} result${totalCount !== 1 ? 's' : ''} found`}
          </div>
          <ExportButton
            onExport={handleExport}
            disabled={totalCount === 0}
            isExporting={isExporting}
          />
        </div>

        {error ? (
          <div className="text-center py-12">
            <p className="text-red-600">{error}</p>
          </div>
        ) : results.length === 0 ? (
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
              Try adjusting your filters or check back later
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Bulk Action Bar */}
            <BulkActionBar
              selectedCount={selectedIds.size}
              onApprove={handleBulkApprove}
              onReject={handleBulkReject}
              onClear={() => setSelectedIds(new Set())}
              isProcessing={isBulkProcessing}
            />

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <th
                          key={header.id}
                          className="px-4 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider"
                        >
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3 text-sm">
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </td>
                      ))}
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
          </div>
        )}
      </div>
    </div>
  )
}
