import { useState, useRef, useEffect, useCallback } from 'react'

export interface ToastState {
  message: string
  visible: boolean
}

export interface UseToastReturn {
  toast: ToastState
  showToast: (msg: string) => void
  dismiss: () => void
}

export function useToast(): UseToastReturn {
  const [message, setMessage] = useState('')
  const [visible, setVisible] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const dismiss = useCallback(() => {
    setVisible(false)
    if (timerRef.current != null) {
      clearTimeout(timerRef.current)
      timerRef.current = undefined
    }
  }, [])

  const showToast = useCallback(
    (msg: string) => {
      setMessage(msg)
      setVisible(true)
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        setVisible(false)
        timerRef.current = undefined
      }, 3000)
    },
    [],
  )

  useEffect(() => {
    return () => {
      clearTimeout(timerRef.current)
    }
  }, [])

  return { toast: { message, visible }, showToast, dismiss }
}

interface ToastProps {
  message: string
  visible: boolean
  onDismiss: () => void
}

export function Toast({ message, visible, onDismiss }: ToastProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-hidden={!visible || undefined}
      className={[
        'fixed bottom-5 right-5 z-50',
        'max-w-sm',
        'bg-journal-surface',
        'border border-warm-border',
        'rounded-lg',
        'px-4 py-3',
        'shadow-lg',
        'transition-all duration-300 ease-out',
        visible
          ? 'opacity-100 motion-safe:translate-y-0'
          : 'opacity-0 motion-safe:translate-y-2.5 pointer-events-none',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        <span className="w-2 h-2 rounded-full bg-sage-green mt-1.5 shrink-0" aria-hidden="true" />
        <p className="text-lamplight-ink text-sm flex-1">{message}</p>
        <button
          onClick={onDismiss}
          className="text-quiet-ink hover:text-faded-ink transition-colors duration-150 shrink-0"
          aria-label="Dismiss notification"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  )
}
