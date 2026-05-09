import { AlertTriangle } from 'lucide-react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
        <div className="flex items-start gap-3">
          {destructive && (
            <div className="p-2 bg-red-50 rounded-lg shrink-0">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
          )}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-1">{title}</h3>
            <p className="text-sm text-gray-500">{message}</p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-md hover:bg-gray-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-3 py-1.5 text-sm text-white rounded-md ${
              destructive ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
