import { useState, useEffect } from "react"
import api from "../services/api"

export default function HealingDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/admin/healing-stats')
      .then(r => { 
        setStats(r.data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load healing stats:', err)
        setError('Failed to load healing statistics')
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading healing statistics...</div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">{error || 'Failed to load data'}</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Self-Healing System</h1>
        <p className="text-gray-600 mt-1">
          Automatic selector healing attempts and success rates
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Attempts"
          value={stats.total_attempts}
          color="blue"
          icon="🔧"
        />
        <StatCard
          title="Auto-Resolved"
          value={stats.resolved}
          color="green"
          icon="✅"
        />
        <StatCard
          title="Success Rate"
          value={stats.success_rate + "%"}
          color="purple"
          icon="📊"
        />
        <StatCard
          title="Avg Confidence"
          value={stats.avg_confidence.toFixed(2)}
          color="orange"
          icon="🎯"
        />
      </div>

      {/* Recent Heals Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Healing Activity</h2>
          <p className="text-sm text-gray-600 mt-1">
            Last 20 automatic healing attempts
          </p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="p-3 text-left font-medium text-gray-700">Source</th>
                <th className="p-3 text-left font-medium text-gray-700">Field</th>
                <th className="p-3 text-left font-medium text-gray-700">Old Selector</th>
                <th className="p-3 text-left font-medium text-gray-700">New Selector</th>
                <th className="p-3 text-left font-medium text-gray-700">Confidence</th>
                <th className="p-3 text-left font-medium text-gray-700">Status</th>
                <th className="p-3 text-left font-medium text-gray-700">Time</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_heals.map((h, i) => (
                <tr 
                  key={i}
                  className={`border-b border-gray-100 ${
                    h.status === 'RESOLVED' 
                      ? 'bg-green-50 hover:bg-green-100' 
                      : 'bg-yellow-50 hover:bg-yellow-100'
                  } transition-colors`}
                >
                  <td className="p-3">
                    <span className="font-medium text-gray-900">{h.source_name}</span>
                  </td>
                  <td className="p-3">
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                      {h.field_name}
                    </code>
                  </td>
                  <td className="p-3">
                    <code className="text-xs text-red-600 max-w-xs truncate block" title={h.old_selector}>
                      {h.old_selector || '—'}
                    </code>
                  </td>
                  <td className="p-3">
                    <code className="text-xs text-green-600 max-w-xs truncate block" title={h.new_selector}>
                      {h.new_selector || '—'}
                    </code>
                  </td>
                  <td className="p-3">
                    <span className={`font-bold ${
                      h.confidence >= 0.7 
                        ? 'text-green-600' 
                        : h.confidence > 0 
                        ? 'text-orange-500' 
                        : 'text-gray-400'
                    }`}>
                      {h.confidence ? h.confidence.toFixed(2) : '—'}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      h.status === 'RESOLVED'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {h.status}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500 text-xs">
                    {new Date(h.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {stats.recent_heals.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No healing attempts recorded yet
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="text-blue-600 text-2xl mr-3">ℹ️</div>
          <div>
            <h3 className="font-semibold text-blue-900 mb-1">About Self-Healing</h3>
            <p className="text-sm text-blue-800">
              When a scraper fails to extract data, the self-healing system automatically 
              analyzes the page structure and attempts to find a working selector. 
              Heals with confidence ≥ 0.7 are automatically applied. Lower confidence heals 
              are marked as PENDING for manual review.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, color, icon }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
  }

  return (
    <div className={`p-4 rounded-lg border ${colors[color]} transition-shadow hover:shadow-md`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm opacity-75">{title}</div>
        <div className="text-2xl">{icon}</div>
      </div>
      <div className="text-3xl font-bold mt-1">{value}</div>
    </div>
  )
}
