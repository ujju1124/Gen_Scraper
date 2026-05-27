/**
 * ExportDialog Component
 * Modal dialog for selecting export format and columns
 */
import { useState, useMemo } from 'react'

// Built-in columns for export
const BUILTIN_COLUMNS = [
  { key: 'id', label: 'ID', defaultChecked: false },
  { key: 'job_id', label: 'Job ID', defaultChecked: false },
  { key: 'source_id', label: 'Source ID', defaultChecked: false },
  { key: 'source_name', label: 'Source Name', defaultChecked: true },
  { key: 'category_id', label: 'Category ID', defaultChecked: false },
  { key: 'name', label: 'Name', defaultChecked: true },
  { key: 'city', label: 'City', defaultChecked: true },
  { key: 'address', label: 'Address', defaultChecked: true },
  { key: 'latitude', label: 'Latitude', defaultChecked: true },
  { key: 'longitude', label: 'Longitude', defaultChecked: true },
  { key: 'phone_primary', label: 'Phone Primary', defaultChecked: true },
  { key: 'phone_secondary', label: 'Phone Secondary', defaultChecked: false },
  { key: 'email', label: 'Email', defaultChecked: true },
  { key: 'website', label: 'Website', defaultChecked: true },
  { key: 'description_short', label: 'Description', defaultChecked: false },
  { key: 'rating_overall', label: 'Rating', defaultChecked: true },
  { key: 'review_count', label: 'Review Count', defaultChecked: false },
  { key: 'price_min', label: 'Price Min', defaultChecked: false },
  { key: 'price_max', label: 'Price Max', defaultChecked: false },
  { key: 'currency', label: 'Currency', defaultChecked: false },
  { key: 'thumbnail_url', label: 'Thumbnail URL', defaultChecked: false },
  { key: 'image_urls', label: 'Image URLs', defaultChecked: false },
  { key: 'amenities', label: 'Amenities', defaultChecked: false },
  { key: 'opening_hours', label: 'Opening Hours', defaultChecked: true },
  { key: 'scraper_source', label: 'Scraper Source', defaultChecked: false },
  { key: 'data_completeness', label: 'Data Completeness', defaultChecked: true },
  { key: 'status', label: 'Status', defaultChecked: true },
  { key: 'created_at', label: 'Created At', defaultChecked: false }
]

export default function ExportDialog({ isOpen, onClose, onExport, activeFilters, customColumns = [] }) {
  const [format, setFormat] = useState('csv')
  
  // Load saved column renames from localStorage
  const [columnRenames, setColumnRenames] = useState(() => {
    try {
      const saved = localStorage.getItem('exportColumnRenames')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })
  
  // Combine built-in columns with custom columns
  const availableColumns = useMemo(() => {
    const customCols = customColumns.map(col => ({
      key: col.name || col.key,  // Support both API format (name) and old format (key)
      label: col.display_name || col.label,
      defaultChecked: true,
      isCustom: true
    }))
    return [...BUILTIN_COLUMNS, ...customCols]
  }, [customColumns])
  
  const [selectedColumns, setSelectedColumns] = useState(
    availableColumns.filter(col => col.defaultChecked).map(col => col.key)
  )

  if (!isOpen) return null

  const handleToggleColumn = (columnKey) => {
    setSelectedColumns(prev => 
      prev.includes(columnKey)
        ? prev.filter(k => k !== columnKey)
        : [...prev, columnKey]
    )
  }

  const handleSelectAll = () => {
    setSelectedColumns(availableColumns.map(col => col.key))
  }

  const handleDeselectAll = () => {
    setSelectedColumns([])
  }
  
  const handleResetRenames = () => {
    setColumnRenames({})
    localStorage.removeItem('exportColumnRenames')
  }

  const handleExport = () => {
    onExport(format, selectedColumns, columnRenames)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-xl font-semibold text-slate-800">Export Data</h2>
          <p className="text-sm text-slate-600 mt-1">
            Select columns to include in your export
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {/* Format Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Export Format
            </label>
            <div className="flex gap-3">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="csv"
                  checked={format === 'csv'}
                  onChange={(e) => setFormat(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm">CSV</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="json"
                  checked={format === 'json'}
                  onChange={(e) => setFormat(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm">JSON</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="excel"
                  checked={format === 'excel'}
                  onChange={(e) => setFormat(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm">Excel</span>
              </label>
            </div>
          </div>

          {/* Column Selection */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-slate-700">
                Columns ({selectedColumns.length} selected)
              </label>
              <div className="flex gap-2">
                <button
                  onClick={handleSelectAll}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  Select All
                </button>
                <span className="text-slate-300">|</span>
                <button
                  onClick={handleDeselectAll}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  Deselect All
                </button>
                <span className="text-slate-300">|</span>
                <button
                  onClick={handleResetRenames}
                  className="text-xs text-orange-600 hover:text-orange-700 font-medium"
                  title="Clear all saved column renames"
                >
                  Reset Renames
                </button>
              </div>
            </div>

            <div className="border border-slate-200 rounded overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="p-2 w-8 text-left">
                      <input
                        type="checkbox"
                        checked={selectedColumns.length === availableColumns.length}
                        onChange={() => selectedColumns.length === availableColumns.length ? handleDeselectAll() : handleSelectAll()}
                        className="rounded"
                      />
                    </th>
                    <th className="p-2 text-left text-xs font-medium text-slate-600">Field</th>
                    <th className="p-2 text-left text-xs font-medium text-slate-600">Export Name</th>
                  </tr>
                </thead>
                <tbody className="max-h-64 overflow-y-auto">
                  {availableColumns.map(column => (
                    <tr key={column.key} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="p-2">
                        <input
                          type="checkbox"
                          checked={selectedColumns.includes(column.key)}
                          onChange={() => handleToggleColumn(column.key)}
                          className="rounded"
                        />
                      </td>
                      <td className="p-2 text-xs text-slate-500">
                        {column.isCustom && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block mr-1" />
                        )}
                        {column.key}
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          value={columnRenames[column.key] ?? column.label}
                          onChange={e => {
                            const newRenames = {
                              ...columnRenames,
                              [column.key]: e.target.value
                            }
                            setColumnRenames(newRenames)
                            // Save to localStorage for persistence
                            localStorage.setItem('exportColumnRenames', JSON.stringify(newRenames))
                          }}
                          placeholder={column.label}
                          className="border border-slate-200 rounded px-2 py-1 text-xs w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Active Filters Info */}
          {Object.keys(activeFilters).length > 0 && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
              <p className="text-xs text-blue-800 font-medium mb-1">
                Active Filters Applied
              </p>
              <p className="text-xs text-blue-600">
                Export will include only filtered results
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={selectedColumns.length === 0}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Export {format.toUpperCase()}
          </button>
        </div>
      </div>
    </div>
  )
}
