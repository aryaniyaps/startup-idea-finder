import { useRef, useEffect, useCallback } from 'react'
import type { Idea } from '../api'
import { VerdictDot } from './VerdictDot'
import { Skeleton } from './Skeleton'

interface IdeaListProps {
  ideas: Idea[]
  selectedId: string | null
  onSelect: (id: string) => void
  loading: boolean
  isFiltered?: boolean
}

export function IdeaList({
  ideas,
  selectedId,
  onSelect,
  loading,
  isFiltered = false,
}: IdeaListProps) {
  const listRef = useRef<HTMLDivElement>(null)

  const selectedIndex = ideas.findIndex((i) => i.id === selectedId)

  // Scroll selected row into view when selection changes
  useEffect(() => {
    if (selectedIndex < 0 || !listRef.current) return
    const el = listRef.current.querySelector(
      `[data-idea-id="${selectedId}"]`,
    ) as HTMLElement | null
    el?.scrollIntoView({ block: 'nearest' })
  }, [selectedId, selectedIndex])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const len = ideas.length
      if (len === 0) return

      let newIndex: number

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          newIndex =
            selectedIndex < 0 ? 0 : Math.min(selectedIndex + 1, len - 1)
          onSelect(ideas[newIndex].id)
          break
        case 'ArrowUp':
          e.preventDefault()
          newIndex =
            selectedIndex < 0 ? len - 1 : Math.max(selectedIndex - 1, 0)
          onSelect(ideas[newIndex].id)
          break
        case 'Enter':
          e.preventDefault()
          if (selectedIndex >= 0) {
            onSelect(ideas[selectedIndex].id)
          }
          break
        case 'Escape':
          e.preventDefault()
          onSelect('')
          listRef.current?.blur()
          break
      }
    },
    [ideas, selectedIndex, onSelect],
  )

  // Loading state
  if (loading) {
    return (
      <div className="p-2 space-y-1 overflow-y-auto" role="status" aria-label="Loading ideas">
        <Skeleton variant="row" count={12} />
      </div>
    )
  }

  // Empty state
  if (ideas.length === 0) {
    return (
      <div className="flex items-center justify-center h-full py-20">
        {isFiltered ? (
          <div className="text-center">
            <p className="text-faded-ink">No ideas match your filters</p>
            <p className="text-quiet-ink text-sm mt-1">
              Try adjusting or clearing your filters
            </p>
          </div>
        ) : (
          <p className="text-faded-ink">No ideas yet</p>
        )}
      </div>
    )
  }

  return (
    <div
      ref={listRef}
      className="overflow-y-auto outline-none"
      tabIndex={0}
      role="listbox"
      aria-label="Ideas"
      onKeyDown={handleKeyDown}
    >
      {ideas.map((idea, i) => {
        const isSelected = idea.id === selectedId
        const composite = idea.composite ?? idea.score?.composite ?? null

        return (
          <div
            key={idea.id}
            data-idea-id={idea.id}
            role="option"
            aria-selected={isSelected}
            onClick={() => onSelect(idea.id)}
            className={[
              'flex items-center gap-3 px-3 h-10 cursor-pointer',
              'transition-colors duration-150',
              isSelected
                ? 'bg-raised-surface text-lamplight-ink'
                : 'text-lamplight-ink hover:bg-journal-surface',
            ].join(' ')}
            style={
              isSelected
                ? { boxShadow: 'inset 2px 0 0 0 var(--color-amber-gold)' }
                : undefined
            }
          >
            {/* Rank */}
            <span className="w-6 text-right text-xs text-faded-ink shrink-0 tabular-nums">
              {i + 1}
            </span>

            {/* Title */}
            <span className="flex-1 truncate text-sm">{idea.title}</span>

            {/* Composite score */}
            <span
              className={[
                'w-10 text-right text-sm font-mono tabular-nums shrink-0',
                composite !== null && composite >= 75
                  ? 'text-amber-gold'
                  : 'text-lamplight-ink',
              ].join(' ')}
            >
              {composite !== null ? composite : '—'}
            </span>

            {/* Verdict dot */}
            {idea.verdict ? (
              <VerdictDot verdict={idea.verdict} />
            ) : (
              <span className="w-2 shrink-0" aria-hidden="true" />
            )}
          </div>
        )
      })}
    </div>
  )
}
