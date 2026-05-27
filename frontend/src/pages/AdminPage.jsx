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
import EditableCellV2 from '../components/EditableCellV2'
import GlobalSaveBar from '../components/GlobalSaveBar'
import OpeningHoursCell from '../components/OpeningHoursCell'
import ExportDialog from '../components/ExportDialog'
import ColumnManager from '../components/ColumnManager'
import { useDragScroll } from '../hooks/useDragScroll'

// Default built-in column visibility
const DEFAULT_BUILTIN_VISIBILITY = {
  name: true, city: true, address: true, phone_primary: true, phone_secondary: false,
  email: true, website: true, description_short: false, latitude: false, longitude: false,
  category_id: true, source_name: false, scraper_source: false, thumbnail_url: false,
  images_count: true, amenities: false, opening_hours: true, rating_overall: true,
  review_count: false, price_min: false, price_max: false, currency: false,
  data_completeness: true, status: true, place_id: false
}

const BUILTIN_COLUMN_LABELS = {
  name: 'Name', city: 'City', address: 'Address', phone_primary: 'Phone',
  phone_secondary: 'Phone 2', email: 'Email', website: 'Website',
  description_short: 'Description', latitude: 'Latitude', longitude: 'Longitude',
  category_id: 'Category', source_name: 'Source', scraper_source: 'Scraper',
  thumbnail_url: 'Thumbnail URL', images_count: 'Images', amenities: 'Amenities',
  opening_hours: 'Hours', rating_overall: 'Rating', review_count: 'Reviews',
  price_min: 'Price Min', price_max: 'Price Max', currency: 'Currency',
  data_completeness: 'Completeness', status: 'Status', place_id: 'Place ID'
}

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
  const canSendToValidated = result.status === 'APPROVED' && !result.sent_to_validated

  return (
    <div className="flex gap-2 items-center min-w-[280px]">
      {canApprove && (
        <button
          onClick={() => onApprove(result.id)}
          disabled={isProcessing}
          className="inline-flex items-center justify-center px-3.5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-green-600 to-green-700 rounded-lg hover:from-green-700 hover:to-green-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
          title="Approve this result"
        >
          <svg className="w-3.5 h-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          Approve
        </button>
      )}
      {canReject && (
        <button
          onClick={() => onReject(result.id)}
          disabled={isProcessing}
          className="inline-flex items-center justify-center px-3.5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-red-600 to-red-700 rounded-lg hover:from-red-700 hover:to-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
          title="Reject this result"
        >
          <svg className="w-3.5 h-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Reject
        </button>
      )}
      {result.status === 'APPROVED' && (
        <>
          {canSendToValidated ? (
            <button
              onClick={() => onSendToValidated(result.id)}
              disabled={isProcessing}
              className="inline-flex items-center justify-center px-3.5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-lg hover:from-indigo-700 hover:to-indigo-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
              title="Send to validated results database"
            >
              <svg className="w-3.5 h-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Send to Validated
            </button>
          ) : (
            <div className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-emerald-700 bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-lg border border-emerald-300 shadow-sm">
              <svg className="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>Validated</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function AdminPage() {
  // Data state
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  
  // Drag scroll hook for table
  const tableScrollRef = useDragScroll()
  
  // Pagination state
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const pageSize = 50
  
  // Filter state
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [scraperSourceFilter, setScraperSourceFilter] = useState('')
  const [duplicateFilter, setDuplicateFilter] = useState('')
  const [completenessFilter, setCompletenessFilter] = useState('')
  const [hasPhoneFilter, setHasPhoneFilter] = useState('')
  const [hasWebsiteFilter, setHasWebsiteFilter] = useState('')
  const [hasRatingFilter, setHasRatingFilter] = useState('')
  const [hasOpeningHoursFilter, setHasOpeningHoursFilter] = useState('')
  const [dateFromFilter, setDateFromFilter] = useState('')
  const [dateToFilter, setDateToFilter] = useState('')
  
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
  const [showExportDialog, setShowExportDialog] = useState(false)

  // Feature 4: Column visibility + custom columns (persisted in localStorage)
  const [columnVisibility, setColumnVisibility] = useState(() => {
    try {
      const saved = localStorage.getItem('adminColumnVisibility')
      return saved ? { ...DEFAULT_BUILTIN_VISIBILITY, ...JSON.parse(saved) } : DEFAULT_BUILTIN_VISIBILITY
    } catch { return DEFAULT_BUILTIN_VISIBILITY }
  })
  // Feature 4: Custom columns - load from API (FIX 1)
  const [customColumns, setCustomColumns] = useState([])
  
  // Load custom columns from API on mount
  useEffect(() => {
    const loadCustomColumns = async () => {
      try {
        const response = await adminService.getColumnDefinitions()
        // Transform API response {id, name, display_name} to {key, label, id}
        const transformed = response.map(col => ({
          id: col.id,
          key: col.name,
          label: col.display_name
        }))
        setCustomColumns(transformed)
      } catch (err) {
        console.error('Failed to load custom columns:', err)
        // Fallback to localStorage if API fails
        try {
          const saved = localStorage.getItem('adminCustomColumns')
          if (saved) setCustomColumns(JSON.parse(saved))
        } catch {}
      }
    }
    loadCustomColumns()
  }, [])
  const [showColumnManager, setShowColumnManager] = useState(false)

  const handleToggleColumn = (key) => {
    setColumnVisibility(prev => {
      const next = { ...prev, [key]: !prev[key] }
      localStorage.setItem('adminColumnVisibility', JSON.stringify(next))
      return next
    })
  }
  const handleResetDefaults = () => {
    setColumnVisibility(DEFAULT_BUILTIN_VISIBILITY)
    localStorage.setItem('adminColumnVisibility', JSON.stringify(DEFAULT_BUILTIN_VISIBILITY))
  }
  const handleAddCustomColumn = async (label, isTemp = false) => {
    const key = 'custom_' + label.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
    try {
      const newCol = await adminService.createColumnDefinition(key, label, isTemp)
      // Transform API response to match expected format
      setCustomColumns(prev => [...prev, {
        id: newCol.id,
        key: newCol.name,
        label: newCol.display_name
      }])
    } catch (err) {
      console.error('Failed to add custom column:', err)
      throw err
    }
  }
  
  const handleRemoveCustomColumn = async (colId) => {
    try {
      await adminService.deleteColumnDefinition(colId)
      setCustomColumns(prev => prev.filter(c => c.id !== colId))
    } catch (err) {
      console.error('Failed to remove custom column:', err)
    }
  }

  // Feature 3: pending changes buffer  { [rowId]: { [fieldName]: { value, isTemporary } } }
  const [pendingChanges, setPendingChanges] = useState({})
  const [isSavingAll, setIsSavingAll] = useState(false)
  
  // Categories for dropdown
  const [categories, setCategories] = useState([])
  // Sources for dropdown
  const [sources, setSources] = useState([])
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

  // Fetch sources for dropdown on mount
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const data = await adminService.getAllSources()
        const sourcesArray = Array.isArray(data) ? data : []
        setSources(sourcesArray)
        
        // Build sourcesMap from the fetched sources
        const sourcesLookup = {}
        sourcesArray.forEach(source => {
          sourcesLookup[source.id] = source.display_name || source.name
        })
        setSourcesMap(sourcesLookup)
      } catch (err) {
        console.error('Error fetching sources:', err)
        setSources([])
        setSourcesMap({})
      }
    }
    fetchSources()
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
        if (sourceFilter) params.source_id = parseInt(sourceFilter)
        if (scraperSourceFilter) params.scraper_source = scraperSourceFilter
        if (duplicateFilter !== '') params.is_duplicate = duplicateFilter === 'true'
        if (completenessFilter) params.min_completeness = parseFloat(completenessFilter)
        if (hasPhoneFilter !== '') params.has_phone = hasPhoneFilter === 'true'
        if (hasWebsiteFilter !== '') params.has_website = hasWebsiteFilter === 'true'
        if (hasRatingFilter !== '') params.has_rating = hasRatingFilter === 'true'
        if (hasOpeningHoursFilter !== '') params.has_opening_hours = hasOpeningHoursFilter === 'true'
        if (dateFromFilter) params.created_after = dateFromFilter
        if (dateToFilter) params.created_before = dateToFilter

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
  }, [page, statusFilter, categoryFilter, cityFilter, sourceFilter, scraperSourceFilter, duplicateFilter, 
      completenessFilter, hasPhoneFilter, hasWebsiteFilter, hasRatingFilter, hasOpeningHoursFilter,
      dateFromFilter, dateToFilter, sortBy])

  // Feature 3: buffer a change (called synchronously by EditableCellV2)
  const handleInlineEdit = (resultId, fieldName, fieldValue, isTemporary = false) => {
    // Update the pending changes buffer
    setPendingChanges(prev => ({
      ...prev,
      [resultId]: {
        ...(prev[resultId] || {}),
        [fieldName]: { value: fieldValue, isTemporary }
      }
    }))

    // Update local display state immediately so the cell shows the new value
    setResults(prevResults =>
      prevResults.map(result => {
        if (result.id !== resultId) return result
        
        // Check if this is a custom column (starts with "custom_")
        const isCustomColumn = fieldName.startsWith('custom_')
        
        if (isCustomColumn) {
          // For custom columns, update user_overrides
          const updatedOverrides = {
            ...(result.user_overrides || {}),
            [fieldName]: {
              value: fieldValue,
              temp: isTemporary,
              custom: true
            }
          }
          return { ...result, user_overrides: updatedOverrides }
        } else {
          // For built-in columns, update the field directly
          const tempOverrides = isTemporary
            ? { ...(result._tempOverrides || {}), [fieldName]: true }
            : (() => { const t = { ...(result._tempOverrides || {}) }; delete t[fieldName]; return t })()
          return { ...result, [fieldName]: fieldValue, _tempOverrides: tempOverrides }
        }
      })
    )
  }

  // Feature 3: save all pending changes to the API
  const handleSaveAll = async () => {
    const entries = Object.entries(pendingChanges) // [ [rowId, { fieldName: {value, isTemporary} }] ]
    if (entries.length === 0) return

    setIsSavingAll(true)
    const errors = []

    await Promise.all(
      entries.flatMap(([rowId, fields]) =>
        Object.entries(fields).map(async ([fieldName, { value, isTemporary }]) => {
          try {
            await adminService.inlineEditResult(rowId, fieldName, value, isTemporary)
          } catch (err) {
            errors.push(`${fieldName} on row ${rowId}`)
          }
        })
      )
    )

    setIsSavingAll(false)
    setPendingChanges({})

    if (errors.length > 0) {
      showToast(`${errors.length} change(s) failed to save`, 'error')
    } else {
      const total = entries.reduce((sum, [, fields]) => sum + Object.keys(fields).length, 0)
      showToast(`${total} change${total !== 1 ? 's' : ''} saved successfully`, 'success')
    }
  }

  // Feature 3: discard all pending changes — revert display values
  const handleDiscard = () => {
    // Revert results to their original DB values by re-applying without pending overrides
    setResults(prevResults =>
      prevResults.map(result => {
        const pending = pendingChanges[result.id]
        if (!pending) return result
        // Restore original values from the pending map isn't possible without originals,
        // so just trigger a re-fetch by clearing pending and letting the next fetch restore
        return result
      })
    )
    setPendingChanges({})
    // Re-fetch current page to restore original values
    setPage(p => p) // triggers the useEffect fetch
    showToast('All pending changes discarded', 'success')
  }

  // Total number of pending field changes
  const pendingCount = Object.values(pendingChanges).reduce(
    (sum, fields) => sum + Object.keys(fields).length, 0
  )

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
      
      // Update local state to mark as sent to validated
      setResults(prevResults =>
        prevResults.map(result =>
          result.id === resultId
            ? { ...result, sent_to_validated: true }
            : result
        )
      )
      
      showToast('Result sent to validated_results successfully', 'success')
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
  const handleExport = async (format, selectedColumns, columnRenames = {}) => {
    setIsExporting(true)
    
    try {
      // Build filters object
      const filters = {}
      if (statusFilter) filters.status = statusFilter
      if (categoryFilter) filters.category_id = parseInt(categoryFilter)
      if (cityFilter) filters.city = cityFilter
      if (sourceFilter) filters.source_id = parseInt(sourceFilter)
      if (scraperSourceFilter) filters.scraper_source = scraperSourceFilter
      if (duplicateFilter !== '') filters.is_duplicate = duplicateFilter === 'true'
      if (completenessFilter) filters.min_completeness = parseFloat(completenessFilter)
      if (hasPhoneFilter !== '') filters.has_phone = hasPhoneFilter === 'true'
      if (hasWebsiteFilter !== '') filters.has_website = hasWebsiteFilter === 'true'
      if (hasRatingFilter !== '') filters.has_rating = hasRatingFilter === 'true'
      if (hasOpeningHoursFilter !== '') filters.has_opening_hours = hasOpeningHoursFilter === 'true'
      if (dateFromFilter) filters.created_after = dateFromFilter
      if (dateToFilter) filters.created_before = dateToFilter
      if (sortBy) filters.sort_by = sortBy
      
      // Add selected columns to filters
      if (selectedColumns && selectedColumns.length > 0) {
        filters.columns = selectedColumns.join(',')
      }
      
      // Add column renames (FIX 2)
      if (columnRenames && Object.keys(columnRenames).length > 0) {
        const labels = selectedColumns
          .filter(k => columnRenames[k])
          .map(k => `${k}:${columnRenames[k]}`)
          .join(',')
        if (labels) filters.labels = labels
      }
      
      // Call export API
      const blob = await adminService.exportResults(format, filters)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      // Map format to correct file extension
      const extension = format === 'excel' ? 'xlsx' : format
      link.download = `results_${new Date().toISOString().split('T')[0]}.${extension}`
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
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="name"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.name)}
            pendingValue={pendingChanges[info.row.original.id]?.name?.value}
          />
        )
      },
      {
        accessorKey: 'city',
        header: 'City',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="city"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.city)}
            pendingValue={pendingChanges[info.row.original.id]?.city?.value}
          />
        )
      },
      {
        accessorKey: 'address',
        header: 'Address',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="address"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.address)}
            pendingValue={pendingChanges[info.row.original.id]?.address?.value}
          />
        )
      },
      {
        accessorKey: 'phone_primary',
        header: 'Phone',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="phone_primary"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.phone_primary)}
            pendingValue={pendingChanges[info.row.original.id]?.phone_primary?.value}
          />
        )
      },
      {
        accessorKey: 'phone_secondary',
        header: 'Phone 2',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="phone_secondary"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.phone_secondary)}
            pendingValue={pendingChanges[info.row.original.id]?.phone_secondary?.value}
          />
        )
      },
      {
        accessorKey: 'email',
        header: 'Email',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="email"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.email)}
            pendingValue={pendingChanges[info.row.original.id]?.email?.value}
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
            <EditableCellV2
              value=""
              rowId={info.row.original.id}
              fieldName="website"
              onSave={handleInlineEdit}
              isTemporary={!!(info.row.original._tempOverrides?.website)}
            />
          )
        }
      },
      {
        accessorKey: 'description_short',
        header: 'Description',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="description_short"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.description_short)}
            pendingValue={pendingChanges[info.row.original.id]?.description_short?.value}
          />
        )
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
        accessorKey: 'source_name',
        header: 'Source',
        cell: (info) => (
          <div className="text-slate-700 text-sm">
            {info.getValue() || sourcesMap[info.row.original.source_id] || 'Unknown'}
          </div>
        )
      },
      {
        accessorKey: 'scraper_source',
        header: 'Scraper',
        cell: (info) => {
          const scraperSource = info.getValue();
          return scraperSource ? (
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
              scraperSource === 'go_scraper' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-blue-100 text-blue-800'
            }`}>
              {scraperSource === 'go_scraper' ? '⚡ Go' : '🎭 ' + scraperSource}
            </span>
          ) : (
            <span className="text-xs text-slate-400">—</span>
          );
        }
      },
      {
        accessorKey: 'thumbnail_url',
        header: 'Thumbnail URL',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="thumbnail_url"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.thumbnail_url)}
            pendingValue={pendingChanges[info.row.original.id]?.thumbnail_url?.value}
          />
        )
      },
      {
        accessorKey: 'images_count',
        header: 'Images',
        cell: (info) => {
          // Calculate from image_urls array if images_count is null
          const count = info.getValue() || info.row.original.image_urls?.length || 0
          return count ? (
            <span className="text-sm text-slate-700 font-medium">{count}</span>
          ) : (
            <span className="text-xs text-slate-400">—</span>
          )
        }
      },
      {
        id: 'amenities_col',
        header: 'Amenities',
        cell: (info) => {
          const amenities = info.row.original.amenities || []
          if (!amenities.length) return <span className="text-xs text-slate-400">—</span>
          return (
            <div className="flex flex-wrap gap-1 max-w-xs">
              {amenities.slice(0, 3).map((a, i) => (
                <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-700">
                  {a}
                </span>
              ))}
              {amenities.length > 3 && (
                <span className="text-xs text-slate-500">+{amenities.length - 3}</span>
              )}
            </div>
          )
        }
      },
      {
        accessorKey: 'opening_hours',
        header: 'Hours',
        cell: (info) => (
          <OpeningHoursCell
            value={info.getValue()}
            rowId={info.row.original.id}
            fieldName="opening_hours"
            onSave={handleInlineEdit}
            pendingValue={pendingChanges[info.row.original.id]?.opening_hours?.value}
          />
        )
      },
      {
        accessorKey: 'rating_overall',
        header: 'Rating',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue() ? String(info.getValue()) : ''}
            rowId={info.row.original.id}
            fieldName="rating_overall"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.rating_overall)}
            pendingValue={pendingChanges[info.row.original.id]?.rating_overall?.value}
          />
        )
      },
      {
        accessorKey: 'price_min',
        header: 'Price',
        cell: (info) => (
          <EditableCellV2
            value={info.getValue() ? String(info.getValue()) : ''}
            rowId={info.row.original.id}
            fieldName="price_min"
            onSave={handleInlineEdit}
            isTemporary={!!(info.row.original._tempOverrides?.price_min)}
            pendingValue={pendingChanges[info.row.original.id]?.price_min?.value}
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
        accessorKey: 'review_count',
        header: 'Reviews',
        cell: (info) => {
          const count = info.getValue()
          return count ? (
            <span className="text-sm text-slate-700">{count.toLocaleString()}</span>
          ) : (
            <span className="text-xs text-slate-400">—</span>
          )
        }
      },
      {
        accessorKey: 'place_id',
        header: 'Place ID',
        cell: (info) => {
          const placeId = info.getValue()
          return placeId ? (
            <div className="text-xs font-mono text-slate-600 max-w-[120px] truncate" title={placeId}>
              {placeId}
            </div>
          ) : (
            <span className="text-xs text-slate-400">—</span>
          )
        }
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
        id: 'view_details',
        header: 'Details',
        cell: (info) => (
          <Link
            to={`/results/${info.row.original.id}`}
            className="text-primary-600 hover:text-primary-800 underline text-xs font-medium"
          >
            View
          </Link>
        )
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
    [categories, sourcesMap, sortBy, processingIds, selectedIds, results.length, pendingChanges]
  )

  // Apply column visibility + append custom columns
  const visibleColumns = useMemo(() => {
    // Filter built-in columns by visibility (always keep select, view_details, actions)
    const filtered = columns.filter(col => {
      if (!col.accessorKey) return true // id-only cols (select, view_details, actions)
      return columnVisibility[col.accessorKey] !== false
    })

    // Append custom columns
    const customCols = customColumns.map(({ key, label }) => ({
      accessorKey: key,
      header: () => (
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />
          {label}
        </span>
      ),
      cell: (info) => {
        const row = info.row.original
        // Read from user_overrides — handleInlineEdit keeps this in sync with local state
        // so this always reflects the latest value (pending or saved)
        const storedVal = row.user_overrides?.[key]
        
        // Value: prefer the live user_overrides entry (updated by handleInlineEdit immediately)
        const currentValue = storedVal?.custom ? storedVal.value : null
        
        // isTemporary: true when the stored entry has temp=true
        const isTemp = storedVal?.temp === true
        
        // pendingValue: set when there's a queued-but-unsaved change in pendingChanges
        // This drives the orange border indicator in EditableCellV2
        const pendingEntry = pendingChanges[row.id]?.[key]
        const pendingVal = pendingEntry !== undefined ? pendingEntry.value : undefined
        
        return (
          <EditableCellV2
            value={currentValue !== null && currentValue !== undefined ? String(currentValue) : ''}
            rowId={row.id}
            fieldName={key}
            onSave={handleInlineEdit}
            isTemporary={isTemp}
            pendingValue={pendingVal}
          />
        )
      }
    }))

    // Insert custom cols before view_details
    const insertAt = filtered.findIndex(c => c.id === 'view_details')
    if (insertAt === -1) return [...filtered, ...customCols]
    return [...filtered.slice(0, insertAt), ...customCols, ...filtered.slice(insertAt)]
  }, [columns, columnVisibility, customColumns, pendingChanges])

  // Initialize TanStack Table with manual pagination
  const table = useReactTable({
    data: results,
    columns: visibleColumns,
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
    setSourceFilter('')
    setScraperSourceFilter('')
    setDuplicateFilter('')
    setCompletenessFilter('')
    setHasPhoneFilter('')
    setHasWebsiteFilter('')
    setHasRatingFilter('')
    setHasOpeningHoursFilter('')
    setDateFromFilter('')
    setDateToFilter('')
    setSortBy('created_at')
    setPage(1)
  }

  // Check if any filters are active
  const hasActiveFilters = statusFilter || categoryFilter || cityFilter || sourceFilter || 
    scraperSourceFilter || duplicateFilter || completenessFilter || hasPhoneFilter || hasWebsiteFilter || 
    hasRatingFilter || hasOpeningHoursFilter || dateFromFilter || dateToFilter || sortBy !== 'created_at'

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
      {/* Feature 3: Global Save Bar — appears when there are unsaved changes */}
      <GlobalSaveBar
        pendingCount={pendingCount}
        onSaveAll={handleSaveAll}
        onDiscard={handleDiscard}
        isSaving={isSavingAll}
      />

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Panel</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage and review all scraped results
          </p>
        </div>
        <div className="flex gap-2">
          <Link 
            to="/validated" 
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-gradient-to-r from-emerald-600 to-emerald-700 rounded-lg hover:from-emerald-700 hover:to-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 transition-all duration-200 shadow-sm hover:shadow-md"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Validated Results
          </Link>
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
        <div className="space-y-4">
          {/* Row 1: Basic Filters */}
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

            {/* Source Filter */}
            <div>
              <label htmlFor="source-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Source
              </label>
              <select
                id="source-filter"
                value={sourceFilter}
                onChange={(e) => {
                  setSourceFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">All Sources</option>
                {Array.isArray(sources) && sources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.display_name || source.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Advanced Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Scraper Source Filter */}
            <div>
              <label htmlFor="scraper-source-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Scraper
              </label>
              <select
                id="scraper-source-filter"
                value={scraperSourceFilter}
                onChange={(e) => {
                  setScraperSourceFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">All Scrapers</option>
                <option value="go_scraper">⚡ Go Scraper</option>
                <option value="playwright">🎭 Playwright</option>
                <option value="serpapi">🔍 SerpAPI</option>
              </select>
            </div>

            {/* Duplicate Filter */}
            <div>
              <label htmlFor="duplicate-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Duplicate Status
              </label>
              <select
                id="duplicate-filter"
                value={duplicateFilter}
                onChange={(e) => {
                  setDuplicateFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">All Records</option>
                <option value="false">Unique Only</option>
                <option value="true">Duplicates Only</option>
              </select>
            </div>

            {/* Completeness Filter */}
            <div>
              <label htmlFor="completeness-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Min Completeness
              </label>
              <select
                id="completeness-filter"
                value={completenessFilter}
                onChange={(e) => {
                  setCompletenessFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">Any</option>
                <option value="80">≥ 80%</option>
                <option value="50">≥ 50%</option>
                <option value="30">≥ 30%</option>
              </select>
            </div>

            {/* Has Phone Filter */}
            <div>
              <label htmlFor="phone-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Has Phone
              </label>
              <select
                id="phone-filter"
                value={hasPhoneFilter}
                onChange={(e) => {
                  setHasPhoneFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">Any</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            {/* Has Website Filter */}
            <div>
              <label htmlFor="website-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Has Website
              </label>
              <select
                id="website-filter"
                value={hasWebsiteFilter}
                onChange={(e) => {
                  setHasWebsiteFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">Any</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>

            {/* Has Opening Hours Filter */}
            <div>
              <label htmlFor="opening-hours-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Has Opening Hours
              </label>
              <select
                id="opening-hours-filter"
                value={hasOpeningHoursFilter}
                onChange={(e) => {
                  setHasOpeningHoursFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">Any</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>

          {/* Row 3: Date Range & Actions */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Date From Filter */}
            <div>
              <label htmlFor="date-from-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Created After
              </label>
              <input
                id="date-from-filter"
                type="date"
                value={dateFromFilter}
                onChange={(e) => {
                  setDateFromFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              />
            </div>

            {/* Date To Filter */}
            <div>
              <label htmlFor="date-to-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Created Before
              </label>
              <input
                id="date-to-filter"
                type="date"
                value={dateToFilter}
                onChange={(e) => {
                  setDateToFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              />
            </div>

            {/* Has Rating Filter */}
            <div>
              <label htmlFor="rating-filter" className="block text-sm font-medium text-slate-700 mb-1">
                Has Rating
              </label>
              <select
                id="rating-filter"
                value={hasRatingFilter}
                onChange={(e) => {
                  setHasRatingFilter(e.target.value)
                  setPage(1)
                }}
                className="input"
              >
                <option value="">Any</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
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
            {sourceFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Source: {sources.find(s => s.id === parseInt(sourceFilter))?.display_name || sourceFilter}
              </span>
            )}
            {duplicateFilter !== '' && (
              <span className="badge bg-indigo-50 text-indigo-700">
                {duplicateFilter === 'true' ? 'Duplicates Only' : 'Unique Only'}
              </span>
            )}
            {completenessFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Completeness: ≥{completenessFilter}%
              </span>
            )}
            {hasPhoneFilter !== '' && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Phone: {hasPhoneFilter === 'true' ? 'Yes' : 'No'}
              </span>
            )}
            {hasWebsiteFilter !== '' && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Website: {hasWebsiteFilter === 'true' ? 'Yes' : 'No'}
              </span>
            )}
            {hasRatingFilter !== '' && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Rating: {hasRatingFilter === 'true' ? 'Yes' : 'No'}
              </span>
            )}
            {hasOpeningHoursFilter !== '' && (
              <span className="badge bg-indigo-50 text-indigo-700">
                Opening Hours: {hasOpeningHoursFilter === 'true' ? 'Yes' : 'No'}
              </span>
            )}
            {dateFromFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                From: {dateFromFilter}
              </span>
            )}
            {dateToFilter && (
              <span className="badge bg-indigo-50 text-indigo-700">
                To: {dateToFilter}
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
        {/* Header with count and action buttons */}
        <div className="mb-4 flex justify-between items-center">
          <div className="text-sm text-slate-600">
            {totalCount > 0 && `${totalCount} result${totalCount !== 1 ? 's' : ''} found`}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowColumnManager(true)}
              className="btn btn-secondary flex items-center gap-2"
              title="Manage columns"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
              </svg>
              Columns
              {customColumns.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
                  +{customColumns.length}
                </span>
              )}
            </button>
            <ExportButton
              onExport={() => setShowExportDialog(true)}
              disabled={totalCount === 0}
              isExporting={isExporting}
            />
          </div>
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
            <div ref={tableScrollRef} className="overflow-x-auto">
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

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        onExport={handleExport}
        customColumns={customColumns}
        activeFilters={{
          status: statusFilter,
          category: categoryFilter,
          city: cityFilter,
          source: sourceFilter,
          scraperSource: scraperSourceFilter,
          duplicate: duplicateFilter,
          completeness: completenessFilter,
          hasPhone: hasPhoneFilter,
          hasWebsite: hasWebsiteFilter,
          hasRating: hasRatingFilter,
          hasOpeningHours: hasOpeningHoursFilter,
          dateFrom: dateFromFilter,
          dateTo: dateToFilter
        }}
      />

      {/* Column Manager */}
      <ColumnManager
        isOpen={showColumnManager}
        onClose={() => setShowColumnManager(false)}
        builtinColumns={Object.entries(BUILTIN_COLUMN_LABELS).map(([key, label]) => ({
          key, label, visible: columnVisibility[key] !== false
        }))}
        onToggleColumn={handleToggleColumn}
        customColumns={customColumns}
        onAddCustomColumn={handleAddCustomColumn}
        onRemoveCustomColumn={handleRemoveCustomColumn}
        onResetDefaults={handleResetDefaults}
      />
    </div>
  )
}
