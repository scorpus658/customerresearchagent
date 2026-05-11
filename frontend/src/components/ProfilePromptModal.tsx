import { useState } from 'react'
import { X, UserCircle, ChevronRight } from 'lucide-react'
import type { IntervieweeProfile } from '../types'

const FIELD_META: Record<
  string,
  { label: string; placeholder: string; type: 'text' | 'select'; options?: string[] }
> = {
  name: { label: 'Name / pseudonym', placeholder: 'e.g. Sarah K.', type: 'text' },
  age_range: {
    label: 'Age range',
    placeholder: '',
    type: 'select',
    options: ['Under 25', '25-34', '35-44', '45-54', '55+'],
  },
  gender: {
    label: 'Gender',
    placeholder: '',
    type: 'select',
    options: ['Male', 'Female', 'Non-binary', 'Prefer not to say'],
  },
  role: { label: 'Job title / role', placeholder: 'e.g. Product Manager', type: 'text' },
  industry: { label: 'Industry', placeholder: 'e.g. SaaS, Healthcare, E-commerce', type: 'text' },
  location: { label: 'Location / region', placeholder: 'e.g. Bangalore, India', type: 'text' },
  income_range: {
    label: 'Annual income range',
    placeholder: '',
    type: 'select',
    options: ['Under ₹3L', '₹3-5L', '₹5-10L', '₹10-20L', '₹20-50L', '₹50L+', 'Under $30k', '$30-60k', '$60-100k', '$100-200k', '$200k+'],
  },
  tech_level: {
    label: 'Technical expertise',
    placeholder: '',
    type: 'select',
    options: ['Non-technical', 'Somewhat technical', 'Technical', 'Very technical'],
  },
  financial_context: {
    label: 'Budget / financial context',
    placeholder: 'Any mentions of budget, pricing, spending constraints…',
    type: 'text',
  },
}

interface Props {
  profile: IntervieweeProfile
  onSave: (updates: Record<string, string>) => Promise<void>
  onDismiss: () => void
}

export default function ProfilePromptModal({ profile, onSave, onDismiss }: Props) {
  const missing = profile.missing_fields ?? []
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  if (missing.length === 0) return null

  const handleSave = async () => {
    const filled = Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim()))
    if (Object.keys(filled).length === 0) {
      onDismiss()
      return
    }
    setSaving(true)
    await onSave(filled)
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-4 pb-4 sm:pb-0">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onDismiss} />

      <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
                <UserCircle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-white">A few quick questions</h2>
                <p className="text-xs text-indigo-200 mt-0.5">
                  We couldn't find these details in the transcript
                </p>
              </div>
            </div>
            <button onClick={onDismiss} className="text-white/60 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Fields */}
        <div className="px-6 py-5 space-y-4 max-h-[60vh] overflow-y-auto">
          {missing.map((field) => {
            const meta = FIELD_META[field]
            if (!meta) return null
            return (
              <div key={field}>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  {meta.label}
                </label>
                {meta.type === 'select' ? (
                  <select
                    value={values[field] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [field]: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 bg-white"
                  >
                    <option value="">— Skip —</option>
                    {meta.options?.map((o) => (
                      <option key={o} value={o}>{o}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={values[field] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [field]: e.target.value }))}
                    placeholder={meta.placeholder}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <button
            onClick={onDismiss}
            className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            Skip for now
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving…' : 'Save & continue'}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
