/**
 * Pagination Controls Component
 * Reusable pagination with previous/next navigation
 */

/**
 * @param {Object} props
 * @param {number} props.currentPage - Current page number
 * @param {number} props.totalPages - Total number of pages
 * @param {number} props.totalCount - Total number of items
 * @param {function} props.onPageChange - Callback when page changes
 */
export function PaginationControls({ currentPage, totalPages, totalCount, onPageChange }) {
  const handlePrevious = () => {
    if (currentPage > 1 && onPageChange) {
      onPageChange(currentPage - 1)
    }
  }

  const handleNext = () => {
    if (currentPage < totalPages && onPageChange) {
      onPageChange(currentPage + 1)
    }
  }

  return (
    <div className="flex items-center justify-between border-t border-slate-200 pt-4">
      <div className="text-sm text-slate-600">
        Page {currentPage} of {totalPages} ({totalCount?.toLocaleString() || totalCount} total results)
      </div>
      <div className="flex gap-2">
        <button
          onClick={handlePrevious}
          disabled={currentPage === 1}
          className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <button
          onClick={handleNext}
          disabled={currentPage >= totalPages}
          className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  )
}
