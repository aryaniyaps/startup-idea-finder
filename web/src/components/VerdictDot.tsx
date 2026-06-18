const verdictColor: Record<string, string> = {
  STRONG: 'bg-sage-green',
  PROMISING: 'bg-steel-blue',
  WEAK: 'bg-ochre',
  TARPIT: 'bg-brick-red',
  REJECT: 'bg-quiet-ink',
}

export function VerdictDot({ verdict }: { verdict: string }) {
  const color = verdictColor[verdict] ?? 'bg-quiet-ink'
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${color}`}
      aria-label={`Verdict: ${verdict}`}
    />
  )
}
