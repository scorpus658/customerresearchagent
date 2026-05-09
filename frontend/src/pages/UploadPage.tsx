import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, DollarSign, FolderOpen, Plus } from 'lucide-react'
import FileUpload from '../components/FileUpload'
import { useUploadInterview, useProjects, useCreateProject } from '../hooks/useInterviews'

const MEDIA_EXTENSIONS = ['mp3', 'wav', 'm4a', 'mp4', 'webm', 'mov']

function estimateCost(file: File | null): string | null {
  if (!file) return null
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  const sizeMB = file.size / (1024 * 1024)
  if (MEDIA_EXTENSIONS.includes(ext)) {
    const isVideo = ['mp4', 'webm', 'mov'].includes(ext)
    const estimatedMinutes = sizeMB / (isVideo ? 10 : 1)
    const transcriptionCost = estimatedMinutes * 0.006
    return `~$${(transcriptionCost + 0.05).toFixed(2)}`
  }
  return '~$0.05'
}

export default function UploadPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const upload = useUploadInterview()
  const { data: projects = [] } = useProjects()
  const createProject = useCreateProject()

  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [progress, setProgress] = useState<number | null>(null)
  const [participantName, setParticipantName] = useState('')
  const [participantAgeRange, setParticipantAgeRange] = useState('')
  const [participantRole, setParticipantRole] = useState('')

  // Project selection state
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [showNewProject, setShowNewProject] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')

  // Pre-select from URL param, then fall back to first project
  useEffect(() => {
    const pid = searchParams.get('project_id')
    if (pid) {
      setSelectedProjectId(pid)
    } else if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [searchParams, projects])

  const handleProjectChange = (val: string) => {
    if (val === '__new__') {
      setShowNewProject(true)
    } else {
      setSelectedProjectId(val)
      setShowNewProject(false)
    }
  }

  const hasProject = showNewProject ? false : !!selectedProjectId

  const handleCreateAndSelect = async () => {
    if (!newProjectName.trim()) return
    const project = await createProject.mutateAsync({ name: newProjectName.trim() })
    setSelectedProjectId(project.id)
    setShowNewProject(false)
    setNewProjectName('')
  }

  const handleUpload = async () => {
    if (!file) return
    setProgress(0)
    try {
      const interview = await upload.mutateAsync({
        file,
        title: title.trim() || undefined,
        projectId: selectedProjectId,
        onProgress: setProgress,
        participantName: participantName.trim() || undefined,
        participantAgeRange: participantAgeRange || undefined,
        participantRole: participantRole.trim() || undefined,
      })
      navigate(`/interviews/${interview.id}`)
    } catch {
      setProgress(null)
    }
  }

  const cost = estimateCost(file)
  const isUploading = progress !== null
  const selectedProject = projects.find((p) => p.id === selectedProjectId)

  return (
    <div className="max-w-xl mx-auto">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      <h1 className="text-xl font-semibold text-gray-900 mb-1">Upload Interview</h1>
      <p className="text-sm text-gray-500 mb-6">
        Upload a transcript or media file. The system will transcribe, analyze, and generate a research report.
      </p>

      <div className="space-y-5">
        <FileUpload onFileSelect={setFile} progress={progress} disabled={isUploading} />

        {/* Project selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Project <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <select
              value={showNewProject ? '__new__' : selectedProjectId}
              onChange={(e) => handleProjectChange(e.target.value)}
              disabled={isUploading}
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 disabled:opacity-50 bg-white appearance-none"
            >
              {projects.length === 0 && !showNewProject && (
                <option value="" disabled>No projects yet — create one below</option>
              )}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
              <option value="__new__">+ Create new project…</option>
            </select>
          </div>

          {/* Inline new project creation */}
          {showNewProject && (
            <div className="mt-2 flex gap-2">
              <input
                autoFocus
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateAndSelect()}
                placeholder="New project name"
                className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
              />
              <button
                onClick={handleCreateAndSelect}
                disabled={!newProjectName.trim() || createProject.isPending}
                className="flex items-center gap-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Plus className="w-3.5 h-3.5" />
                {createProject.isPending ? 'Creating…' : 'Create'}
              </button>
              <button
                onClick={() => { setShowNewProject(false); setSelectedProjectId(projects[0]?.id ?? '') }}
                className="px-3 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          )}

          {selectedProject && (
            <p className="mt-1.5 text-xs text-gray-400">
              Will be added to <span className="font-medium text-gray-600">{selectedProject.name}</span>
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Title <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., User Interview — Sarah, PM at Acme Corp"
            disabled={isUploading}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 disabled:opacity-50"
          />
        </div>

        {/* Participant info */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">
            Participant <span className="text-gray-400 font-normal">(optional — helps with research board)</span>
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <input
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                placeholder="Name or pseudonym"
                disabled={isUploading}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 disabled:opacity-50"
              />
            </div>
            <select
              value={participantAgeRange}
              onChange={(e) => setParticipantAgeRange(e.target.value)}
              disabled={isUploading}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 disabled:opacity-50 bg-white text-gray-700"
            >
              <option value="">Age range</option>
              <option>Under 25</option>
              <option>25-34</option>
              <option>35-44</option>
              <option>45-54</option>
              <option>55+</option>
            </select>
            <input
              type="text"
              value={participantRole}
              onChange={(e) => setParticipantRole(e.target.value)}
              placeholder="Role / profession"
              disabled={isUploading}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 disabled:opacity-50"
            />
          </div>
        </div>

        {cost && (
          <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 px-3 py-2 rounded-lg">
            <DollarSign className="w-3.5 h-3.5" />
            Estimated processing cost: {cost}
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!file || isUploading || !hasProject}
          className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isUploading ? 'Uploading…' : 'Upload & Process'}
        </button>

        {upload.isError && (
          <p className="text-sm text-red-600">Upload failed. Please try again.</p>
        )}
      </div>
    </div>
  )
}
