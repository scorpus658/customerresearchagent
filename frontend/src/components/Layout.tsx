import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Mic, Upload, FolderOpen, List, Zap, Brain } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Projects', icon: FolderOpen, exact: true },
  { to: '/interviews', label: 'All Interviews', icon: List, exact: true },
  { to: '/upload', label: 'Upload', icon: Upload, exact: false },
]

export type SynthesisModel = 'haiku' | 'sonnet'

export function getSynthesisModel(): SynthesisModel {
  return (localStorage.getItem('synthesis_model') as SynthesisModel) ?? 'haiku'
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [model, setModel] = useState<SynthesisModel>(getSynthesisModel)

  const toggleModel = () => {
    const next: SynthesisModel = model === 'haiku' ? 'sonnet' : 'haiku'
    localStorage.setItem('synthesis_model', next)
    setModel(next)
  }

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

          <div className="flex items-center gap-3">
            {/* Model toggle */}
            <button
              onClick={toggleModel}
              title={model === 'haiku' ? 'Switch to Sonnet (better quality)' : 'Switch to Haiku (faster)'}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                model === 'sonnet'
                  ? 'bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100'
                  : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
              }`}
            >
              {model === 'sonnet' ? <Brain className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
              {model === 'sonnet' ? 'Sonnet' : 'Haiku'}
            </button>

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
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
