interface ScoreCardProps {
  label: string
  score: number
  weight: string
}

export function ScoreCard({ label, score, weight }: ScoreCardProps) {
  return (
    <div className="bg-expedition-black border border-warm-border rounded-lg p-4">
      <p className="text-xs uppercase tracking-wide text-faded-ink mb-2">{label}</p>
      <p className="text-3xl font-bold font-mono text-lamplight-ink">{score}</p>
      <p className="text-xs text-faded-ink mt-1">{weight}</p>
    </div>
  )
}
