import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  RotateCcw,
  Trash2,
  FileText,
  MessageSquare,
  BarChart3,
  ClipboardList,
  Clock,
  Globe,
  HardDrive,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import TranscriptViewer from '../components/TranscriptViewer'
import InsightCard from '../components/InsightCard'
import ReportEditor from '../components/ReportEditor'
import ConfirmDialog from '../components/ConfirmDialog'
import {
  useInterviewDetail,
  useDeleteInterview,
  useReprocessInterview,
  useUpdateReport,
  useExportReport,
  useProfile,
  useUpdateProfile,
} from '../hooks/useInterviews'
import ProfilePromptModal from '../components/ProfilePromptModal'
import type { InsightCategory, Insight } from '../types'

const TABS = [
  { key: 'overview', label: 'Overview', icon: ClipboardList },
  { key: 'transcript', label: 'Transcript', icon: MessageSquare },
  { key: 'analysis', label: 'Analysis', icon: BarChart3 },
  { key: 'report', label: 'Report', icon: FileText },
] as const

type TabKey = (typeof TABS)[number]['key']

const PIPELINE_STAGES = ['uploaded', 'transcribing', 'analyzing', 'synthesizing', 'complete'] as const

const STAGE_PERCENT: Record<string, number> = {
  uploaded: 5,
  transcribing: 30,
  analyzing: 60,
  synthesizing: 85,
  complete: 100,
  error: 0,
}

const STAGE_DESCRIPTIONS: Record<string, string> = {
  uploaded: 'File received. Queuing for processing…',
  transcribing: 'Converting audio to text. This may take a few minutes for longer files.',
  analyzing: 'Extracting pain points, goals, quotes, and other insights from the transcript.',
  synthesizing: 'Generating executive summary, themes, and recommendations.',
  complete: 'All processing complete.',
}

const INSIGHT_CATEGORIES: InsightCategory[] = [
  'pain_points',
  'goals',
  'objections',
  'feature_requests',
  'workarounds',
  'emotional_moments',
  'strong_quotes',
]

