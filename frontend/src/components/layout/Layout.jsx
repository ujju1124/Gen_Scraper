/**
 * Layout Component
 * Main layout wrapper with navigation and content areas
 */
import { Navigation } from './Navigation'

/**
 * @param {Object} props
 * @param {React.ReactNode} props.children - Page content
 */
export function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
