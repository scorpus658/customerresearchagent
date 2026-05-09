import axios from 'axios'
import type {
  Interview,
  InterviewDetail,
  PaginatedResponse,
  Project,
  Report,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ---------- Projects ----------

export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get<Project[]>('/projects')
  return data
}

export async function createProject(name: string, description?: string): Promise<Project> {
  const { data } = await api.post<Project>('/projects', { name, description })
  return data
}

export async function getProject(id: string): Promise<Project> {
  const { data } = await api.get<Project>(`/projects/${id}`)
  return data
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`)
}

// ---------- Interviews ----------

export async function uploadInterview(
  file: File,
  title?: string,
  projectId?: string,
  onProgress?: (pct: number) => void,
  participantName?: string,
  participantAgeRange?: string,
  participantRole?: string,
): Promise<Interview> {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (projectId) form.append('project_id', projectId)
  if (participantName) form.append('participant_name', participantName)
  if (participantAgeRange) form.append('participant_age_range', participantAgeRange)
  if (participantRole) form.append('participant_role', participantRole)
  form.append('synthesis_model', localStorage.getItem('synthesis_model') ?? 'haiku')
  const { data } = await api.post<Interview>('/interviews/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
    },
  })
  return data
}

export async function getInterviews(
  limit = 20,
  offset = 0,
  projectId?: string,
): Promise<PaginatedResponse<Interview>> {
  const { data } = await api.get<PaginatedResponse<Interview>>('/interviews', {
    params: { limit, offset, ...(projectId ? { project_id: projectId } : {}) },
  })
  return data
}

export async function getInterview(id: string): Promise<InterviewDetail> {
  const { data } = await api.get<InterviewDetail>(`/interviews/${id}`)
  return data
}

export async function updateReport(
  id: string,
  updates: Partial<Pick<Report, 'executive_summary' | 'detailed_findings' | 'recommendations'>>,
): Promise<Report> {
  const { data } = await api.patch<Report>(`/interviews/${id}/report`, updates)
  return data
}

export async function exportReport(id: string): Promise<Blob> {
  const { data } = await api.get(`/interviews/${id}/export`, {
    responseType: 'blob',
  })
  return data as Blob
}

export async function deleteInterview(id: string): Promise<void> {
  await api.delete(`/interviews/${id}`)
}

export async function reprocessInterview(id: string): Promise<Interview> {
  const model = localStorage.getItem('synthesis_model') ?? 'haiku'
  const { data } = await api.post<Interview>(`/interviews/${id}/reprocess`, { synthesis_model: model })
  return data
}

export async function searchInterviews(query: string): Promise<Interview[]> {
  const { data } = await api.get<Interview[]>('/interviews/search', {
    params: { q: query },
  })
  return data
}

export async function getProfile(interviewId: string): Promise<import('../types').IntervieweeProfile> {
  const { data } = await api.get(`/interviews/${interviewId}/profile`)
  return data
}

export async function updateProfile(
  interviewId: string,
  updates: Partial<Omit<import('../types').IntervieweeProfile, 'id' | 'interview_id' | 'missing_fields' | 'user_filled'>>,
): Promise<import('../types').IntervieweeProfile> {
  const { data } = await api.patch(`/interviews/${interviewId}/profile`, updates)
  return data
}

export async function getBoard(projectId: string): Promise<import('../types').ProjectBoard> {
  const { data } = await api.get(`/projects/${projectId}/board`)
  return data
}

export async function synthesizeBoard(projectId: string): Promise<import('../types').ProjectBoard> {
  const { data } = await api.post(`/projects/${projectId}/board/synthesize`)
  return data
}
