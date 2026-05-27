import { useState, useEffect } from 'react'
import { Key, Save, Eye, EyeOff } from 'lucide-react'

export default function ApiSettings() {
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const storedKey = localStorage.getItem('gmaps_api_key') || ''
    setApiKey(storedKey)
  }, [])

  const handleSave = () => {
    localStorage.setItem('gmaps_api_key', apiKey)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            API Settings
          </h2>
        </div>
      </div>

      <div className="mt-8 max-w-3xl">
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 flex items-center">
              <Key className="h-5 w-5 mr-2 text-gray-400" />
              API Key Configuration
            </h3>
            <div className="mt-2 max-w-xl text-sm text-gray-500">
              <p>
                Enter your API key to authenticate requests to the Google Maps Scraper backend.
                You can generate an API key from the admin dashboard.
              </p>
            </div>
            <div className="mt-5">
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your API key"
                  className="block w-full pr-10 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                >
                  {showKey ? (
                    <EyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <button
                  onClick={handleSave}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save API Key
                </button>
                {saved && (
                  <span className="text-sm text-green-600 font-medium">
                    ✓ Saved successfully
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* API Documentation */}
        <div className="mt-8 bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              API Documentation
            </h3>
            <div className="mt-4 text-sm text-gray-500 space-y-4">
              <div>
                <h4 className="font-medium text-gray-900">Backend URL</h4>
                <code className="mt-1 block bg-gray-100 px-3 py-2 rounded">
                  http://localhost:8080
                </code>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900">Available Endpoints</h4>
                <ul className="mt-2 space-y-2">
                  <li>
                    <code className="bg-gray-100 px-2 py-1 rounded text-xs">POST /api/v1/scrape</code>
                    <span className="ml-2">Submit a new scrape job</span>
                  </li>
                  <li>
                    <code className="bg-gray-100 px-2 py-1 rounded text-xs">GET /api/v1/jobs</code>
                    <span className="ml-2">List all jobs</span>
                  </li>
                  <li>
                    <code className="bg-gray-100 px-2 py-1 rounded text-xs">GET /api/v1/jobs/:id</code>
                    <span className="ml-2">Get job details</span>
                  </li>
                  <li>
                    <code className="bg-gray-100 px-2 py-1 rounded text-xs">DELETE /api/v1/jobs/:id</code>
                    <span className="ml-2">Delete a job</span>
                  </li>
                </ul>
              </div>

              <div>
                <h4 className="font-medium text-gray-900">Swagger Documentation</h4>
                <p className="mt-1">
                  Full API documentation is available at:{' '}
                  <a
                    href="http://localhost:8080/swagger/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800"
                  >
                    http://localhost:8080/swagger/
                  </a>
                </p>
              </div>

              <div>
                <h4 className="font-medium text-gray-900">Authentication</h4>
                <p className="mt-1">
                  All API requests require an API key in the <code className="bg-gray-100 px-1 rounded">X-API-Key</code> header.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
