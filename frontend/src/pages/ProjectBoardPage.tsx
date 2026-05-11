import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  GitBranch,
  Users,
  HelpCircle,
  Loader2,
  Clock,
} from 'lucide-react'
import { useProject, useBoard, useSynthesizeBoard, useInterviews } from '../hooks/useInterviews'
import type { BoardTheme, BoardPainPoint, BoardInsight, BoardPattern, BoardDataGap, BoardEvidence } from '../types'

const STRENGTH_COLOR = {
  strong: 'bg-red-500',
  moderate: 'bg-amber-400',
  weak: 'bg-blue-400',
}

const PATTERN_COLOR: Record<string, string> = {
  behavioral: 'border-purple-200 bg-purple-50 text-purple-700',
  demographic: 'border-blue-200 bg-blue-50 text-blue-700',
  contextual: 'border-teal-200 bg-teal-50 text-teal-700',
  emotional: 'border-pink-200 bg-pink-50 text-pink-700',
}

function timeAgo(iso: string) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

// Progress increments: fast early, slows near 90%, snaps to 100 on complete
function useRunningProgress(isRunning: boolean, isComplete: boolean) {
  const [pct, setPct] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (isRunning) {
      setPct(0)
      intervalRef.current = setInterval(() => {
        setPct((prev) => {
          // Asymptotic curve: increment shrinks as we approach 90
          const remaining = 90 - prev
          const step = Math.max(0.3, remaining * 0.025)
          return Math.min(90, prev + step)
        })
      }, 500)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (isComplete) setPct(100)
      else setPct(0)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [isRunning, isComplete])

  return pct
}

const STAGE_LABELS = [
  { at: 0,  label: 'Starting up…' },
  { at: 15, label: 'Reading transcripts…' },
  { at: 35, label: 'Identifying patterns…' },
  { at: 55, label: 'Mapping pain points…' },
  { at: 72, label: 'Synthesizing insights…' },
  { at: 85, label: 'Finalising board…' },
  { at: 100, label: 'Done!' },
]

function currentLabel(pct: number) {
  const stage = [...STAGE_LABELS].reverse().find((s) => pct >= s.at)
  return stage?.label ?? 'Starting up…'
}

