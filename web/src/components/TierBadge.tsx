const tierColor: Record<number, string> = {
  1: 'bg-tier-gold text-expedition-black',
  2: 'bg-tier-silver text-expedition-black',
  3: 'bg-tier-bronze text-expedition-black',
  4: 'bg-quiet-ink text-lamplight-ink',
  5: 'bg-quiet-ink text-faded-ink',
}

export function TierBadge({ tier }: { tier: number }) {
  const color = tierColor[tier] ?? tierColor[5]
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-semibold ${color}`}
      aria-label={`Tier ${tier}`}
    >
      T{tier}
    </span>
  )
}
