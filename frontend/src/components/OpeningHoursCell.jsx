/**
 * OpeningHoursCell
 * Displays opening hours as a compact summary.
 * Click to open an inline editor with one row per day.
 */
import { useState } from 'react'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function parseHours(raw) {
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  try { 
    const parsed = JSON.parse(raw)
    // If it's a valid JSON object, return it
    if (typeof parsed === 'object' && parsed !== null) return parsed
    // If it's a JSON string (like "Working Hours"), return empty object
    return {}
  } catch { 
    // If JSON parse fails, it's plain text - return empty object
    // (we'll handle plain text display separately)
    return {}
  }
}

function summarize(parsed, rawValue) {
  // If we have a plain text value (not JSON), display it directly
  if (rawValue && typeof rawValue === 'string' && !rawValue.trim().startsWith('{')) {
    return rawValue
  }

  const days = Object.keys(parsed)
  if (!days.length) return null

  // Collect unique hour strings
  const unique = [...new Set(days.map(d => {
    const v = parsed[d]
    return Array.isArray(v) ? v[0] : v
  }))]

  // All same hours → compact
  if (unique.length === 1) {
    const abbrevDays = days.map(d => d.slice(0, 3))
    return `${abbrevDays[0]}–${abbrevDays[abbrevDays.length - 1]}  ${unique[0]}`
  }

  // Different hours → show count
  return `${days.length} days (varied)`
}

export default function OpeningHoursCell({ value, rowId, fieldName, onSave, pendingValue }) {
  const [open, setOpen] = useState(false)
  const [saveMode, setSaveMode] = useState('permanent')
  const [isSaving, setIsSaving] = useState(false)

  // Use pending value if available, otherwise DB value
  const raw = pendingValue !== undefined ? pendingValue : value
  const parsed = parseHours(raw)
  const isPending = pendingValue !== undefined

  // Local edit state — one string per day
  const [draft, setDraft] = useState({})

  const openEditor = () => {
    const initial = {}
    DAYS.forEach(d => {
      const v = parsed[d]
      initial[d] = Array.isArray(v) ? v[0] : (v || '')
    })
    setDraft(initial)
    setOpen(true)
  }

  const handleSave = async () => {
    // Build cleaned object — omit empty days
    const cleaned = {}
    DAYS.forEach(d => { if (draft[d]?.trim()) cleaned[d] = [draft[d].trim()] })
    const serialized = JSON.stringify(cleaned)

    setIsSaving(true)
    try {
      await onSave(rowId, fieldName, serialized, saveMode === 'temporary')
      setOpen(false)
    } catch (err) {
      console.error('Save error:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const summary = summarize(parsed, raw)

  // ── Display mode ──────────────────────────────────────────────────────────
  if (!open) {
    return (
      <div
        onClick={openEditor}
        title="Click to edit opening hours"
        className={`cursor-pointer rounded px-1 py-0.5 min-h-[22px] hover:bg-slate-100 transition-colors group text-xs ${
          isPending ? 'border-l-2 border-orange-400 pl-1.5' : ''
        }`}
      >
        {summary ? (
          <span className="text-slate-700">
            {summary}
            {isPending && <span className="ml-1 text-orange-500 font-medium">•</span>}
          </span>
        ) : (
          <span className="text-slate-400 italic group-hover:text-slate-500">Click to add</span>
        )}
      </div>
    )
  }

  // ── Edit mode ─────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-2 py-1 min-w-[220px]">
      <div className="grid gap-1">
        {DAYS.map(day => (
          <div key={day} className="flex items-center gap-1.5">
            <span className="text-xs text-slate-500 w-8 shrink-0">{day.slice(0, 3)}</span>
            <input
              type="text"
              value={draft[day] || ''}
              onChange={e => setDraft(prev => ({ ...prev, [day]: e.target.value }))}
              placeholder="e.g. 9AM–6PM"
              className="flex-1 border border-slate-300 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
        ))}
      </div>

      <div className="flex items-center gap-1.5 pt-0.5">
        <select
          value={saveMode}
          onChange={e => setSaveMode(e.target.value)}
          disabled={isSaving}
          className="text-xs border border-slate-300 rounded px-1.5 py-0.5 bg-white text-slate-600 focus:outline-none"
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
          onClick={() => setOpen(false)}
          disabled={isSaving}
          className="text-xs px-2 py-0.5 rounded text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
