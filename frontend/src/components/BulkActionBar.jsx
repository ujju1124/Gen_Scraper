/**
 * BulkActionBar Component
 * Displays bulk action controls when rows are selected
 */

export function BulkActionBar({ selectedCount, onApprove, onReject, onClear, isProcessing }) {
  if (selectedCount === 0) return null

  return (
    <div
      data-testid="bulk-action-bar"
      className="bg-primary-50 border border-primary-200 rounded-lg p-4 flex items-center justify-between"
    >
      <div className="flex items-center space-x-4">
        <span className="text-sm font-medium text-primary-900">
          {selectedCount} result{selectedCount !== 1 ? 's' : ''} selected
        </span>
        <div className="flex space-x-2">
          <button
            onClick={onApprove}
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing...
              </>
            ) : (
              `Approve Selected (${selectedCount})`
            )}
          </button>
          <button
            onClick={onReject}
            disabled={isProcessing}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing...
              </>
            ) : (
              `Reject Selected (${selectedCount})`
            )}
          </button>
        </div>
      </div>
      <button
        onClick={onClear}
        className="text-sm text-primary-600 hover:text-primary-700"
      >
        Clear Selection
      </button>
    </div>
  )
}
