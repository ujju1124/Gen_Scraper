/**
 * ColumnManager
 * Panel for toggling built-in column visibility and managing custom columns.
 * Custom columns are stored in database via API (FIX 1).
 */
import { useState, useRef, useEffect } from 'react'
import * as api from '../services/api'

export default function ColumnManager({
  isOpen,
  onClose,
  builtinColumns,        // [{ key, label, visible }]
  onToggleColumn,        // (key) => void
  customColumns,         // [{ id, name, display_name }] - from API
  onAddCustomColumn,     // (label, isTemp) => void - updated to call API
  onRemoveCustomColumn,  // (id) => void - updated to use ID
  onResetDefaults,       // () => void
}) {
  const [newColName, setNewColName] = useState('')
  const [error, setError] = useState('')
  const [isTemp, setIsTemp] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (isOpen && inputRef.current) inputRef.current.focus()
  }, [isOpen])

  if (!isOpen) return null

  const handleAdd = async () => {
    const trimmed = newColName.trim()
    if (!trimmed) { setError('Column name cannot be empty'); return }
    if (trimmed.length > 40) { setError('Max 40 characters'); return }
    
    // Check duplicate
    const key = 'custom_' + trimmed.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
    const exists = customColumns.some(c => c.key === key) ||
                   builtinColumns.some(c => c.key === key)
    if (exists) { setError('A column with that name already exists'); return }
    
    try {
      await onAddCustomColumn(trimmed, isTemp)
      setNewColName('')
      setError('')
      setIsTemp(false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add column')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleAdd()
    if (e.key === 'Escape') onClose()
  }

  const visibleCount = builtinColumns.filter(c => c.visible).length + customColumns.length

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col">

        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Manage Columns</h2>
            <p className="text-xs text-slate-500 mt-0.5">{visibleCount} columns visible</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-6">

          {/* Built-in columns */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-700">Built-in Columns</h3>
              <button
                onClick={onResetDefaults}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                Reset defaults
              </button>
            </div>
            <div className="grid grid-cols-2 gap-1 border border-slate-200 rounded-lg p-3 bg-slate-50">
              {builtinColumns.map(col => (
                <label
                  key={col.key}
                  className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-100 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={col.visible}
                    onChange={() => onToggleColumn(col.key)}
                    className="w-3.5 h-3.5 text-blue-600 rounded"
                  />
                  <span className="text-sm text-slate-700">{col.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Custom columns */}
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-2">Custom Columns</h3>

            {customColumns.length > 0 && (
              <div className="mb-3 space-y-1">
                {customColumns.map(col => (
                  <div
                    key={col.id}
                    className="flex items-center justify-between px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                      <span className="text-sm font-medium text-blue-800">{col.label}</span>
                      <span className="text-xs text-blue-500 italic">custom</span>
                    </div>
                    <button
                      onClick={() => onRemoveCustomColumn(col.id)}
                      className="text-red-400 hover:text-red-600 transition-colors ml-2"
                      title="Remove column"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add new custom column */}
            <div className="border border-dashed border-slate-300 rounded-lg p-3 bg-slate-50">
              <p className="text-xs text-slate-500 mb-2">
                Add a custom column — you can enter data for each row directly in the table.
              </p>
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={newColName}
                  onChange={e => { setNewColName(e.target.value); setError('') }}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. Data Quality Rating"
                  maxLength={40}
                  className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <button
                  onClick={handleAdd}
                  disabled={!newColName.trim()}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Add
                </button>
              </div>
              {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-slate-700 rounded-lg hover:bg-slate-800 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
