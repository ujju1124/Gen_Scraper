/**
 * Progress Bar Component
 * Displays data completeness with color coding
 * Red (<50%), Yellow (50-80%), Green (>80%)
 */

/**
 * @param {Object} props
 * @param {number} props.percentage - Completeness percentage (0-100)
 */
export function ProgressBar({ percentage }) {
  // Handle null/undefined percentage
  const safePercentage = percentage ?? 0
  const clampedPercentage = Math.min(100, Math.max(0, safePercentage))
  
  const getColor = () => {
    if (safePercentage < 50) return 'bg-red-500'
    if (safePercentage < 80) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getTextColor = () => {
    if (safePercentage < 50) return 'text-red-700'
    if (safePercentage < 80) return 'text-yellow-700'
    return 'text-green-700'
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className={`text-xs font-medium ${getTextColor()}`}>
          {Math.round(safePercentage)}%
        </span>
      </div>
      <div 
        className="w-full bg-slate-200 rounded-full h-2"
        role="progressbar"
        aria-valuenow={clampedPercentage}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-2 rounded-full transition-all duration-300 ${getColor()}`}
          style={{ width: `${clampedPercentage}%` }}
        ></div>
      </div>
    </div>
  )
}
