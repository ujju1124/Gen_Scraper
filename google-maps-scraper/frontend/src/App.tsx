import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Map, List, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import NewJob from './pages/NewJob'
import JobDetails from './pages/JobDetails'
import ApiSettings from './pages/ApiSettings'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <Link to="/" className="flex items-center px-2 text-gray-900 font-semibold text-lg">
                  <Map className="h-6 w-6 mr-2 text-blue-600" />
                  Google Maps Scraper
                </Link>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 border-b-2 border-transparent hover:border-gray-300"
                  >
                    <List className="h-4 w-4 mr-1" />
                    Jobs
                  </Link>
                  <Link
                    to="/new"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:border-gray-300 hover:text-gray-700"
                  >
                    New Job
                  </Link>
                  <Link
                    to="/settings"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:border-gray-300 hover:text-gray-700"
                  >
                    <Settings className="h-4 w-4 mr-1" />
                    Settings
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new" element={<NewJob />} />
            <Route path="/jobs/:jobId" element={<JobDetails />} />
            <Route path="/settings" element={<ApiSettings />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
