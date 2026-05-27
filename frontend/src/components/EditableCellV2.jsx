/**
 * EditableCellV2 - Full Inline Edit (Feature 2 + Feature 3)
 *
 * Works in two modes depending on whether a pendingValue is passed:
 *   - Buffered (Feature 3): parent holds the value, changes are queued
 *   - Direct (legacy): saves immediately on Save click
 *
 * Visual states:
 *   - isTemporary: small clock icon next to value
 *   - isPending:   orange left border — change is queued, not yet saved
 */
import { useState, useEffect, useRef } from 'react'

export default function EditableCellV2({
  value,           // original DB value
  rowId,
  fieldName,
  onSave,          // (rowId, fieldName, value, isTemporary) => void  [buffered: sync, direct: async]
  disabled = false,
  isTemporary = false,  // true when current value is a DB-stored temp override
  pendingValue = undefined, // if set, this is the buffered (unsaved) value
}) {
  const [editing, setEditing] = useState(false)
  const [saveMode, setSaveMode] = useState('permanent')
  const [isSaving, setIsSaving] = useState(false)

  // The displayed value: pending overrides DB value
  const displayValue = pendingValue !== undefined ? pendingValue : value
  const isPending = pendingValue !== undefined

  const [inputVal, setInputVal] = useState(displayValue || '')
  const inputRef = useRef(null)

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  // Sync input when display value changes externally (e.g. discard)
  useEffect(() => {
    if (!editing) setInputVal(displayValue || '')
  }, [displayValue, editing])

  const handleSave = async () => {
    if (inputVal === (displayValue || '')) { setEditing(false); return }

    setIsSaving(true)
    try {
      await onSave(rowId, fieldName, inputVal || null, saveMode === 'temporary')
      setEditing(false)
    } catch (err) {
      console.error('Save error:', err)
      setInputVal(displayValue || '')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => { setInputVal(displayValue || ''); setEditing(false) }
  const handleKeyDown = (e) => { if (e.key === 'Escape') handleCancel() }

  if (disabled) {
    return <span className="text-slate-600 text-sm">{displayValue || '—'}</span>
  }

  // ── Display mode ──────────────────────────────────────────────────────────
  if (!editing) {
    return (
      <div
        onClick={() => setEditing(true)}
        title={
          isPending ? 'Unsaved change — click to edit' :
          isTemporary ? 'Temporary edit — reverts on refresh. Click to edit.' :
          'Click to edit'
        }
        className={`cursor-pointer rounded px-1 py-0.5 min-h-[22px] hover:bg-slate-100 transition-colors group ${
          isPending ? 'border-l-2 border-orange-400 pl-1.5' : ''
        }`}
      >
        {displayValue ? (
          <span className="text-sm text-slate-700">
            {displayValue}
            {isTemporary && !isPending && (
              <svg
                className="inline-block ml-1 mb-0.5 text-slate-400"
                width="11" height="11" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            )}
            {isPending && (
              <span className="ml-1 text-xs text-orange-500 font-medium">•</span>
            )}
          </span>
        ) : (
          <span className="text-slate-300 text-xs italic group-hover:text-slate-400 transition-colors">
            —
          </span>
        )}
      </div>
    )
  }

  // ── Edit mode ─────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-1.5 py-0.5">
      <input
        ref={inputRef}
        type="text"
        value={inputVal}
        onChange={(e) => setInputVal(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isSaving}
        className="border border-blue-400 rounded px-2 py-1 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        placeholder="Enter value…"
      />

      <div className="flex items-center gap-1.5">
        <select
          value={saveMode}
          onChange={(e) => setSaveMode(e.target.value)}
          disabled={isSaving}
          className="text-xs border border-slate-300 rounded px-1.5 py-0.5 bg-white text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-400"
        >
          <option value="permanent">Permanent</option>
          <option value="temporary">Temporary</option>
        </select>

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="text-xs px-2.5 py-0.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 transition-colors"
        >
          {isSaving ? 'Saving…' : 'Queue'}
        </button>

        <button
          onClick={handleCancel}
          disabled={isSaving}
          className="text-xs px-2 py-0.5 rounded text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          Cancel
        </button>
      </div>

      {saveMode === 'temporary' && (
        <p className="text-xs text-slate-400 leading-tight">
          Shown now · reverts on refresh
        </p>
      )}
    </div>
  )
}
