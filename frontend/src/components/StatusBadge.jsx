/**
 * Status Badge Component
 * Displays color-coded status badges for jobs and results
 */

/**
 * @param {Object} props
 * @param {'QUEUED'|'RUNNING'|'DONE'|'FAILED'|'PENDING'|'APPROVED'|'REJECTED'} props.status
 */
export function StatusBadge({ status }) {
  const getBadgeClass = () => {
    switch (status?.toUpperCase()) {
      case 'QUEUED':
        return 'badge badge-queued'
      case 'RUNNING':
        return 'badge badge-running'
      case 'DONE':
        return 'badge badge-done'
      case 'FAILED':
        return 'badge badge-failed'
      case 'PENDING':
        return 'badge badge-pending'
      case 'APPROVED':
        return 'badge badge-approved'
      case 'REJECTED':
        return 'badge badge-rejected'
      default:
        return 'badge bg-slate-100 text-slate-700'
    }
  }

  return (
    <span className={getBadgeClass()}>
      {status || 'UNKNOWN'}
    </span>
  )
}
