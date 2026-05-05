/**
 * Job Creation Form Component
 * Form for creating new scraping jobs with category, location, source selection,
 * and result limit control.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import * as jobService from '../../services/jobService'

// Preset options — null means "scrape everything"
const RESULT_LIMIT_PRESETS = [
  { label: '25', value: 25 },
  { label: '100', value: 100 },
  { label: '500', value: 500 },
  { label: '1,000', value: 1000 },
  { label: '5,000', value: 5000 },
  { label: 'Max', value: null },
]

export function JobCreationForm() {
  const [categories, setCategories] = useState([])
  const [sources, setSources] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [location, setLocation] = useState('')
  const [selectedSources, setSelectedSources] = useState([])
  const [resultLimit, setResultLimit] = useState(null)       // null = max
  const [customLimit, setCustomLimit] = useState('')          // free-text custom value
  const [useCustom, setUseCustom] = useState(false)          // toggle custom input
  const [loading, setLoading] = useState(false)
  const [loadingCategories, setLoadingCategories] = useState(true)
  const [loadingSources, setLoadingSources] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  // Fetch categories on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await jobService.getCategories()
        setCategories(data.items || data)
      } catch (err) {
        setError('Failed to load categories')
        console.error('Error fetching categories:', err)
      } finally {
        setLoadingCategories(false)
      }
    }
    fetchCategories()
  }, [])

  // Fetch sources when category changes
  useEffect(() => {
    if (!selectedCategory) {
      setSources([])
      setSelectedSources([])
      return
    }
    const fetchSources = async () => {
      setLoadingSources(true)
      try {
        const data = await jobService.getSourcesForCategory(selectedCategory)
        setSources(data)
        setSelectedSources([])
      } catch (err) {
        setError('Failed to load sources for this category')
        console.error('Error fetching sources:', err)
        setSources([])
      } finally {
        setLoadingSources(false)
      }
    }
    fetchSources()
  }, [selectedCategory])

  const handleSourceToggle = (sourceId) => {
    setSelectedSources(prev =>
      prev.includes(sourceId)
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    )
  }

  const handlePresetClick = (value) => {
    setUseCustom(false)
    setCustomLimit('')
    setResultLimit(value)
  }

  const handleCustomToggle = () => {
    setUseCustom(true)
    setResultLimit(null)
    setCustomLimit('')
  }

  const handleCustomChange = (e) => {
    const raw = e.target.value.replace(/\D/g, '') // digits only
    setCustomLimit(raw)
    setResultLimit(raw ? parseInt(raw, 10) : null)
  }

  // Compute the effective limit for display
  const effectiveLimit = useCustom
    ? (customLimit ? parseInt(customLimit, 10) : null)
    : resultLimit

  const validateForm = () => {
    if (!selectedCategory) {
      setError('Please select a category')
      return false
    }
    if (!location.trim()) {
      setError('Please enter a location')
      return false
    }
    if (selectedSources.length === 0) {
      setError('Please select at least one source')
      return false
    }
    if (useCustom && customLimit && parseInt(customLimit, 10) < 1) {
      setError('Result limit must be at least 1')
      return false
    }
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!validateForm()) return

    setLoading(true)
    try {
      const jobData = {
        category_id: parseInt(selectedCategory),
        location: location.trim(),
        source_ids: selectedSources,
        max_results: effectiveLimit,  // null = scrape all
      }
      const createdJob = await jobService.createJob(jobData)
      navigate(`/jobs/${createdJob.id}`)
    } catch (err) {
      setError(err.message || 'Failed to create job. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loadingCategories) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p className="mt-2 text-sm text-slate-600">Loading categories...</p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* Category Dropdown */}
      <div>
        <label htmlFor="category" className="block text-sm font-medium text-slate-700 mb-1.5">
          Category
        </label>
        <select
          id="category"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="input w-full"
          disabled={loading}
        >
          <option value="">Select a category</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.display_name}
            </option>
          ))}
        </select>
      </div>

      {/* Location Input */}
      <div>
        <label htmlFor="location" className="block text-sm font-medium text-slate-700 mb-1.5">
          Location
        </label>
        <input
          id="location"
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="input w-full"
          placeholder="e.g., Kathmandu, Pokhara"
          disabled={loading}
        />
      </div>

      {/* ── Result Limit ── */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Result Limit
          <span className="ml-1.5 text-xs font-normal text-slate-400">(per source)</span>
        </label>

        {/* Preset buttons */}
        <div className="flex flex-wrap gap-2 mb-2">
          {RESULT_LIMIT_PRESETS.map((opt) => {
            const isActive = !useCustom && resultLimit === opt.value
            return (
              <button
                key={String(opt.value)}
                type="button"
                onClick={() => handlePresetClick(opt.value)}
                disabled={loading}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium border transition-colors focus:outline-none focus:ring-2 focus:ring-primary-400 ${
                  isActive
                    ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                    : 'bg-white text-slate-600 border-slate-300 hover:border-primary-400 hover:text-primary-600'
                }`}
              >
                {opt.label}
              </button>
            )
          })}

          {/* Custom button */}
          <button
            type="button"
            onClick={handleCustomToggle}
            disabled={loading}
            className={`px-3.5 py-1.5 rounded-lg text-sm font-medium border transition-colors focus:outline-none focus:ring-2 focus:ring-primary-400 ${
              useCustom
                ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                : 'bg-white text-slate-600 border-slate-300 hover:border-primary-400 hover:text-primary-600'
            }`}
          >
            Custom
          </button>
        </div>

        {/* Custom number input — shown only when "Custom" is selected */}
        {useCustom && (
          <div className="flex items-center gap-2 mt-1">
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={customLimit}
              onChange={handleCustomChange}
              placeholder="e.g. 300"
              disabled={loading}
              className="input w-32 text-sm"
              autoFocus
            />
            <span className="text-xs text-slate-500">results per source</span>
          </div>
        )}

        {/* Helper text */}
        <p className="mt-1.5 text-xs text-slate-500">
          {effectiveLimit === null
            ? '✦ Max — scrape all available listings across all pages.'
            : `Stop after ${effectiveLimit.toLocaleString()} results per source. If fewer exist, all are returned.`}
        </p>
      </div>

      {/* Source Multi-Select */}
      {selectedCategory && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Sources
          </label>
          {loadingSources ? (
            <div className="text-center py-4">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-sm text-slate-600">Loading sources...</p>
            </div>
          ) : sources.length === 0 ? (
            <p className="text-sm text-slate-500 py-2">No active sources available for this category</p>
          ) : (
            <>
              <div className="space-y-2 border border-slate-200 rounded-lg p-3 max-h-48 overflow-y-auto">
                {sources.filter(source => source.name !== 'google_maps').map((source) => (
                  <label
                    key={source.id}
                    className="flex items-center space-x-2 cursor-pointer hover:bg-slate-50 p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={selectedSources.includes(source.id)}
                      onChange={() => handleSourceToggle(source.id)}
                      className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                      disabled={loading}
                    />
                    <span className="text-sm text-slate-700">{source.display_name}</span>
                  </label>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-600 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 flex items-start gap-2">
                <span className="text-blue-600 flex-shrink-0">ℹ️</span>
                <span>Google Maps data is always included automatically for richer results.</span>
              </p>
            </>
          )}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || !selectedCategory || !location.trim() || selectedSources.length === 0}
        className="btn btn-primary w-full"
      >
        {loading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Creating Job...
          </span>
        ) : (
          'Create Job'
        )}
      </button>
    </form>
  )
}
