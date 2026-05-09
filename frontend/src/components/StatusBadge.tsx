import type { InterviewStatus } from '../types'

const statusConfig: Record<InterviewStatus, { label: string; bg: string; text: string; dot: string }> = {
  uploaded:      { label: 'Uploaded',      bg: 'bg-gray-100',    text: 'text-gray-700',    dot: 'bg-gray-400' },
  transcribing:  { label: 'Transcribing',  bg: 'bg-blue-50',     text: 'text-blue-700',    dot: 'bg-blue-400' },
  analyzing:     { label: 'Analyzing',     bg: 'bg-amber-50',    text: 'text-amber-700',   dot: 'bg-amber-400' },
  synthesizing:  { label: 'Synthesizing',  bg: 'bg-purple-50',   text: 'text-purple-700',  dot: 'bg-purple-400' },
  complete:      { label: 'Complete',      bg: 'bg-green-50',    text: 'text-green-700',   dot: 'bg-green-500' },
  error:         { label: 'Error',         bg: 'bg-red-50',      text: 'text-red-700',     dot: 'bg-red-500' },
}

export default function StatusBadge({ status }: { status: InterviewStatus }) {
  const cfg = statusConfig[status] ?? statusConfig.error
  const isAnimating = ['transcribing', 'analyzing', 'synthesizing'].includes(status)

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${isAnimating ? 'animate-pulse' : ''}`} />
      {cfg.label}
    </span>
  )
}
