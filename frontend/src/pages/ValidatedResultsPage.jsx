/**
 * Validated Results Page
 * Read-only view of validated business data
 * Can be accessed by clients via API
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import * as validatedService from '../services/validatedService'
import * as adminService from '../services/adminService'
import * as jobService from '../services/jobService'
import { StatusBadge } from '../components/StatusBadge'
import { ProgressBar } from '../components/ProgressBar'
import { PaginationControls } from '../components/PaginationControls'
import { ExportButton } from '../components/ExportButton'
import ExportDialog from '../components/ExportDialog'
import ColumnManager from '../components/ColumnManager'
import { useDragScroll } from '../hooks/useDragScroll'

export function ValidatedResultsPage() {
  // Data state
  const [results, setResults] = useState([])
  const [stats, setStats] = useState(null)
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
  const [categoryFilter, setCategoryFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const [hasPhoneFilter, setHasPhoneFilter] = useState('')
  const [hasWebsiteFilter, setHasWebsiteFilter] = useState('')
  const [hasRatingFilter, setHasRatingFilter] = useState('')
  const [minRatingFilter, setMinRatingFilter] = useState('')
  const [dateFromFilter, setDateFromFilter] = useState('')
  const [dateToFilter, setDateToFilter] = useState('')
  
  // Sort state
  const [sortBy, setSortBy] = useState('validated_at')
  
  // Export state
  const [showExportDialog, setShowExportDialog] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  
  // Custom columns state
  const [customColumns, setCustomColumns] = useState([])
  
  // Column visibility state - load from localStorage
  const [showColumnManager, setShowColumnManager] = useState(false)
  const DEFAULT_COLUMN_VISIBILITY = {
    name: true,
    city: true,
    address: true,
    phone_primary: true,
    phone_secondary: false,
    email: true,
    website: true,
    description_short: false,
    latitude: false,
    longitude: false,
    category_id: true,
    source_name: false,
    scraper_source: false,
    thumbnail_url: false,
    images_count: true,
    amenities: false,
    opening_hours: true,
    rating_overall: true,
    review_count: false,
    price_min: false,
    price_max: false,
    currency: false,
    data_completeness: true,
    place_id: false
  }
  
  const [columnVisibility, setColumnVisibility] = useState(() => {
    try {
      const saved = localStorage.getItem('validatedColumnVisibility')
      return saved ? { ...DEFAULT_COLUMN_VISIBILITY, ...JSON.parse(saved) } : DEFAULT_COLUMN_VISIBILITY
    } catch {
      return DEFAULT_COLUMN_VISIBILITY
    }
  })

  const BUILTIN_COLUMN_LABELS = {
    name: 'Name',
    city: 'City',
    address: 'Address',
    phone_primary: 'Phone',
    phone_secondary: 'Phone 2',
    email: 'Email',
    website: 'Website',
    description_short: 'Description',
    latitude: 'Latitude',
    longitude: 'Longitude',
    category_id: 'Category',
    source_name: 'Source',
    scraper_source: 'Scraper',
    thumbnail_url: 'Thumbnail URL',
    images_count: 'Images',
    amenities: 'Amenities',
    opening_hours: 'Hours',
    rating_overall: 'Rating',
    review_count: 'Reviews',
    price_min: 'Price Min',
    price_max: 'Price Max',
    currency: 'Currency',
    data_completeness: 'Completeness',
    place_id: 'Place ID'
  }

  // Column manager handlers
  const handleToggleColumn = (key) => {
    setColumnVisibility(prev => {
      const next = { ...prev, [key]: !prev[key] }
      localStorage.setItem('validatedColumnVisibility', JSON.stringify(next))
      return next
    })
  }

  const handleResetDefaults = () => {
    setColumnVisibility(DEFAULT_COLUMN_VISIBILITY)
    localStorage.setItem('validatedColumnVisibility', JSON.stringify(DEFAULT_COLUMN_VISIBILITY))
  }
  
  // Categories for dropdown
  const [categories, setCategories] = useState([])

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

  // Load custom columns from API on mount
  useEffect(() => {
    const loadCustomColumns = async () => {
      try {
        const response = await adminService.getColumnDefinitions()
        // Transform API response {id, name, display_name} to {id, key, label}
        const transformed = response.map(col => ({
          id: col.id,
          key: col.name,
          label: col.display_name
        }))
        setCustomColumns(transformed)
      } catch (err) {
        console.error('Failed to load custom columns:', err)
      }
    }
    loadCustomColumns()
  }, [])

  // Fetch stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await validatedService.getValidatedStats()
        setStats(data)
      } catch (err) {
        console.error('Error fetching stats:', err)
      }
    }
    fetchStats()
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

        if (categoryFilter) params.category_id = parseInt(categoryFilter)
        if (cityFilter) params.city = cityFilter
        if (hasPhoneFilter !== '') params.has_phone = hasPhoneFilter === 'true'
        if (hasWebsiteFilter !== '') params.has_website = hasWebsiteFilter === 'true'
        if (hasRatingFilter !== '') params.has_rating = hasRatingFilter === 'true'
        if (minRatingFilter) params.min_rating = parseFloat(minRatingFilter)
        if (dateFromFilter) params.validated_after = dateFromFilter
        if (dateToFilter) params.validated_before = dateToFilter

        const data = await validatedService.getValidatedResults(params)
        setResults(data.items || [])
        setTotalPages(data.pages || 1)
        setTotalCount(data.total || 0)
      } catch (err) {
        setError('Failed to load validated results')
        console.error('Error fetching validated results:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [page, categoryFilter, cityFilter, hasPhoneFilter, hasWebsiteFilter, hasRatingFilter, 
      minRatingFilter, dateFromFilter, dateToFilter, sortBy])

  // Handle sort change
  const handleSortChange = (field) => {
    setSortBy(field)
    setPage(1)
  }

  // Reset filters
  const handleResetFilters = () => {
    setCategoryFilter('')
    setCityFilter('')
    setHasPhoneFilter('')
    setHasWebsiteFilter('')
    setHasRatingFilter('')
    setMinRatingFilter('')
    setDateFromFilter('')
    setDateToFilter('')
    setSortBy('validated_at')
    setPage(1)
  }

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

  // Handle export
  const handleExport = async (format, selectedColumns, columnRenames = {}) => {
    setIsExporting(true)
    
    try {
      // Build filters object - same as current filters but add status=APPROVED
      const filters = {
        status: 'APPROVED'  // Only export approved results (validated results are approved)
      }
      
      if (categoryFilter) filters.category_id = parseInt(categoryFilter)
      if (cityFilter) filters.city = cityFilter
      if (hasPhoneFilter !== '') filters.has_phone = hasPhoneFilter === 'true'
      if (hasWebsiteFilter !== '') filters.has_website = hasWebsiteFilter === 'true'
      if (hasRatingFilter !== '') filters.has_rating = hasRatingFilter === 'true'
      if (minRatingFilter) filters.min_rating = parseFloat(minRatingFilter)
      if (dateFromFilter) filters.created_after = dateFromFilter
      if (dateToFilter) filters.created_before = dateToFilter
      if (sortBy) filters.sort_by = sortBy
      
      // Add selected columns to filters
      if (selectedColumns && selectedColumns.length > 0) {
        filters.columns = selectedColumns.join(',')
      }
      
      // Add column renames
      if (columnRenames && Object.keys(columnRenames).length > 0) {
        const labels = selectedColumns
          .filter(k => columnRenames[k])
          .map(k => `${k}:${columnRenames[k]}`)
          .join(',')
        if (labels) filters.labels = labels
      }
      
      // Call admin export API (validated results use same endpoint with status=APPROVED)
      const blob = await adminService.exportResults(format, filters)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const extension = format === 'excel' ? 'xlsx' : format
      link.download = `validated_results_${new Date().toISOString().split('T')[0]}.${extension}`
      document.body.appendChild(link)
      link.click()
      
      // Cleanup
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      showToast(`Export completed successfully (${format.toUpperCase()})`, 'success')
      setShowExportDialog(false)
    } catch (error) {
      console.error('Export error:', error)
      const errorMessage = error.response?.data?.detail || 'Failed to export results'
      showToast(errorMessage, 'error')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 mb-2">
                ✓ Validated Results
              </h1>
              <p className="text-slate-600">
                Approved and validated business data ready for use
              </p>
            </div>
            <Link
              to="/admin"
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-300 hover:bg-slate-50 transition-colors"
            >
              ← Back to Admin
            </Link>
          </div>

          {/* Stats Cards */}
          {stats && stats.total !== undefined && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
                <div className="text-sm font-medium text-slate-600 mb-1">Total Validated</div>
                <div className="text-3xl font-bold text-slate-900">{stats.total.toLocaleString()}</div>
              </div>
              <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
                <div className="text-sm font-medium text-slate-600 mb-1">With Phone</div>
                <div className="text-3xl font-bold text-green-600">{stats.with_phone.toLocaleString()}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {((stats.with_phone / stats.total) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
                <div className="text-sm font-medium text-slate-600 mb-1">With Website</div>
                <div className="text-3xl font-bold text-blue-600">{stats.with_website.toLocaleString()}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {((stats.with_website / stats.total) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
                <div className="text-sm font-medium text-slate-600 mb-1">With Rating</div>
                <div className="text-3xl font-bold text-amber-600">{stats.with_rating.toLocaleString()}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {((stats.with_rating / stats.total) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Filters</h2>
            <button
              onClick={handleResetFilters}
              className="text-sm text-primary-600 hover:text-primary-800 font-medium"
            >
              Reset All
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Category Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Category
              </label>
              <select
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="">All Categories</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.display_name}</option>
                ))}
              </select>
            </div>

            {/* City Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                City
              </label>
              <input
                type="text"
                value={cityFilter}
                onChange={(e) => { setCityFilter(e.target.value); setPage(1); }}
                placeholder="e.g., Kathmandu"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
            </div>

            {/* Has Phone Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Phone
              </label>
              <select
                value={hasPhoneFilter}
                onChange={(e) => { setHasPhoneFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="">All</option>
                <option value="true">Has Phone</option>
                <option value="false">No Phone</option>
              </select>
            </div>

            {/* Has Website Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Website
              </label>
              <select
                value={hasWebsiteFilter}
                onChange={(e) => { setHasWebsiteFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="">All</option>
                <option value="true">Has Website</option>
                <option value="false">No Website</option>
              </select>
            </div>

            {/* Min Rating Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Min Rating
              </label>
              <input
                type="number"
                value={minRatingFilter}
                onChange={(e) => { setMinRatingFilter(e.target.value); setPage(1); }}
                placeholder="e.g., 4.0"
                min="0"
                max="10"
                step="0.1"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
            </div>

            {/* Date From Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Validated From
              </label>
              <input
                type="date"
                value={dateFromFilter}
                onChange={(e) => { setDateFromFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
            </div>

            {/* Date To Filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Validated To
              </label>
              <input
                type="date"
                value={dateToFilter}
                onChange={(e) => { setDateToFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              >
                <option value="validated_at">Validation Date</option>
                <option value="rating">Rating</option>
              </select>
            </div>
          </div>
        </div>

        {/* Results Table */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Results ({totalCount.toLocaleString()})
              </h2>
              <p className="text-sm text-slate-600 mt-1">
                Showing {results.length} of {totalCount.toLocaleString()} validated results
              </p>
            </div>
            
            {/* Export Button */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowColumnManager(true)}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-300 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-all duration-200 shadow-sm hover:shadow-md"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
                Manage Columns
              </button>
              
              <button
                onClick={() => setShowExportDialog(true)}
                disabled={isExporting || results.length === 0}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-green-600 to-green-700 rounded-lg hover:from-green-700 hover:to-green-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {isExporting ? 'Exporting...' : 'Export'}
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="px-6 py-12 text-center">
              <p className="text-red-600">{error}</p>
            </div>
          ) : results.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-slate-600">No validated results found</p>
            </div>
          ) : (
            <>
              <div ref={tableScrollRef} className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      {columnVisibility.name && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Name
                        </th>
                      )}
                      {columnVisibility.city && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          City
                        </th>
                      )}
                      {columnVisibility.address && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Address
                        </th>
                      )}
                      {columnVisibility.phone_primary && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Phone
                        </th>
                      )}
                      {columnVisibility.phone_secondary && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Phone 2
                        </th>
                      )}
                      {columnVisibility.email && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Email
                        </th>
                      )}
                      {columnVisibility.website && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Website
                        </th>
                      )}
                      {columnVisibility.description_short && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Description
                        </th>
                      )}
                      {columnVisibility.latitude && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Latitude
                        </th>
                      )}
                      {columnVisibility.longitude && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Longitude
                        </th>
                      )}
                      {columnVisibility.category_id && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Category
                        </th>
                      )}
                      {columnVisibility.source_name && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Source
                        </th>
                      )}
                      {columnVisibility.scraper_source && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Scraper
                        </th>
                      )}
                      {columnVisibility.thumbnail_url && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Thumbnail
                        </th>
                      )}
                      {columnVisibility.images_count && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Images
                        </th>
                      )}
                      {columnVisibility.amenities && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Amenities
                        </th>
                      )}
                      {columnVisibility.opening_hours && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Hours
                        </th>
                      )}
                      {columnVisibility.rating_overall && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Rating
                        </th>
                      )}
                      {columnVisibility.review_count && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Reviews
                        </th>
                      )}
                      {columnVisibility.price_min && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Price Min
                        </th>
                      )}
                      {columnVisibility.price_max && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Price Max
                        </th>
                      )}
                      {columnVisibility.currency && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Currency
                        </th>
                      )}
                      {columnVisibility.data_completeness && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Completeness
                        </th>
                      )}
                      {columnVisibility.place_id && (
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          Place ID
                        </th>
                      )}
                      {/* Custom columns */}
                      {customColumns.map(col => (
                        <th key={col.key} className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                          {col.label}
                        </th>
                      ))}
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-200">
                    {results.map((result) => {
                      const category = categories.find(c => c.id === result.category_id)
                      const userOverrides = result.user_overrides || {}
                      
                      return (
                        <tr key={result.id} className="hover:bg-slate-50 transition-colors">
                          {columnVisibility.name && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-slate-900">
                                {result.name || 'N/A'}
                              </div>
                            </td>
                          )}
                          {columnVisibility.city && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">{result.city || 'N/A'}</div>
                            </td>
                          )}
                          {columnVisibility.address && (
                            <td className="px-6 py-4">
                              <div className="text-sm text-slate-700 max-w-xs truncate">{result.address || 'N/A'}</div>
                            </td>
                          )}
                          {columnVisibility.phone_primary && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.phone_primary || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.phone_secondary && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.phone_secondary || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.email && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.email || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.website && (
                            <td className="px-6 py-4">
                              {result.website ? (
                                <a
                                  href={result.website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-primary-600 hover:text-primary-800 underline truncate block max-w-xs"
                                >
                                  {result.website}
                                </a>
                              ) : (
                                <span className="text-sm text-slate-400">—</span>
                              )}
                            </td>
                          )}
                          {columnVisibility.description_short && (
                            <td className="px-6 py-4">
                              <div className="text-sm text-slate-700 max-w-xs truncate">
                                {result.description_short || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.latitude && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">{result.latitude || 'N/A'}</div>
                            </td>
                          )}
                          {columnVisibility.longitude && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">{result.longitude || 'N/A'}</div>
                            </td>
                          )}
                          {columnVisibility.category_id && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {category?.display_name || 'Unknown'}
                              </div>
                            </td>
                          )}
                          {columnVisibility.source_name && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">{result.source_name || 'N/A'}</div>
                            </td>
                          )}
                          {columnVisibility.scraper_source && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">{result.scraper_source || 'N/A'}</div>
                            </td>
                          )}
                          {columnVisibility.thumbnail_url && (
                            <td className="px-6 py-4">
                              {result.thumbnail_url ? (
                                <a href={result.thumbnail_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary-600 hover:text-primary-800 underline">
                                  View
                                </a>
                              ) : (
                                <span className="text-sm text-slate-400">—</span>
                              )}
                            </td>
                          )}
                          {columnVisibility.images_count && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {Array.isArray(result.image_urls) ? result.image_urls.length : 0}
                              </div>
                            </td>
                          )}
                          {columnVisibility.amenities && (
                            <td className="px-6 py-4">
                              <div className="text-sm text-slate-700 max-w-xs truncate">
                                {Array.isArray(result.amenities) && result.amenities.length > 0
                                  ? result.amenities.join(', ')
                                  : <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.opening_hours && (
                            <td className="px-6 py-4">
                              <div className="text-sm text-slate-700 max-w-xs truncate">
                                {result.opening_hours ? (
                                  typeof result.opening_hours === 'string' 
                                    ? result.opening_hours 
                                    : JSON.stringify(result.opening_hours)
                                ) : <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.rating_overall && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              {result.rating_overall ? (
                                <div className="flex items-center gap-1">
                                  <span className="text-sm font-medium text-amber-600">
                                    ⭐ {result.rating_overall}
                                  </span>
                                </div>
                              ) : (
                                <span className="text-sm text-slate-400">—</span>
                              )}
                            </td>
                          )}
                          {columnVisibility.review_count && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.review_count || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.price_min && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.price_min || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.price_max && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.price_max || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.currency && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.currency || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {columnVisibility.data_completeness && (
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {result.data_completeness ? `${result.data_completeness.toFixed(1)}%` : 'N/A'}
                              </div>
                            </td>
                          )}
                          {columnVisibility.place_id && (
                            <td className="px-6 py-4">
                              <div className="text-sm text-slate-700 max-w-xs truncate">
                                {result.place_id || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          )}
                          {/* Custom columns */}
                          {customColumns.map(col => (
                            <td key={col.key} className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-slate-700">
                                {userOverrides[col.key]?.value || <span className="text-slate-400">—</span>}
                              </div>
                            </td>
                          ))}
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Link
                              to={`/results/${result.id}`}
                              className="text-sm text-primary-600 hover:text-primary-800 underline font-medium"
                            >
                              View Details
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-slate-200">
                <PaginationControls
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        onExport={handleExport}
        isExporting={isExporting}
        customColumns={customColumns}
        activeFilters={{}}
      />

      {/* Column Manager - Functional for validated results */}
      <ColumnManager
        isOpen={showColumnManager}
        onClose={() => setShowColumnManager(false)}
        builtinColumns={Object.entries(BUILTIN_COLUMN_LABELS).map(([key, label]) => ({
          key,
          label,
          visible: columnVisibility[key] !== false
        }))}
        onToggleColumn={handleToggleColumn}
        customColumns={customColumns}
        onAddCustomColumn={() => {}}
        onRemoveCustomColumn={() => {}}
        onResetDefaults={handleResetDefaults}
      />
    </div>
  )
}
