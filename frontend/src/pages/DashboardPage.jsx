/**
 * Dashboard Page
 * Main user dashboard with job creation form and job history table
 */
import { JobCreationForm } from '../components/dashboard/JobCreationForm'
import { JobHistoryTable } from '../components/dashboard/JobHistoryTable'

export function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600">
          Create new scraping jobs and monitor their progress
        </p>
      </div>

      {/* Job Creation Form */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Create New Job</h2>
        <JobCreationForm />
      </div>

      {/* Job History */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Job History</h2>
        <JobHistoryTable />
      </div>
    </div>
  )
}
