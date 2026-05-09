import { Link, useLocation } from 'react-router-dom'
import { Mic, Upload, FolderOpen, List } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Projects', icon: FolderOpen, exact: true },
  { to: '/interviews', label: 'All Interviews', icon: List, exact: true },
  { to: '/upload', label: 'Upload', icon: Upload, exact: false },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="border-b border-[var(--color-border)] bg-white sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 text-[var(--color-text)] no-underline">
            <Mic className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-[15px] tracking-tight">
              Customer Research Agent
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon, exact }) => {
              const active = exact ? location.pathname === to : location.pathname.startsWith(to)
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm no-underline transition-colors ${
                    active
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
