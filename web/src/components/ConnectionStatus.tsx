export interface ConnectionStatusProps {
  connected: boolean
  reconnecting?: boolean
}

const BASE = 'inline-flex items-center gap-1.5 text-xs'
const DOT = 'inline-block w-2 h-2 rounded-full'

export function ConnectionStatus({ connected, reconnecting = false }: ConnectionStatusProps) {
  if (connected) {
    return (
      <span className={BASE} role="status" aria-live="polite">
        <span className={`${DOT} bg-sage-green`} aria-hidden="true" />
        <span className="text-sage-green">Live</span>
      </span>
    )
  }

  if (reconnecting) {
    return (
      <span className={BASE} role="status" aria-live="polite">
        <span className={`${DOT} bg-amber-gold animate-pulse`} aria-hidden="true" />
        <span className="text-amber-gold">Reconnecting\u2026</span>
      </span>
    )
  }

  return (
    <span className={BASE} role="status" aria-live="polite">
      <span className={`${DOT} bg-quiet-ink`} aria-hidden="true" />
      <span className="text-quiet-ink">Connecting\u2026</span>
    </span>
  )
}
