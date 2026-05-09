import { useCallback, useState } from 'react'
import { UploadCloud, File as FileIcon, X } from 'lucide-react'

const ACCEPTED_TYPES = [
  '.txt', '.json', '.srt', '.vtt',
  '.mp3', '.wav', '.m4a',
  '.mp4', '.webm', '.mov',
]

interface FileUploadProps {
  onFileSelect: (file: File) => void
  progress: number | null
  disabled?: boolean
}

export default function FileUpload({ onFileSelect, progress, disabled }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const validateFile = useCallback((file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ACCEPTED_TYPES.includes(ext)) {
      setError(`Unsupported file type: ${ext}`)
      return false
    }
    setError(null)
    return true
  }, [])

  const handleFile = useCallback(
    (file: File) => {
      if (validateFile(file)) {
        setSelectedFile(file)
        onFileSelect(file)
      }
    },
    [onFileSelect, validateFile],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const clearFile = () => {
    setSelectedFile(null)
    setError(null)
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer
          ${dragOver ? 'border-blue-400 bg-blue-50/50' : 'border-gray-200 hover:border-gray-300 bg-white'}
          ${disabled ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input
          type="file"
          accept={ACCEPTED_TYPES.join(',')}
          onChange={handleChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={disabled}
        />

        {selectedFile ? (
          <div className="flex items-center justify-center gap-3">
            <FileIcon className="w-8 h-8 text-blue-500" />
            <div className="text-left">
              <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
              <p className="text-xs text-gray-500">{formatSize(selectedFile.size)}</p>
            </div>
            {progress === null && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  clearFile()
                }}
                className="ml-2 p-1 rounded hover:bg-gray-100"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <UploadCloud className="w-10 h-10 text-gray-300" />
            <div>
              <p className="text-sm font-medium text-gray-700">
                Drop a file here or click to browse
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Transcripts (.txt, .json, .srt, .vtt) or media (.mp3, .wav, .m4a, .mp4, .webm, .mov)
              </p>
            </div>
          </div>
        )}
      </div>

      {progress !== null && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Uploading...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  )
}
