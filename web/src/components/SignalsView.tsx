import { useState, useEffect, useCallback } from 'react'
import type { Signal } from '../api'
import { fetchSignals } from '../client'
import { TierBadge } from './TierBadge'
import { Skeleton } from './Skeleton'

export function SignalsView() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sourceFilter, setSourceFilter] = useState('')
  const [page, setPage] = useState(0)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { limit: 30, offset: page * 30 }
      if (sourceFilter) params.source_type = sourceFilter
      const data = await fetchSignals(params)
      setSignals(data.signals)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signals')
    } finally {
      setLoading(false)
    }
  }, [page, sourceFilter])

  useEffect(() => { load() }, [load])

  return (
    <div className="flex flex-col h-full">
      <header className="flex justify-between items-center py-4 border-b border-warm-border mb-4 shrink-0">
        <div>
          <h1 className="text-2xl font-semibold text-amber-gold">Signals</h1>
          <span className="text-faded-ink text-sm">Raw community signals collected by the pipeline</span>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={sourceFilter}
            onChange={e => { setSourceFilter(e.target.value); setPage(0) }}
            className="bg-expedition-black text-lamplight-ink border border-warm-border rounded-md px-3 py-1.5 text-sm"
            aria-label="Filter by source"
          >
            <option value="">All Sources</option>
            <option value="reddit">Reddit</option>
            <option value="hn">Hacker News</option>
            <option value="twitter">Twitter/X</option>
            <option value="github_issue">GitHub Issues</option>
            <option value="review">Reviews</option>
            <option value="news">News</option>
            <option value="job_board">Job Boards</option>
            <option value="worldmonitor">World Monitor</option>
          </select>
        </div>
      </header>

      {error && (
        <div className="bg-brick-red/15 border border-brick-red/30 text-brick-red text-sm rounded-md px-4 py-2 mb-4 shrink-0" role="alert">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="space-y-2 p-2">
            <Skeleton variant="row" count={10} />
          </div>
        ) : signals.length === 0 ? (
          <div className="flex items-center justify-center h-full py-20">
            <p className="text-faded-ink">
              {sourceFilter ? 'No signals match this source filter.' : 'No signals yet. Run the pipeline to start collecting.'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {signals.map(sig => {
              const isExpanded = expandedId === sig.id
              return (
                <div
                  key={sig.id}
                  className="bg-journal-surface border border-warm-border rounded-lg overflow-hidden cursor-pointer transition-colors duration-150 hover:bg-raised-surface"
                  onClick={() => setExpandedId(isExpanded ? null : sig.id)}
                >
                  <div className="flex items-start gap-3 px-4 py-3">
                    <span className="text-xs text-faded-ink mt-0.5 font-mono shrink-0">#{sig.id}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-lamplight-ink truncate">{sig.title}</p>
                      <p className="text-xs text-faded-ink mt-1 line-clamp-2">
                        {(sig.text || '').slice(0, 200)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <TierBadge tier={sig.source_tier} />
                      <span className="text-xs text-quiet-ink font-mono">
                        {sig.discovered_at?.slice(0, 10)}
                      </span>
                      <span className="text-xs text-faded-ink bg-warm-border/30 rounded px-2 py-0.5">
                        {sig.source_type}
                      </span>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-0 border-t border-warm-border mx-4">
                      <p className="text-sm text-lamplight-ink whitespace-pre-wrap mt-3 leading-relaxed">
                        {sig.text || sig.title}
                      </p>
                      {sig.url && (
                        <a
                          href={sig.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block mt-2 text-xs text-warm-teal hover:underline"
                          onClick={e => e.stopPropagation()}
                        >
                          View source →
                        </a>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      {!loading && signals.length > 0 && (
        <div className="flex justify-center gap-4 py-4 shrink-0 border-t border-warm-border mt-4">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-4 py-2 text-sm text-faded-ink hover:text-lamplight-ink disabled:opacity-30 transition-colors duration-150"
          >
            ← Previous
          </button>
          <span className="text-sm text-faded-ink self-center">Page {page + 1}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={signals.length < 30}
            className="px-4 py-2 text-sm text-faded-ink hover:text-lamplight-ink disabled:opacity-30 transition-colors duration-150"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
