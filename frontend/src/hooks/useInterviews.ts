import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../utils/api'
import type { Report } from '../types'

// ---------- Projects ----------

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id),
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      api.createProject(name, description),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export function useDeleteProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

// ---------- Interviews ----------

export function useInterviews(limit = 20, offset = 0, projectId?: string) {
  return useQuery({
    queryKey: ['interviews', limit, offset, projectId],
    queryFn: () => api.getInterviews(limit, offset, projectId),
  })
}

export function useSearchInterviews(query: string) {
  return useQuery({
    queryKey: ['interviews', 'search', query],
    queryFn: () => api.searchInterviews(query),
    enabled: query.length > 0,
  })
}

export function useInterviewDetail(id: string) {
  return useQuery({
    queryKey: ['interview', id],
    queryFn: () => api.getInterview(id),
    refetchInterval: (query) => {
      const status = query.state.data?.interview?.status
      if (status && !['complete', 'error'].includes(status)) return 3000
      return false
    },
  })
}

export function useUploadInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      file,
      title,
      projectId,
      onProgress,
      participantName,
      participantAgeRange,
      participantRole,
    }: {
      file: File
      title?: string
      projectId?: string
      onProgress?: (pct: number) => void
      participantName?: string
      participantAgeRange?: string
      participantRole?: string
    }) => api.uploadInterview(file, title, projectId, onProgress, participantName, participantAgeRange, participantRole),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['interviews'] })
      if (vars.projectId) {
        qc.invalidateQueries({ queryKey: ['projects'] })
        qc.invalidateQueries({ queryKey: ['project', vars.projectId] })
      }
    },
  })
}

export function useDeleteInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteInterview(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['interviews'] })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useReprocessInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.reprocessInterview(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['interview', id] })
      qc.invalidateQueries({ queryKey: ['interviews'] })
    },
  })
}

export function useUpdateReport(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (
      updates: Partial<Pick<Report, 'executive_summary' | 'detailed_findings' | 'recommendations'>>,
    ) => api.updateReport(id, updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interview', id] }),
  })
}

export function useProfile(interviewId: string, enabled = true) {
  return useQuery({
    queryKey: ['profile', interviewId],
    queryFn: () => api.getProfile(interviewId),
    enabled,
    retry: false,
  })
}

export function useUpdateProfile(interviewId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (updates: Parameters<typeof api.updateProfile>[1]) =>
      api.updateProfile(interviewId, updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile', interviewId] }),
  })
}

export function useBoard(projectId: string) {
  return useQuery({
    queryKey: ['board', projectId],
    queryFn: () => api.getBoard(projectId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' ? 3000 : false
    },
  })
}

export function useSynthesizeBoard(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.synthesizeBoard(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board', projectId] }),
  })
}

export function useExportReport() {
  return useMutation({
    mutationFn: async (id: string) => {
      const blob = await api.exportReport(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${id}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}
