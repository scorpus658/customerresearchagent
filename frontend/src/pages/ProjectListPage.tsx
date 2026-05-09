import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen, Plus, Trash2, FileText } from 'lucide-react'
import { useProjects, useCreateProject, useDeleteProject } from '../hooks/useInterviews'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function ProjectListPage() {
  const navigate = useNavigate()
  const { data: projects = [], isLoading } = useProjects()
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()

  const [showNew, setShowNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleCreate = async () => {
    if (!newName.trim()) return
    await createProject.mutateAsync({ name: newName.trim(), description: newDesc.trim() || undefined })
    setNewName('')
    setNewDesc('')
    setShowNew(false)
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this project? Interviews will become unassigned.')) return
    setDeletingId(id)
    await deleteProject.mutateAsync(id)
    setDeletingId(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Projects</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {projects.length} project{projects.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* New project form */}
      {showNew && (
        <div className="mb-6 p-4 border border-blue-200 rounded-xl bg-blue-50/50">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">Create project</h2>
          <div className="space-y-3">
            <input
              autoFocus
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              placeholder="Project name"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 bg-white"
            />
            <input
              type="text"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              placeholder="Description (optional)"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 bg-white"
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || createProject.isPending}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {createProject.isPending ? 'Creating…' : 'Create'}
              </button>
              <button
                onClick={() => { setShowNew(false); setNewName(''); setNewDesc('') }}
                className="px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="text-center py-16">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-gray-400 mt-3">Loading projects…</p>
        </div>
      )}

      {!isLoading && projects.length === 0 && !showNew && (
        <div className="text-center py-20">
          <FolderOpen className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 mb-3">No projects yet.</p>
          <button
            onClick={() => setShowNew(true)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Create your first project
          </button>
        </div>
      )}

      {!isLoading && projects.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <div
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}`)}
              className="group relative bg-white border border-gray-200 rounded-xl p-5 cursor-pointer hover:border-blue-300 hover:shadow-sm transition-all"
            >
              {/* Delete button */}
              <button
                onClick={(e) => handleDelete(project.id, e)}
                disabled={deletingId === project.id}
                className="absolute top-3 right-3 p-1.5 text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded-md hover:bg-red-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>

              <div className="flex items-start gap-3 mb-3">
                <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <FolderOpen className="w-4.5 h-4.5 text-blue-600" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900 truncate">{project.name}</h3>
                  {project.description && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{project.description}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {project.interview_count} interview{project.interview_count !== 1 ? 's' : ''}
                </span>
                <span>{formatDate(project.created_at)}</span>
              </div>

              {/* Upload shortcut */}
              <button
                onClick={(e) => { e.stopPropagation(); navigate(`/upload?project_id=${project.id}`) }}
                className="mt-3 w-full py-1.5 text-xs text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors opacity-0 group-hover:opacity-100"
              >
                + Upload to this project
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
