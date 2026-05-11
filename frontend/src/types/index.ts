export type InterviewStatus =
  | 'uploaded'
  | 'transcribing'
  | 'analyzing'
  | 'synthesizing'
  | 'complete'
  | 'error'

export interface Project {
  id: string
  name: string
  description: string | null
  interview_count: number
  created_at: string
  updated_at: string
}

export interface Interview {
  id: string
  project_id: string | null
  title: string
  status: InterviewStatus
  original_filename: string
  file_type: string
  file_url: string | null
  language_detected: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface TranscriptSegment {
  speaker: string
  text: string
  start_time: number | null
  end_time: number | null
  language: string | null
  translated_text: string | null
}

export interface Transcript {
  id: string
  interview_id: string
  raw_text: string | null
  segments: TranscriptSegment[]
  created_at: string
}

export interface Insight {
  text: string
  quote: string
  speaker: string
  timestamp: number | null
  confidence: number
  category: string
  translated_quote: string | null
}

export interface Analysis {
  id: string
  interview_id: string
  pain_points: Insight[]
  goals: Insight[]
  objections: Insight[]
  feature_requests: Insight[]
  workarounds: Insight[]
  emotional_moments: Insight[]
  strong_quotes: Insight[]
  raw_extraction: unknown[] | null
  created_at: string
}

export type InsightCategory =
  | 'pain_points'
  | 'goals'
  | 'objections'
  | 'feature_requests'
  | 'workarounds'
  | 'emotional_moments'
  | 'strong_quotes'

export interface Theme {
  name: string
  description: string
  evidence_count: number
  insight_ids: number[]
}

export interface Report {
  id: string
  interview_id: string
  executive_summary: string | null
  detailed_findings: Record<string, unknown> | null
  themes: Theme[] | null
  recommendations: Recommendation[] | null
  metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface Recommendation {
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  supporting_evidence: string
  effort: 'low' | 'medium' | 'high'
}

export interface InterviewDetail {
  interview: Interview
  transcript: Transcript | null
  analysis: Analysis | null
  report: Report | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface IntervieweeProfile {
  id: string
  interview_id: string
  name: string | null
  age_range: string | null
  gender: string | null
  role: string | null
  industry: string | null
  location: string | null
  income_range: string | null
  tech_level: string | null
  financial_context: string | null
  notes: string | null
  missing_fields: string[]
  user_filled: 'no' | 'partial' | 'done'
}

export interface BoardTheme {
  name: string
  description: string
  count: number
  interviews: string[]
  strength: 'strong' | 'moderate' | 'weak'
}

export interface BoardPainPoint {
  text: string
  count: number
  interviews: string[]
  quotes: string[]
}

export interface BoardInsight {
  text: string
  interview: string
  quote: string
  why_notable: string
}

export interface BoardPattern {
  title: string
  description: string
  evidence: string
  type: 'behavioral' | 'demographic' | 'contextual' | 'emotional'
}

export interface BoardDataGap {
  question: string
  context: string
  missing_in: number
}

export interface ProjectBoard {
  id: string | null
  project_id: string
  status: 'pending' | 'running' | 'complete' | 'error'
  error_message: string | null
  recurring_themes: BoardTheme[] | null
  pain_points: BoardPainPoint[] | null
  unique_insights: BoardInsight[] | null
  patterns: BoardPattern[] | null
  demographic_summary: Record<string, unknown> | null
  data_gaps: BoardDataGap[] | null
  interviews_included: string[] | null
  last_run_at: string | null
}
