import { useState, useEffect, useRef, useCallback } from 'react'

const VERDICT_OPTIONS = [
  { value: '', label: 'All Verdicts' },
  { value: 'STRONG', label: 'Strong' },
  { value: 'PROMISING', label: 'Promising' },
  { value: 'WEAK', label: 'Weak' },
  { value: 'TARPIT', label: 'Tarpit' },
  { value: 'REJECT', label: 'Reject' },
]

export interface FilterBarProps {
  onFilter: (v: { minScore?: number; verdict?: string }) => void
}

export function FilterBar({ onFilter }: FilterBarProps) {
  const [verdict, setVerdict] = useState('')
  const [minScore, setMinScore] = useState(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onFilterRef = useRef(onFilter)
  onFilterRef.current = onFilter

  const emit = useCallback((v: { minScore?: number; verdict?: string }) => {
    const f: { minScore?: number; verdict?: string } = {}
    if (v.minScore && v.minScore > 0) f.minScore = v.minScore
    if (v.verdict) f.verdict = v.verdict
    onFilterRef.current(f)
  }, [])

  const handleVerdictChange = (value: string) => {
    setVerdict(value)
    emit({ minScore: minScore > 0 ? minScore : undefined, verdict: value || undefined })
  }

  const handleScoreChange = (value: number) => {
    setMinScore(value)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      emit({ minScore: value > 0 ? value : undefined, verdict: verdict || undefined })
    }, 300)
  }

  const clearVerdict = () => {
    setVerdict('')
    emit({ minScore: minScore > 0 ? minScore : undefined })
  }

  const clearScore = () => {
    setMinScore(0)
    if (timerRef.current) clearTimeout(timerRef.current)
    emit({ verdict: verdict || undefined })
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const hasFilters = verdict !== '' || minScore > 0

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-3 bg-journal-surface border border-warm-border rounded-full px-4 py-1.5">
        <label className="text-faded-ink text-xs uppercase tracking-wide whitespace-nowrap" htmlFor="verdict-select">
          Verdict
        </label>
        <select
          id="verdict-select"
          value={verdict}
          onChange={(e) => handleVerdictChange(e.target.value)}
          className="bg-expedition-black text-lamplight-ink border border-warm-border rounded-full px-3 py-1 text-sm appearance-none cursor-pointer
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/50 focus-visible:ring-offset-1 focus-visible:ring-offset-expedition-black"
        >
          {VERDICT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-3 bg-journal-surface border border-warm-border rounded-full px-4 py-1.5">
        <label className="text-faded-ink text-xs uppercase tracking-wide whitespace-nowrap" htmlFor="score-slider">
          Min Score
        </label>
        <input
          id="score-slider"
          type="range"
          min={0}
          max={100}
          value={minScore}
          onChange={(e) => handleScoreChange(Number(e.target.value))}
          className="w-24 h-1.5 rounded-full appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-amber-gold
            [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-amber-gold [&::-moz-range-thumb]:border-none
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/50 focus-visible:ring-offset-1 focus-visible:ring-offset-expedition-black"
          style={{ accentColor: 'var(--color-amber-gold)' }}
        />
        <span className="text-lamplight-ink text-sm font-mono w-7 text-right tabular-nums">{minScore}</span>
      </div>

      {hasFilters && (
        <div className="flex items-center gap-2 flex-wrap" aria-label="Active filters">
          {verdict && (
            <span className="inline-flex items-center gap-1 bg-amber-muted/20 text-amber-gold text-xs rounded-full px-3 py-1 border border-amber-muted/30">
              Verdict: {VERDICT_OPTIONS.find((o) => o.value === verdict)?.label ?? verdict}
              <button
                onClick={clearVerdict}
                className="ml-0.5 hover:text-lamplight-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/50 rounded-sm"
                aria-label="Remove verdict filter"
              >
                ×
              </button>
            </span>
          )}
          {minScore > 0 && (
            <span className="inline-flex items-center gap-1 bg-amber-muted/20 text-amber-gold text-xs rounded-full px-3 py-1 border border-amber-muted/30">
              Min Score: {minScore}
              <button
                onClick={clearScore}
                className="ml-0.5 hover:text-lamplight-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/50 rounded-sm"
                aria-label="Remove score filter"
              >
                ×
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  )
}
