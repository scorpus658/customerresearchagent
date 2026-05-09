import { useState } from 'react'
import { Pencil, X, Save, FileText, Lightbulb, Tags } from 'lucide-react'
import type { Report } from '../types'

interface ReportEditorProps {
  report: Report
  onSave: (updates: Partial<Pick<Report, 'executive_summary' | 'detailed_findings' | 'recommendations'>>) => void
  saving?: boolean
}

// If executive_summary was accidentally stored as a full JSON blob, extract the real text
function extractSummary(raw: string | null): string {
  if (!raw) return ''
  const trimmed = raw.trim()
  if (!trimmed.startsWith('{')) return trimmed
  try {
    const parsed = JSON.parse(trimmed)
    return parsed.executive_summary ?? trimmed
  } catch {
    return trimmed
  }
}

export default function ReportEditor({ report, onSave, saving }: ReportEditorProps) {
  const [editingSummary, setEditingSummary] = useState(false)
  const [summaryDraft, setSummaryDraft] = useState('')
  const executiveSummary = extractSummary(report.executive_summary)

  const startEditSummary = () => {
    setEditingSummary(true)
    setSummaryDraft(executiveSummary)
  }

  const saveSummary = () => {
    onSave({ executive_summary: summaryDraft })
    setEditingSummary(false)
  }

  const findings = report.detailed_findings ?? {}
  const recommendations = report.recommendations ?? []
  const themes = report.themes ?? []

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className="border border-gray-200 rounded-lg bg-white">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-900">Executive Summary</h3>
          </div>
          {!editingSummary && (
            <button
              onClick={startEditSummary}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 transition-colors"
            >
              <Pencil className="w-3 h-3" />
              Edit
            </button>
          )}
        </div>
        <div className="px-5 py-4">
          {editingSummary ? (
            <div>
              <textarea
                value={summaryDraft}
                onChange={(e) => setSummaryDraft(e.target.value)}
                rows={10}
                className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 resize-y"
              />
              <div className="flex justify-end gap-2 mt-3">
                <button
                  onClick={() => setEditingSummary(false)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-md hover:bg-gray-50"
                >
                  <X className="w-3.5 h-3.5" />
                  Cancel
                </button>
                <button
                  onClick={saveSummary}
                  disabled={saving}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {executiveSummary || (
                <span className="text-gray-400 italic">No summary yet.</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Detailed Findings */}
      {Object.keys(findings).length > 0 && (
        <div className="border border-gray-200 rounded-lg bg-white">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-200">
            <FileText className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-900">Detailed Findings</h3>
          </div>
          <div className="px-5 py-4 space-y-4">
            {Object.entries(findings).map(([theme, data]) => {
              const finding = data as Record<string, unknown>
              return (
                <div key={theme} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                  <h4 className="text-sm font-medium text-gray-900 mb-1">{theme}</h4>
                  {!!finding.description && (
                    <p className="text-sm text-gray-600 mb-2">{String(finding.description)}</p>
                  )}
                  {!!finding.implications && (
                    <p className="text-xs text-gray-500 italic">Implications: {String(finding.implications)}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="border border-gray-200 rounded-lg bg-white">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-200">
            <Lightbulb className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-900">Recommendations</h3>
          </div>
          <div className="px-5 py-4 space-y-3">
            {recommendations.map((rec, i) => (
              <div key={i} className="border border-gray-100 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-sm font-medium text-gray-900">{rec.title}</h4>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium uppercase ${
                    rec.priority === 'high' ? 'bg-red-50 text-red-600' :
                    rec.priority === 'medium' ? 'bg-amber-50 text-amber-600' :
                    'bg-gray-50 text-gray-500'
                  }`}>
                    {rec.priority}
                  </span>
                  {rec.effort && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium uppercase">
                      {rec.effort} effort
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600">{rec.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Themes */}
      {themes.length > 0 && (
        <div className="border border-gray-200 rounded-lg bg-white">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-200">
            <Tags className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-900">Themes</h3>
          </div>
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {themes.map((theme, i) => (
              <div
                key={i}
                className="border border-gray-100 rounded-lg p-4 bg-gray-50/50"
              >
                <h4 className="text-sm font-medium text-gray-900 mb-1">{theme.name}</h4>
                <p className="text-xs text-gray-500 mb-2">{theme.description}</p>
                <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">
                  {theme.evidence_count} evidence items
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