const CATEGORY_LABELS: Record<InsightCategory, string> = {
  pain_points: 'Pain Points',
  goals: 'Goals',
  objections: 'Objections',
  feature_requests: 'Feature Requests',
  workarounds: 'Workarounds',
  emotional_moments: 'Emotional Moments',
  strong_quotes: 'Key Quotes',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function InterviewDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<TabKey>('overview')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [analysisFilter, setAnalysisFilter] = useState<InsightCategory | 'all'>('all')
  const [profileDismissed, setProfileDismissed] = useState(false)

  const detailQ = useInterviewDetail(id!)
  const detail = detailQ.data
  const interview = detail?.interview

  // Live elapsed time while processing
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!interview || ['complete', 'error'].includes(interview.status)) return
    const start = new Date(interview.created_at).getTime()
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [interview?.status, interview?.created_at])
  const transcript = detail?.transcript
  const analysis = detail?.analysis
  const report = detail?.report

  const canShowTranscript = interview && ['analyzing', 'synthesizing', 'complete'].includes(interview.status)
  const canShowAnalysis = interview && ['synthesizing', 'complete'].includes(interview.status)
  const canShowReport = interview?.status === 'complete'

  const deleteMutation = useDeleteInterview()
  const reprocessMutation = useReprocessInterview()
  const updateReportMutation = useUpdateReport(id!)
  const exportMutation = useExportReport()
  const profileQuery = useProfile(id!, interview?.status === 'complete')
  const updateProfileMutation = useUpdateProfile(id!)

  const showProfilePrompt =
    !profileDismissed &&
    interview?.status === 'complete' &&
    profileQuery.data?.user_filled === 'no' &&
    (profileQuery.data?.missing_fields?.length ?? 0) > 0

  const handleDelete = async () => {
    setShowDeleteConfirm(false)
    await deleteMutation.mutateAsync(id!)
    navigate('/')
  }

  if (detailQ.isLoading) {
    return (
      <div className="text-center py-20">
        <Loader2 className="w-6 h-6 text-blue-600 animate-spin mx-auto" />
        <p className="text-sm text-gray-400 mt-3">Loading interview...</p>
      </div>
    )
  }

  if (detailQ.isError || !interview) {
    return (
      <div className="text-center py-20">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-600">Failed to load interview.</p>
        <button onClick={() => navigate('/')} className="text-sm text-blue-600 hover:underline mt-2">
          Back to list
        </button>
      </div>
    )
  }

  const allInsights: { category: InsightCategory; insight: Insight }[] = []
  if (analysis) {
    for (const cat of INSIGHT_CATEGORIES) {
      const items = analysis[cat] ?? []
      for (const insight of items) {
        allInsights.push({ category: cat, insight })
      }
    }
  }

  const filteredInsights =
    analysisFilter === 'all'
      ? allInsights
      : allInsights.filter((i) => i.category === analysisFilter)

  const insightCountByCategory = INSIGHT_CATEGORIES.reduce(
    (acc, cat) => {
      const count = analysis?.[cat]?.length ?? 0
      if (count > 0) acc[cat] = count
      return acc
    },
    {} as Partial<Record<InsightCategory, number>>,
  )

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {interview.title || interview.original_filename}
            </h1>
            <div className="mt-1.5">
              <StatusBadge status={interview.status} />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {canShowReport && (
              <button
                onClick={() => exportMutation.mutate(id!)}
                disabled={exportMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                Export
              </button>
            )}
            <button
              onClick={() => reprocessMutation.mutate(id!)}
              disabled={reprocessMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              <RotateCcw className="w-4 h-4" />
              Reprocess
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-0.5">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors ${
                tab === key
                  ? 'border-blue-600 text-blue-600 font-medium'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="space-y-6">
          <div className="border border-gray-200 rounded-lg bg-white p-5">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-gray-900">Processing Pipeline</h3>
              {interview.status !== 'complete' && interview.status !== 'error' && (
                <span className="text-xs text-gray-400 tabular-nums">
                  {Math.floor(elapsed / 60)}m {String(elapsed % 60).padStart(2, '0')}s elapsed
                </span>
              )}
            </div>

            {/* Percentage bar */}
            {interview.status !== 'error' && (
              <div className="mb-5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-gray-500 capitalize">
                    {interview.status === 'complete' ? 'Complete' : interview.status}
                  </span>
                  <span className="text-xs font-semibold text-blue-600">
                    {STAGE_PERCENT[interview.status] ?? 0}%
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      interview.status === 'complete' ? 'bg-green-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${STAGE_PERCENT[interview.status] ?? 0}%` }}
                  />
                </div>
                {interview.status !== 'complete' && (
                  <p className="text-xs text-gray-400 mt-2">
                    {STAGE_DESCRIPTIONS[interview.status]}
                  </p>
                )}
              </div>
            )}

            {/* Step list */}
            <div className="space-y-3">
              {PIPELINE_STAGES.map((stage) => {
                const stageIdx = PIPELINE_STAGES.indexOf(interview.status as typeof stage)
                const currentIdx = interview.status === 'error' ? -1 : stageIdx
                const thisIdx = PIPELINE_STAGES.indexOf(stage)
                const isDone = thisIdx < currentIdx || interview.status === 'complete'
                const isCurrent = thisIdx === currentIdx && interview.status !== 'complete'

                return (
                  <div key={stage} className="flex items-center gap-3">
                    <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                      {isDone ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      ) : isCurrent ? (
                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border-2 border-gray-200" />
                      )}
                    </div>
                    <span
                      className={`text-sm capitalize ${
                        isDone
                          ? 'text-gray-700 font-medium'
                          : isCurrent
                          ? 'text-blue-600 font-semibold'
                          : 'text-gray-400'
                      }`}
                    >
                      {stage}
                    </span>
                    {isCurrent && (
                      <span className="text-xs text-blue-400 animate-pulse">in progress…</span>
                    )}
                  </div>
                )
              })}

              {interview.status === 'error' && (
                <div className="flex items-start gap-3 mt-2 p-3 bg-red-50 rounded-lg border border-red-100">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-600">{interview.error_message || 'Processing failed.'}</p>
                </div>
              )}
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg bg-white p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Details</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <MetadataItem icon={Globe} label="Language" value={interview.language_detected?.toUpperCase() ?? '--'} />
              <MetadataItem icon={HardDrive} label="File" value={interview.original_filename} />
              <MetadataItem icon={FileText} label="Type" value={interview.file_type} />
              <MetadataItem icon={Clock} label="Created" value={formatDate(interview.created_at)} />
            </div>
          </div>

          {profileQuery.data && interview.status === 'complete' && (
            <div className="border border-gray-200 rounded-lg bg-white p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Participant Demographics</h3>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: profileQuery.data.name },
                  { label: profileQuery.data.age_range },
                  { label: profileQuery.data.gender },
                  { label: profileQuery.data.role },
                  { label: profileQuery.data.industry },
                  { label: profileQuery.data.location },
                  { label: profileQuery.data.income_range },
                  { label: profileQuery.data.tech_level },
                ].filter(t => t.label).map((tag, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 text-xs rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 font-medium"
                  >
                    {tag.label}
                  </span>
                ))}
                {profileQuery.data.financial_context && (
                  <span className="px-2.5 py-1 text-xs rounded-full bg-amber-50 border border-amber-100 text-amber-700 font-medium max-w-xs truncate">
                    💰 {profileQuery.data.financial_context}
                  </span>
                )}
                {profileQuery.data.missing_fields?.length > 0 && (
                  <span className="px-2.5 py-1 text-xs rounded-full bg-gray-50 border border-gray-200 text-gray-400">
                    {profileQuery.data.missing_fields.length} field{profileQuery.data.missing_fields.length > 1 ? 's' : ''} missing
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'transcript' && (
        <div className="border border-gray-200 rounded-lg bg-white p-5">
          {!canShowTranscript ? (
            <EmptyState message="Transcript will appear once transcription is complete." />
          ) : !transcript ? (
            <EmptyState message="No transcript data available." />
          ) : (
            <TranscriptViewer segments={transcript.segments ?? []} />
          )}
        </div>
      )}

      {tab === 'analysis' && (
        <div>
          {!canShowAnalysis ? (
            <EmptyState message="Analysis will appear once processing is complete." />
          ) : !analysis ? (
            <EmptyState message="No analysis data available." />
          ) : allInsights.length === 0 ? (
            <EmptyState message="No insights were extracted from this interview." />
          ) : (
            <>
              <div className="flex flex-wrap gap-1.5 mb-5">
                <FilterChip
                  label={`All (${allInsights.length})`}
                  active={analysisFilter === 'all'}
                  onClick={() => setAnalysisFilter('all')}
                />
                {INSIGHT_CATEGORIES.filter((cat) => insightCountByCategory[cat]).map((cat) => (
                  <FilterChip
                    key={cat}
                    label={`${CATEGORY_LABELS[cat]} (${insightCountByCategory[cat]})`}
                    active={analysisFilter === cat}
                    onClick={() => setAnalysisFilter(cat)}
                  />
                ))}
              </div>

              <div className="grid gap-3">
                {filteredInsights.map(({ category, insight }, i) => (
                  <InsightCard key={i} insight={insight} categoryLabel={CATEGORY_LABELS[category]} />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'report' && (
        <div>
          {!canShowReport ? (
            <EmptyState message="Report will be generated once all processing stages are complete." />
          ) : !report ? (
            <EmptyState message="No report data available." />
          ) : (
            <ReportEditor
              report={report}
              onSave={(updates) => updateReportMutation.mutate(updates)}
              saving={updateReportMutation.isPending}
            />
          )}
        </div>
      )}

      <ConfirmDialog
        open={showDeleteConfirm}
        title="Delete Interview"
        message="This will permanently delete the interview and all associated data. This action cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />

      {showProfilePrompt && profileQuery.data && (
        <ProfilePromptModal
          profile={profileQuery.data}
          onSave={async (updates) => {
            await updateProfileMutation.mutateAsync(updates)
            setProfileDismissed(true)
          }}
          onDismiss={() => setProfileDismissed(true)}
        />
      )}
    </div>
  )
}

function MetadataItem({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-0.5">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </div>
      <p className="text-sm font-medium text-gray-700 truncate">{value}</p>
    </div>
  )
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
        active
          ? 'bg-blue-50 border-blue-200 text-blue-700 font-medium'
          : 'border-gray-200 text-gray-500 hover:bg-gray-50'
      }`}
    >
      {label}
    </button>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16 text-gray-400">
      <p className="text-sm">{message}</p>
    </div>
  )
}