export default function ProjectBoardPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: project } = useProject(id!)
  const { data: board, isLoading } = useBoard(id!)
  const synthesize = useSynthesizeBoard(id!)
  const { data: interviewsData } = useInterviews(200, 0, id!)

  // Build title → id map so board references can link to transcripts
  const titleToId = (interviewsData?.items ?? []).reduce<Record<string, string>>(
    (acc, iv) => { acc[iv.title] = iv.id; return acc },
    {}
  )

  const isRunning = board?.status === 'running' || synthesize.isPending
  const hasData = board?.status === 'complete'
  const progress = useRunningProgress(isRunning, hasData)

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Top bar */}
      <div className="sticky top-0 z-20 border-b border-white/10 bg-gray-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(`/projects/${id}`)}
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              {project?.name ?? 'Project'}
            </button>
            <span className="text-gray-700">/</span>
            <span className="flex items-center gap-1.5 text-sm font-medium text-white">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              Research Board
            </span>
          </div>

          <div className="flex items-center gap-3">
            {board?.last_run_at && (
              <span className="flex items-center gap-1.5 text-xs text-gray-500">
                <Clock className="w-3.5 h-3.5" />
                Last run {timeAgo(board.last_run_at)}
              </span>
            )}
            <button
              onClick={() => synthesize.mutate()}
              disabled={isRunning}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors min-w-[160px] justify-center"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
                  <span className="tabular-nums">{Math.round(progress)}%</span>
                  <span className="text-indigo-200 text-xs">{currentLabel(progress)}</span>
                </>
              ) : (
                <><RefreshCw className="w-4 h-4" />{hasData ? 'Re-synthesize' : 'Generate Board'}</>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Loading skeleton */}
        {isLoading && (
          <div className="flex items-center justify-center py-32">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        )}

        {/* Running state — progress bar */}
        {!isLoading && isRunning && !hasData && (
          <div className="flex flex-col items-center justify-center py-32 gap-8 max-w-md mx-auto w-full">
            <div className="w-16 h-16 rounded-full bg-indigo-600/20 flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-indigo-400 animate-pulse" />
            </div>
            <div className="w-full">
              {/* Percentage + label */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-300">{currentLabel(progress)}</span>
                <span className="text-sm font-semibold text-indigo-400 tabular-nums">
                  {Math.round(progress)}%
                </span>
              </div>
              {/* Track */}
              <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
              {/* Stage dots */}
              <div className="flex justify-between mt-3">
                {STAGE_LABELS.filter((s) => s.at > 0 && s.at < 100).map((s) => (
                  <div
                    key={s.at}
                    className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
                      progress >= s.at ? 'bg-indigo-400' : 'bg-white/15'
                    }`}
                  />
                ))}
              </div>
            </div>
            <p className="text-xs text-gray-600 text-center">
              Claude is reading every transcript and finding patterns across your interviews.
              This takes 30–60 seconds.
            </p>
          </div>
        )}

        {/* Empty / not generated yet */}
        {!isLoading && !isRunning && !hasData && board?.status !== 'error' && (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-gray-600" />
            </div>
            <p className="text-lg font-medium text-white">No board generated yet</p>
            <p className="text-sm text-gray-500 text-center max-w-sm">
              Hit "Generate Board" to run cross-interview synthesis across all completed interviews in this project.
            </p>
          </div>
        )}

        {/* Error */}
        {!isLoading && board?.status === 'error' && (
          <div className="bg-red-900/20 border border-red-800 rounded-xl p-5 max-w-lg mx-auto mt-16">
            <p className="text-sm text-red-400">{board.error_message ?? 'Synthesis failed.'}</p>
          </div>
        )}

        {/* Board content */}
        {hasData && board && (
          <div className="space-y-8">
            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Interviews" value={board.interviews_included?.length ?? 0} color="indigo" />
              <StatCard label="Recurring themes" value={board.recurring_themes?.length ?? 0} color="purple" />
              <StatCard label="Pain points" value={board.pain_points?.length ?? 0} color="red" />
              <StatCard label="Patterns found" value={board.patterns?.length ?? 0} color="teal" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recurring themes */}
              {(board.recurring_themes?.length ?? 0) > 0 && (
                <Section icon={TrendingUp} title="Recurring Themes" iconColor="text-indigo-400">
                  <div className="space-y-3">
                    {board.recurring_themes!.map((theme, i) => (
                      <ThemeRow key={i} theme={theme} total={board.interviews_included?.length ?? 1} titleToId={titleToId} />
                    ))}
                  </div>
                </Section>
              )}

              {/* Pain points */}
              {(board.pain_points?.length ?? 0) > 0 && (
                <Section icon={AlertTriangle} title="Top Pain Points" iconColor="text-red-400">
                  <div className="space-y-3">
                    {board.pain_points!.map((pp, i) => (
                      <PainPointRow key={i} pp={pp} total={board.interviews_included?.length ?? 1} titleToId={titleToId} />
                    ))}
                  </div>
                </Section>
              )}
            </div>

            {/* Non-obvious patterns */}
            {(board.patterns?.length ?? 0) > 0 && (
              <Section icon={GitBranch} title="Non-obvious Patterns" iconColor="text-teal-400" fullWidth>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {board.patterns!.map((p, i) => (
                    <PatternCard key={i} pattern={p} />
                  ))}
                </div>
              </Section>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Unique insights */}
              {(board.unique_insights?.length ?? 0) > 0 && (
                <Section icon={Lightbulb} title="Unique Insights" iconColor="text-amber-400">
                  <div className="space-y-3">
                    {board.unique_insights!.map((ins, i) => (
                      <UniqueInsightCard key={i} insight={ins} titleToId={titleToId} />
                    ))}
                  </div>
                </Section>
              )}

              {/* Demographics */}
              {board.demographic_summary && Object.keys(board.demographic_summary).length > 0 && (
                <Section icon={Users} title="Who You Talked To" iconColor="text-blue-400">
                  <DemographicSummary summary={board.demographic_summary as Record<string, unknown>} />
                </Section>
              )}
            </div>

            {/* Data gaps */}
            {(board.data_gaps?.length ?? 0) > 0 && (
              <Section icon={HelpCircle} title="Open Questions & Data Gaps" iconColor="text-orange-400" fullWidth>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {board.data_gaps!.map((gap, i) => (
                    <DataGapCard key={i} gap={gap} />
                  ))}
                </div>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------- Sub-components ----------

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    indigo: 'text-indigo-400 bg-indigo-400/10',
    purple: 'text-purple-400 bg-purple-400/10',
    red: 'text-red-400 bg-red-400/10',
    teal: 'text-teal-400 bg-teal-400/10',
  }
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl px-5 py-4">
      <p className={`text-2xl font-bold ${colors[color].split(' ')[0]}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}

function Section({
  icon: Icon,
  title,
  iconColor,
  children,
  fullWidth,
}: {
  icon: React.ElementType
  title: string
  iconColor: string
  children: React.ReactNode
  fullWidth?: boolean
}) {
  return (
    <div className={`bg-white/5 border border-white/10 rounded-xl p-5 ${fullWidth ? 'col-span-full' : ''}`}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className={`w-4 h-4 ${iconColor}`} />
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function EvidenceDrawer({ evidence, titleToId, accentClass }: {
  evidence: BoardEvidence[]
  titleToId: Record<string, string>
  accentClass: string
}) {
  const navigate = useNavigate()
  return (
    <div className="mt-3 space-y-3 border-t border-white/10 pt-3">
      {evidence.map((ev, i) => {
        const ivId = titleToId[ev.title]
        return (
          <div key={i} className="bg-white/5 rounded-lg p-3 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-300 truncate">{ev.title}</span>
              {ivId && (
                <button
                  onClick={() => navigate(`/interviews/${ivId}`)}
                  className={`text-[10px] px-2 py-0.5 rounded-full border ${accentClass} flex-shrink-0 ml-2 transition-colors`}
                >
                  View transcript →
                </button>
              )}
            </div>
            {ev.insight && (
              <p className="text-xs text-gray-400 leading-relaxed">{ev.insight}</p>
            )}
            {ev.quote && (
              <blockquote className="border-l-2 border-white/20 pl-2 text-xs text-gray-500 italic">
                "{ev.quote}"
              </blockquote>
            )}
          </div>
        )
      })}
    </div>
  )
}

function ThemeRow({ theme, total, titleToId }: { theme: BoardTheme; total: number; titleToId: Record<string, string> }) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.round((theme.count / total) * 100)
  const hasEvidence = theme.interviews?.length > 0
  return (
    <div>
      <div
        className={`flex items-center justify-between mb-1 ${hasEvidence ? 'cursor-pointer' : ''}`}
        onClick={() => hasEvidence && setExpanded((e) => !e)}
      >
        <span className="text-sm text-gray-200">{theme.name}</span>
        <span className={`text-xs ml-3 flex-shrink-0 ${hasEvidence ? 'text-indigo-400 hover:text-indigo-300' : 'text-gray-500'}`}>
          {theme.count}/{total}{hasEvidence ? (expanded ? ' ▲' : ' ▼') : ''}
        </span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${STRENGTH_COLOR[theme.strength] ?? 'bg-indigo-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {theme.description && (
        <p className="text-xs text-gray-500 mt-1">{theme.description}</p>
      )}
      {expanded && hasEvidence && (
        <EvidenceDrawer
          evidence={theme.interviews}
          titleToId={titleToId}
          accentClass="border-indigo-500/40 text-indigo-400 hover:bg-indigo-500/20"
        />
      )}
    </div>
  )
}

function PainPointRow({ pp, total, titleToId }: { pp: BoardPainPoint; total: number; titleToId: Record<string, string> }) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.round((pp.count / total) * 100)
  const hasEvidence = pp.interviews?.length > 0
  return (
    <div>
      <div
        className={`flex items-center justify-between mb-1 ${hasEvidence ? 'cursor-pointer' : ''}`}
        onClick={() => hasEvidence && setExpanded((e) => !e)}
      >
        <span className="text-sm text-gray-200 leading-snug">{pp.text}</span>
        <span className={`text-xs ml-3 flex-shrink-0 ${hasEvidence ? 'text-red-400 hover:text-red-300' : 'text-gray-500'}`}>
          {pp.count}/{total}{hasEvidence ? (expanded ? ' ▲' : ' ▼') : ''}
        </span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className="h-full rounded-full bg-red-500" style={{ width: `${pct}%` }} />
      </div>
      {expanded && hasEvidence && (
        <EvidenceDrawer
          evidence={pp.interviews}
          titleToId={titleToId}
          accentClass="border-red-500/40 text-red-400 hover:bg-red-500/20"
        />
      )}
    </div>
  )
}

function PatternCard({ pattern }: { pattern: BoardPattern }) {
  const cls = PATTERN_COLOR[pattern.type] ?? 'border-gray-200 bg-gray-50 text-gray-700'
  return (
    <div className="bg-white/5 border border-white/10 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${cls}`}>
          {pattern.type}
        </span>
      </div>
      <p className="text-sm font-medium text-white mb-1">{pattern.title}</p>
      <p className="text-xs text-gray-400 leading-relaxed">{pattern.description}</p>
      {pattern.evidence && (
        <p className="text-xs text-gray-600 mt-2 italic">{pattern.evidence}</p>
      )}
    </div>
  )
}

function UniqueInsightCard({ insight, titleToId }: { insight: BoardInsight; titleToId: Record<string, string> }) {
  const navigate = useNavigate()
  const ivId = titleToId[insight.interview]
  return (
    <div className="border border-amber-500/20 bg-amber-500/5 rounded-lg p-4">
      <p className="text-sm text-gray-200 mb-2">{insight.text}</p>
      {insight.quote && (
        <p className="text-xs text-amber-400/70 italic mb-2">"{insight.quote}"</p>
      )}
      <div className="flex items-center justify-between">
        {ivId ? (
          <button
            onClick={() => navigate(`/interviews/${ivId}`)}
            className="text-xs text-amber-500/70 hover:text-amber-400 underline underline-offset-2 transition-colors"
          >
            {insight.interview}
          </button>
        ) : (
          <span className="text-xs text-gray-600">{insight.interview}</span>
        )}
        {insight.why_notable && (
          <span className="text-xs text-amber-500/60 ml-2 text-right">{insight.why_notable}</span>
        )}
      </div>
    </div>
  )
}

function DemographicSummary({ summary }: { summary: Record<string, unknown> }) {
  const sections = [
    { key: 'roles', label: 'Roles' },
    { key: 'industries', label: 'Industries' },
    { key: 'locations', label: 'Locations' },
    { key: 'age_ranges', label: 'Age ranges' },
    { key: 'tech_levels', label: 'Tech level' },

  ]

  return (
    <div className="space-y-3">
      {sections.map(({ key, label }) => {
        const val = summary[key]
        if (!val) return null
        const items = Array.isArray(val)
          ? val.map((v) => String(v))
          : Object.entries(val as Record<string, number>).map(([k, n]) => `${k} (${n})`)
        if (!items.length) return null
        return (
          <div key={key}>
            <p className="text-xs text-gray-500 mb-1.5 uppercase tracking-wide">{label}</p>
            <div className="flex flex-wrap gap-1.5">
              {items.map((item) => (
                <span
                  key={item}
                  className="text-xs bg-white/10 text-gray-300 px-2 py-0.5 rounded-full"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function DataGapCard({ gap }: { gap: BoardDataGap }) {
  return (
    <div className="border border-orange-500/20 bg-orange-500/5 rounded-lg p-4">
      <p className="text-sm font-medium text-orange-300 mb-1">{gap.question}</p>
      {gap.context && <p className="text-xs text-gray-500 mb-2">{gap.context}</p>}
      {gap.missing_in > 0 && (
        <span className="text-xs text-orange-500/60">
          Unclear in {gap.missing_in} interview{gap.missing_in !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  )
}
