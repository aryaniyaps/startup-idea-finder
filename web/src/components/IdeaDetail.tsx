import { useRef, useEffect } from 'react'
import type { Idea } from '../api'
import { ScoreCard } from './ScoreCard'

interface IdeaDetailProps {
  idea: Idea | null
}

const SCORE_DIMENSIONS = [
  { key: 'problem_quality' as const, label: 'Problem Quality', weight: 'High' },
  { key: 'market_viability' as const, label: 'Market Viability', weight: 'Medium' },
  { key: 'sentiment_signal' as const, label: 'Sentiment Signal', weight: 'Medium' },
  { key: 'founder_fit' as const, label: 'Founder Fit', weight: 'Low' },
]

const VERDICT_STYLES: Record<string, string> = {
  STRONG: 'bg-sage-green/20 text-sage-green border-sage-green/30',
  PROMISING: 'bg-amber-gold/20 text-amber-gold border-amber-gold/30',
  WEAK: 'bg-ochre/20 text-ochre border-ochre/30',
  TARPIT: 'bg-brick-red/20 text-brick-red border-brick-red/30',
  REJECT: 'bg-quiet-ink/20 text-quiet-ink border-quiet-ink/30',
}

const SECTION_LABEL =
  'text-xs uppercase tracking-wide text-faded-ink mb-3 font-medium'

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-faded-ink gap-4">
      <svg
        width="48"
        height="48"
        viewBox="0 0 48 48"
        fill="none"
        className="opacity-40"
        aria-hidden="true"
      >
        <circle
          cx="24"
          cy="24"
          r="20"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <circle cx="24" cy="24" r="3" fill="currentColor" />
        <path
          d="M24 4 L24 8 M24 40 L24 44"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          d="M44 24 L40 24 M8 24 L4 24"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          d="M38.14 9.86 L35.31 12.69 M12.69 35.31 L9.86 38.14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          d="M9.86 9.86 L12.69 12.69 M35.31 35.31 L38.14 38.14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <path
          d="M24 8 L27 14 L33 17 L27 20 L24 26 L21 20 L15 17 L21 14 Z"
          fill="currentColor"
          className="opacity-60"
        />
      </svg>
      <p className="text-sm max-w-[28ch] text-center leading-relaxed">
        Select an idea from the left to see its full analysis.
      </p>
    </div>
  )
}

function SkeletonScoreCards() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="bg-expedition-black border border-warm-border rounded-lg p-4 animate-pulse"
        >
          <div className="h-3 w-20 bg-warm-border rounded mb-2" />
          <div className="h-8 w-12 bg-warm-border rounded" />
          <div className="h-3 w-14 bg-warm-border rounded mt-1" />
        </div>
      ))}
    </div>
  )
}

function useFadeOnChange(dep: string | undefined) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.opacity = '0'
    el.style.transform = 'translateY(4px)'
    // Force a layout flush so the browser registers the starting style
    // before we set the transition target.
    void el.offsetHeight
    el.style.transition = 'opacity 200ms ease-out, transform 200ms ease-out'
    el.style.opacity = '1'
    el.style.transform = 'translateY(0)'
  }, [dep])

  return ref
}

function IdeaDetailContent({ idea }: { idea: Idea }) {
  const fadeRef = useFadeOnChange(idea.id)
  const score = idea.score

  return (
    <div ref={fadeRef} className="space-y-6 pb-8">
      {/* 1. Title */}
      <h2 className="text-xl font-semibold text-lamplight-ink">
        {idea.title}
      </h2>

      {/* 2. Description */}
      {idea.description && (
        <p className="text-sm text-faded-ink leading-relaxed">
          {idea.description}
        </p>
      )}

      {/* 3. Source link */}
      {idea.source_url && (
        <a
          href={idea.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-sm text-warm-teal underline underline-offset-2 hover:text-warm-teal/80 transition-colors"
        >
          View source
        </a>
      )}

      {/* 4. Composite score + 5. Verdict badge */}
      {score && (
        <div className="flex items-baseline gap-3">
          <span className="text-[3rem] font-mono font-bold text-amber-gold leading-none">
            {score.composite}
          </span>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded border ${VERDICT_STYLES[score.verdict] ?? VERDICT_STYLES.REJECT}`}
          >
            {score.verdict}
          </span>
        </div>
      )}

      {/* 6. Score dimension grid */}
      {score ? (
        <>
          <h3 className={SECTION_LABEL}>Score Dimensions</h3>
          <div className="grid grid-cols-2 gap-4">
            {SCORE_DIMENSIONS.map((dim) => (
              <ScoreCard
                key={dim.key}
                label={dim.label}
                score={score[dim.key]}
                weight={dim.weight}
              />
            ))}
          </div>
        </>
      ) : (
        <>
          <h3 className={SECTION_LABEL}>Score Dimensions</h3>
          <SkeletonScoreCards />
        </>
      )}

      {/* 7. Sentiment Flags */}
      {score && score.sentiment_flags.length > 0 && (
        <div>
          <h3 className={SECTION_LABEL}>Sentiment Flags</h3>
          <ul className="space-y-1.5">
            {score.sentiment_flags.map((flag, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-faded-ink">
                <span className="text-warm-teal mt-0.5 shrink-0">•</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 8. Risks */}
      {score && score.risks.length > 0 && (
        <div>
          <h3 className={SECTION_LABEL}>Risks</h3>
          <ul className="space-y-1.5">
            {score.risks.map((risk, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-faded-ink">
                <span className="text-brick-red mt-0.5 shrink-0">•</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 9. Tarpit warning */}
      {score?.tarpit && (
        <div className="border border-brick-red rounded-lg p-4">
          <h3 className="text-sm font-semibold text-brick-red mb-3">
            Tarpit Warning
          </h3>
          <pre className="text-xs font-mono text-faded-ink whitespace-pre-wrap break-words leading-relaxed">
            {JSON.stringify(score.tarpit, null, 2)}
          </pre>
        </div>
      )}

      {/* 10. Justification */}
      {score?.justification && (
        <div>
          <h3 className={SECTION_LABEL}>Justification</h3>
          <p className="text-sm font-medium text-lamplight-ink leading-relaxed max-w-prose">
            {score.justification}
          </p>
        </div>
      )}

      {/* 11. Related Mentions */}
      {idea.mentions.length > 0 && (
        <div>
          <h3 className={SECTION_LABEL}>Related Mentions</h3>
          <p className="text-sm text-faded-ink flex items-center gap-2 flex-wrap">
            <span>{idea.mentions.length} related mention{idea.mentions.length !== 1 ? 's' : ''}</span>
            <span className="inline-flex items-center gap-1">
              {Array.from({ length: idea.source_tier }).map((_, i) => (
                <span
                  key={i}
                  className="inline-block w-2 h-2 rounded-full bg-amber-gold"
                  aria-label={`Tier ${idea.source_tier}`}
                />
              ))}
            </span>
          </p>
        </div>
      )}
    </div>
  )
}

export function IdeaDetail({ idea }: IdeaDetailProps) {
  return (
    <div className="h-full overflow-y-auto px-6 py-5">
      {!idea ? <EmptyState /> : <IdeaDetailContent idea={idea} />}
    </div>
  )
}
