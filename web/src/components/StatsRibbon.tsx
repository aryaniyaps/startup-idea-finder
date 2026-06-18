import type { Stats } from '../api'

const VERDICT_LABELS: Record<string, string> = {
  STRONG: 'Strong',
  PROMISING: 'Promising',
  WEAK: 'Weak',
  TARPIT: 'Tarpit',
  REJECT: 'Reject',
}

const VERDICT_COLORS: Record<string, string> = {
  STRONG: 'text-sage-green',
  PROMISING: 'text-warm-teal',
  WEAK: 'text-ochre',
  TARPIT: 'text-brick-red',
  REJECT: 'text-quiet-ink',
}

const VERDICT_ORDER = ['STRONG', 'PROMISING', 'WEAK', 'TARPIT', 'REJECT']

export interface StatsRibbonProps {
  stats: Stats | null
}

function StatPill({ label, value, valueClass }: { label: string; value: string | number; valueClass?: string }) {
  return (
    <div className="bg-journal-surface border border-warm-border rounded-md px-4 py-2 flex flex-col items-center min-w-[80px]">
      <span className="text-faded-ink text-xs uppercase tracking-wide">{label}</span>
      <span className={`text-lamplight-ink text-lg font-semibold ${valueClass ?? ''}`}>{value}</span>
    </div>
  )
}

function SkeletonPill() {
  return (
    <div className="bg-journal-surface border border-warm-border rounded-md px-4 py-2 flex flex-col items-center gap-1 min-w-[80px] animate-pulse">
      <span className="w-14 h-3 bg-raised-surface rounded" />
      <span className="w-8 h-5 bg-raised-surface rounded" />
    </div>
  )
}

export function StatsRibbon({ stats }: StatsRibbonProps) {
  if (!stats) {
    return (
      <div className="flex gap-3" role="status" aria-label="Loading statistics">
        <SkeletonPill />
        {VERDICT_ORDER.map((v) => (
          <SkeletonPill key={v} />
        ))}
        <SkeletonPill />
      </div>
    )
  }

  return (
    <div className="flex gap-3" role="region" aria-label="Statistics">
      <StatPill label="Total Ideas" value={stats.total_ideas} />
      {VERDICT_ORDER.map((verdict) => {
        const count = stats.by_verdict[verdict] ?? 0
        return (
          <StatPill
            key={verdict}
            label={VERDICT_LABELS[verdict] ?? verdict}
            value={count}
            valueClass={VERDICT_COLORS[verdict] ?? ''}
          />
        )
      })}
      <StatPill label="Signals" value={stats.total_signals} />
    </div>
  )
}
