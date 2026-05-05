/**
 * Loading Skeleton Components
 * Animated skeleton loaders for tables and forms
 */

/**
 * Table Skeleton Loader
 * @param {Object} props
 * @param {number} props.rows - Number of skeleton rows to display
 * @param {number} props.columns - Number of columns
 */
export function TableSkeleton({ rows = 5, columns = 5 }) {
  return (
    <div className="animate-pulse">
      {/* Table Header */}
      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <div key={`header-${i}`} className="h-4 bg-slate-200 rounded"></div>
        ))}
      </div>

      {/* Table Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={`row-${rowIndex}`}
          className="grid gap-4 mb-3"
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div
              key={`cell-${rowIndex}-${colIndex}`}
              className="h-4 bg-slate-100 rounded"
            ></div>
          ))}
        </div>
      ))}
    </div>
  )
}

/**
 * Form Skeleton Loader
 * @param {Object} props
 * @param {number} props.fields - Number of form fields to display
 */
export function FormSkeleton({ fields = 3 }) {
  return (
    <div className="animate-pulse space-y-4">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={`field-${i}`}>
          {/* Label */}
          <div className="h-4 bg-slate-200 rounded w-24 mb-2"></div>
          {/* Input */}
          <div className="h-10 bg-slate-100 rounded-lg"></div>
        </div>
      ))}
      {/* Button */}
      <div className="h-10 bg-slate-200 rounded-lg w-32"></div>
    </div>
  )
}

/**
 * Card Skeleton Loader
 */
export function CardSkeleton() {
  return (
    <div className="card p-6 animate-pulse">
      <div className="h-6 bg-slate-200 rounded w-1/3 mb-4"></div>
      <div className="space-y-3">
        <div className="h-4 bg-slate-100 rounded"></div>
        <div className="h-4 bg-slate-100 rounded w-5/6"></div>
        <div className="h-4 bg-slate-100 rounded w-4/6"></div>
      </div>
    </div>
  )
}

/**
 * Page Skeleton Loader
 * Full page loading state
 */
export function PageSkeleton() {
  return (
    <div className="animate-pulse">
      {/* Page Header */}
      <div className="mb-8">
        <div className="h-8 bg-slate-200 rounded w-1/4 mb-2"></div>
        <div className="h-4 bg-slate-100 rounded w-1/2"></div>
      </div>

      {/* Content Cards */}
      <div className="grid gap-6 md:grid-cols-2">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  )
}
