import { useState, useMemo } from 'react'
import { Search, Globe, Eye, EyeOff } from 'lucide-react'
import type { TranscriptSegment } from '../types'

const SPEAKER_COLORS = [
  'text-blue-700 bg-blue-50',
  'text-emerald-700 bg-emerald-50',
  'text-purple-700 bg-purple-50',
  'text-orange-700 bg-orange-50',
  'text-pink-700 bg-pink-50',
  'text-teal-700 bg-teal-50',
]

function formatTime(seconds: number | null) {
  if (seconds === null) return '--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

interface TranscriptViewerProps {
  segments: TranscriptSegment[]
}

export default function TranscriptViewer({ segments }: TranscriptViewerProps) {
  const [search, setSearch] = useState('')
  const [showTranslations, setShowTranslations] = useState(true)

  const speakerColorMap = useMemo(() => {
    const map = new Map<string, string>()
    const speakers = [...new Set(segments.map((s) => s.speaker))]
    speakers.forEach((s, i) => map.set(s, SPEAKER_COLORS[i % SPEAKER_COLORS.length]))
    return map
  }, [segments])

  const filtered = useMemo(() => {
    if (!search.trim()) return segments
    const q = search.toLowerCase()
    return segments.filter(
      (s) =>
        s.text.toLowerCase().includes(q) ||
        s.speaker.toLowerCase().includes(q) ||
        s.translated_text?.toLowerCase().includes(q),
    )
  }, [segments, search])

  if (segments.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-sm">No transcript available yet.</p>
      </div>
    )
  }

  const hasTranslations = segments.some((s) => s.translated_text)

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search transcript..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
          />
        </div>
        {hasTranslations && (
          <button
            onClick={() => setShowTranslations(!showTranslations)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {showTranslations ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            Translations
          </button>
        )}
      </div>

      <div className="space-y-1">
        {filtered.map((seg, i) => {
          const colorClass = speakerColorMap.get(seg.speaker) ?? SPEAKER_COLORS[0]
          const isNonEnglish = seg.language && seg.language !== 'en'

          return (
            <div
              key={i}
              className="flex gap-3 py-2 px-3 rounded-lg hover:bg-gray-50/50 group"
            >
              <span className="text-xs text-gray-400 pt-0.5 w-10 shrink-0 tabular-nums text-right">
                {formatTime(seg.start_time)}
              </span>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span
                    className={`text-xs font-medium px-1.5 py-0.5 rounded ${colorClass}`}
                  >
                    {seg.speaker}
                  </span>
                  {isNonEnglish && (
                    <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 uppercase">
                      <Globe className="w-3 h-3" />
                      {seg.language}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-800 leading-relaxed">{seg.text}</p>
                {showTranslations && seg.translated_text && (
                  <p className="text-sm text-gray-500 italic mt-1 pl-3 border-l-2 border-blue-200">
                    {seg.translated_text}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && search && (
        <div className="text-center py-8 text-gray-400 text-sm">
          No segments match &ldquo;{search}&rdquo;
        </div>
      )}
    </div>
  )
}
