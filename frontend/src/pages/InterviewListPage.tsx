import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, ChevronLeft, ChevronRight, Inbox } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import SearchBar from '../components/SearchBar'
import { useInterviews, useSearchInterviews } from '../hooks/useInterviews'

const PAGE_SIZE = 20

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function InterviewListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')

  const listQuery = useInterviews(PAGE_SIZE, page * PAGE_SIZE)
  const searchResult = useSearchInterviews(searchQuery)

  const isSearching = searchQuery.length > 0
  const isLoading = isSearching ? searchResult.isLoading : listQuery.isLoading
  const isError = isSearching ? searchResult.isError : listQuery.isError

  const interviews = isSearching
    ? searchResult.data ?? []
    : listQuery.data?.items ?? []
  const total = isSearching
    ? (searchResult.data?.length ?? 0)
    : (listQuery.data?.total ?? 0)

  const handleSearch = useCallback((q: string) => {
    setSearchQuery(q)
    setPage(0)
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Interviews</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} interview{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload
        </button>
      </div>

      <div className="mb-4 max-w-sm">
        <SearchBar
          onSearch={handleSearch}
          placeholder="Search interviews..."
        />
      </div>

      {isLoading && (
        <div className="text-center py-16">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-gray-400 mt-3">Loading interviews...</p>
        </div>
      )}

      {isError && (
        <div className="text-center py-16">
          <p className="text-sm text-red-600">Failed to load interviews. Please try again.</p>
        </div>
      )}

      {!isLoading && !isError && interviews.length === 0 && (
        <div className="text-center py-20">
          <Inbox className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 mb-1">
            {isSearching ? 'No interviews match your search.' : 'No interviews yet.'}
          </p>
          {!isSearching && (
            <button
              onClick={() => navigate('/upload')}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Upload your first interview
            </button>
          )}
        </div>
      )}

      {!isLoading && interviews.length > 0 && (
        <>
          <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Title
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Status
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3 hidden sm:table-cell">
                    Language
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3 hidden md:table-cell">
                    Type
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {interviews.map((interview) => (
                  <tr
                    key={interview.id}
                    onClick={() => navigate(`/interviews/${interview.id}`)}
                    className="cursor-pointer hover:bg-gray-50/50 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                        {interview.title || interview.original_filename}
                      </div>
                      {interview.title && (
                        <div className="text-xs text-gray-400 truncate max-w-xs">
                          {interview.original_filename}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={interview.status} />
                    </td>
                    <td className="px-5 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-gray-500 uppercase">
                        {interview.language_detected ?? '--'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 hidden md:table-cell">
                      <span className="text-xs text-gray-500 capitalize">
                        {interview.file_type}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-xs text-gray-500">
                        {formatDate(interview.created_at)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!isSearching && total > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-xs text-gray-500">
                Showing {page * PAGE_SIZE + 1}&ndash;{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
              </p>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-1.5 border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-30"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={(page + 1) * PAGE_SIZE >= total}
                  className="p-1.5 border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-30"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
