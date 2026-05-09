import {
  AlertTriangle,
  Target,
  ShieldAlert,
  Lightbulb,
  Wrench,
  Heart,
  Quote,
} from 'lucide-react'
import type { Insight } from '../types'

const categoryIcons: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  'Pain Points':       { icon: AlertTriangle, color: 'text-red-600',    bg: 'bg-red-50' },
  'Goals':             { icon: Target,        color: 'text-blue-600',   bg: 'bg-blue-50' },
  'Objections':        { icon: ShieldAlert,   color: 'text-orange-600', bg: 'bg-orange-50' },
  'Feature Requests':  { icon: Lightbulb,     color: 'text-amber-600',  bg: 'bg-amber-50' },
  'Workarounds':       { icon: Wrench,        color: 'text-gray-600',   bg: 'bg-gray-50' },
  'Emotional Moments': { icon: Heart,         color: 'text-pink-600',   bg: 'bg-pink-50' },
  'Key Quotes':        { icon: Quote,         color: 'text-indigo-600', bg: 'bg-indigo-50' },
}

const defaultCfg = { icon: Quote, color: 'text-indigo-600', bg: 'bg-indigo-50' }

function formatTimestamp(seconds: number | null) {
  if (seconds === null) return null
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

interface InsightCardProps {
  insight: Insight
  categoryLabel: string
}

export default function InsightCard({ insight, categoryLabel }: InsightCardProps) {
  const cfg = categoryIcons[categoryLabel] ?? defaultCfg
  const Icon = cfg.icon
  const confidencePct = Math.round(insight.confidence * 100)

  return (
    <div className="border border-gray-200 rounded-lg bg-white p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${cfg.bg} shrink-0`}>
          <Icon className={`w-4 h-4 ${cfg.color}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-medium ${cfg.color}`}>{categoryLabel}</span>
            {insight.category && (
              <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{insight.category}</span>
            )}
            <div className="flex items-center gap-1 ml-auto">
              <div className="w-12 h-1 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    confidencePct >= 80 ? 'bg-green-400' : confidencePct >= 50 ? 'bg-amber-400' : 'bg-red-400'
                  }`}
                  style={{ width: `${confidencePct}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-400 w-8 text-right">{confidencePct}%</span>
            </div>
          </div>

          <p className="text-sm text-gray-900 mb-2">{insight.text}</p>

          {insight.quote && (
            <blockquote className="text-sm border-l-2 border-gray-200 pl-3 text-gray-500 italic mb-2">
              &ldquo;{insight.quote}&rdquo;
            </blockquote>
          )}

          {insight.translated_quote && (
            <div className="text-xs text-gray-400 italic mb-2 pl-3 border-l-2 border-blue-200">
              Translation: {insight.translated_quote}
            </div>
          )}

          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="font-medium text-gray-500">{insight.speaker}</span>
            {insight.timestamp !== null && (
              <span>{formatTimestamp(insight.timestamp)}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
