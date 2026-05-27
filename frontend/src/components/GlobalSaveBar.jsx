/**
 * GlobalSaveBar - Feature 3: Global Save Changes
 * Sticky bar that appears when there are pending (unsaved) edits.
 */
export default function GlobalSaveBar({ pendingCount, onSaveAll, onDiscard, isSaving }) {
  if (pendingCount === 0) return null

  return (
    <div className="sticky top-0 z-40 bg-white border-b border-orange-200 shadow-sm">
      <div className="max-w-full px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-orange-700">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-orange-100 text-orange-600 font-semibold text-xs">
            {pendingCount}
          </span>
          <span>
            unsaved {pendingCount === 1 ? 'change' : 'changes'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onDiscard}
            disabled={isSaving}
            className="text-xs px-3 py-1.5 rounded text-slate-600 hover:text-slate-800 hover:bg-slate-100 transition-colors disabled:opacity-50"
          >
            Discard all
          </button>
          <button
            onClick={onSaveAll}
            disabled={isSaving}
            className="text-xs px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            {isSaving ? (
              <>
                <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Saving…
              </>
            ) : (
              <>Save all changes</>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
