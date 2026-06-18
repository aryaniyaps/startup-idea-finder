import { useState, useEffect, useCallback } from 'react'
import type { DerivedProblem } from '../api'
import { fetchProblems } from '../client'
import { Skeleton } from './Skeleton'

const CATEGORY_COLORS: Record<string, string> = {
  workflow: 'bg-amber-gold/15 text-amber-gold border-amber-gold/30',
  data: 'bg-warm-teal/15 text-warm-teal border-warm-teal/30',
  integration: 'bg-steel-blue/15 text-steel-blue border-steel-blue/30',
  compliance: 'bg-ochre/15 text-ochre border-ochre/30',
  consumer: 'bg-sage-green/15 text-sage-green border-sage-green/30',
  developer_tool: 'bg-steel-blue/15 text-steel-blue border-steel-blue/30',
  marketplace: 'bg-tier-gold/15 text-tier-gold border-tier-gold/30',
  other: 'bg-quiet-ink/15 text-quiet-ink border-quiet-ink/30',
}

export function ProblemsView() {
  const [problems, setProblems] = useState<DerivedProblem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchProblems(20, 0)
      setProblems(data.problems || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load problems')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="flex flex-col h-full">
      <header className="flex justify-between items-center py-4 border-b border-warm-border mb-4 shrink-0">
        <div>
          <h1 className="text-2xl font-semibold text-amber-gold">Derived Problems</h1>
          <span className="text-faded-ink text-sm">Patterns discovered from mass signal analysis</span>
        </div>
      </header>

      {error && (
        <div className="bg-brick-red/15 border border-brick-red/30 text-brick-red text-sm rounded-md px-4 py-2 mb-4 shrink-0" role="alert">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="space-y-4 p-2">
            <Skeleton variant="card" count={4} />
          </div>
        ) : problems.length === 0 ? (
          <div className="flex items-center justify-center h-full py-20">
            <p className="text-faded-ink">
              No problems derived yet. Run mass analysis to discover patterns from signals.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {problems.map(p => {
              const isExpanded = expandedId === p.id
              const catStyle = CATEGORY_COLORS[p.category] || CATEGORY_COLORS.other
              const verdictColor =
                p.composite_score >= 75 ? 'text-sage-green' :
                p.composite_score >= 60 ? 'text-warm-teal' :
                p.composite_score >= 40 ? 'text-ochre' :
                'text-brick-red'

              return (
                <div
                  key={p.id}
                  className="bg-journal-surface border border-warm-border rounded-lg overflow-hidden cursor-pointer transition-colors duration-150 hover:bg-raised-surface"
                  onClick={() => setExpandedId(isExpanded ? null : p.id)}
                >
                  <div className="px-5 py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-lamplight-ink">{p.title}</h3>
                        <p className="text-sm text-faded-ink mt-1 line-clamp-2">{p.description}</p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${catStyle}`}>
                          {p.category}
                        </span>
                        <div className="text-right">
                          <div className={`text-2xl font-bold font-mono ${verdictColor}`}>
                            {p.composite_score.toFixed(0)}
                          </div>
                          <div className="text-xs text-quiet-ink">
                            {p.signal_count} signals
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-5 pb-5 border-t border-warm-border mx-5">
                      {/* Description */}
                      <div className="mt-4">
                        <h4 className="text-xs uppercase tracking-wide text-faded-ink mb-2">Problem Description</h4>
                        <p className="text-sm text-lamplight-ink leading-relaxed">{p.description}</p>
                        <p className="text-xs text-faded-ink mt-2">
                          Affected: {p.affected_demographic} · Severity: {p.severity}/5 · Quality: {p.problem_quality} · Market: {p.market_viability}
                        </p>
                      </div>

                      {/* Risks */}
                      {p.risks && p.risks.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-xs uppercase tracking-wide text-faded-ink mb-2">Risks</h4>
                          <ul className="space-y-1">
                            {p.risks.map((r, i) => (
                              <li key={i} className="text-sm text-brick-red flex items-start gap-2">
                                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brick-red shrink-0" aria-hidden="true" />
                                {r}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Tarpit warning */}
                      {p.tarpit_check && Boolean((p.tarpit_check as Record<string, unknown>).is_tarpit) && (
                        <div className="mt-4 bg-brick-red/10 border border-brick-red/30 rounded-md p-3">
                          <p className="text-sm text-brick-red font-semibold">Tarpit Warning</p>
                          <p className="text-xs text-brick-red/80 mt-1">
                            {String((p.tarpit_check as Record<string, unknown>).reason ?? '')}
                          </p>
                        </div>
                      )}

                      {/* Innovative Solutions */}
                      {p.innovative_solutions && p.innovative_solutions.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-xs uppercase tracking-wide text-faded-ink mb-3">
                            Innovative Solutions ({p.innovative_solutions.length})
                          </h4>
                          <div className="space-y-3">
                            {p.innovative_solutions.map((sol, i) => (
                              <div
                                key={i}
                                className="bg-expedition-black border border-warm-border rounded-md p-3"
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                                    sol.approach === 'first_principles'
                                      ? 'bg-amber-gold/15 text-amber-gold'
                                      : 'bg-warm-teal/15 text-warm-teal'
                                  }`}>
                                    {sol.approach === 'first_principles' ? 'First Principles' : 'Inversion'}
                                  </span>
                                  <span className="text-xs text-quiet-ink">
                                    Impact: {sol.impact} · Novelty: {sol.novelty} · Score: {sol.composite}
                                  </span>
                                </div>
                                <h5 className="text-sm font-semibold text-lamplight-ink">{sol.title}</h5>
                                <p className="text-xs text-faded-ink mt-1">{sol.description}</p>
                                <p className="text-xs text-amber-gold/80 mt-1 italic">
                                  Insight: {sol.fundamental_insight}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
