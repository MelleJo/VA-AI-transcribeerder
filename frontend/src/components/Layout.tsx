// src/components/Layout.tsx
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Mic, FileText, Settings, Menu } from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
  { icon: Mic, label: 'Audio Input', path: '/audio' },
  { icon: FileText, label: 'Text Input', path: '/text' },
]

export default function Layout({ children }: LayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-40 h-screen transition-transform ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="h-full px-3 py-4 overflow-y-auto bg-white border-r w-64">
          <div className="flex items-center justify-between mb-6 px-2">
            <h1 className="text-xl font-bold text-gray-800">Summary App</h1>
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
          
          <nav className="space-y-2">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="ml-3">{item.label}</span>
                </Link>
              )
            })}
          </nav>

          <div className="absolute bottom-4 w-full px-3">
            <Link
              to="/settings"
              className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                location.pathname === '/settings'
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Settings className="w-5 h-5" />
              <span className="ml-3">Settings</span>
            </Link>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className={`transition-all ${isSidebarOpen ? 'md:ml-64' : ''} p-6`}>
        {children}
      </main>
    </div>
  )
}