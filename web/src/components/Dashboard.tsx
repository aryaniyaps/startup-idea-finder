import { useCallback, useState } from 'react'
import { useIdeas } from '../hooks/useIdeas'
import { StatsRibbon } from './StatsRibbon'
import { FilterBar } from './FilterBar'
import { ConnectionStatus } from './ConnectionStatus'
import { IdeaList } from './IdeaList'
import { IdeaDetail } from './IdeaDetail'

export interface DashboardProps {
  onNavigateToProfile?: () => void
}

export function Dashboard({ onNavigateToProfile }: DashboardProps) {
  const { ideas, stats, selectedIdea, loading, error, connected, reconnecting, selectIdea, applyFilters } = useIdeas()
  const selectedId = selectedIdea?.id ?? null

  const handleFilter = useCallback(
    (f: { minScore?: number; verdict?: string }) => {
      const params: { min_score?: number; verdict?: string } = {}
      const hasMinScore = f.minScore !== undefined && f.minScore > 0
      const hasVerdict = !!f.verdict
      if (hasMinScore) params.min_score = f.minScore
      if (hasVerdict) params.verdict = f.verdict
      setHasActiveFilters(hasMinScore || hasVerdict)
      applyFilters(params).catch(() => {
        /* errors surfaced via hook's error state */
      })
    },
    [applyFilters],
  )

  const handleSelect = useCallback(
    (id: string) => {
      selectIdea(id)
    },
    [selectIdea],
  )

  const [hasActiveFilters, setHasActiveFilters] = useState(false)

  return (
    <>
      {/* Header */}
      <header className="flex justify-between items-center py-4 border-b border-warm-border mb-4 shrink-0">
        <div>
          <h1 className="text-2xl font-semibold text-amber-gold">Scout Dashboard</h1>
          <span className="text-faded-ink text-sm">AI-Powered Startup Idea Discovery</span>
        </div>
        <div className="flex items-center gap-3">
          <ConnectionStatus connected={connected} reconnecting={reconnecting} />
          <button
            onClick={onNavigateToProfile}
            className="text-faded-ink hover:text-lamplight-ink transition-colors duration-150 p-1"
            aria-label="Configure profile"
            title="Founder Profile"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>
      </header>

      {/* Stats + Filters */}
      <div className="flex flex-col gap-3 shrink-0 mb-4">
        <StatsRibbon stats={stats} />
        <FilterBar onFilter={handleFilter} />
      </div>

      {/* Error banner */}
      {error && (
        <div
          className="bg-brick-red/15 border border-brick-red/30 text-brick-red text-sm rounded-md px-4 py-2 mb-4 shrink-0"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Split pane */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4">
        {/* Left pane: Idea list */}
        <aside
          className="w-full lg:w-[35%] lg:min-w-[280px] lg:max-w-[420px] overflow-y-auto shrink-0 bg-journal-surface border border-warm-border rounded-lg"
          aria-label="Idea list"
        >
          <IdeaList
            ideas={ideas}
            selectedId={selectedId}
            onSelect={handleSelect}
            loading={loading}
            isFiltered={hasActiveFilters}
          />
        </aside>

        {/* Right pane: Idea detail */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-journal-surface border border-warm-border rounded-lg">
          <IdeaDetail idea={selectedIdea} />
        </main>
      </div>
    </>
  )
}
