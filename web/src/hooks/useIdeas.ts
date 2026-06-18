import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Idea, Stats } from '../api'
import { fetchIdeas } from '../client'
import { useWebSocket } from './useWebSocket'

export interface IdeaFilters {
  limit?: number
  offset?: number
  min_score?: number
  verdict?: string
}

export interface UseIdeasParams {
  onWebSocketMessage?: (msg: unknown) => void
}

export interface UseIdeasState {
  ideas: Idea[]
  stats: Stats | null
  selectedIdea: Idea | null
  loading: boolean
  error: string | null
  connected: boolean
  reconnecting: boolean
  selectIdea: (id: string | null) => void
  refresh: (filters?: IdeaFilters) => Promise<void>
  applyFilters: (params: IdeaFilters) => Promise<void>
}

export function useIdeas(params?: UseIdeasParams): UseIdeasState {
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { lastMessage, connected, reconnecting } = useWebSocket()
  const onMessageRef = useRef(params?.onWebSocketMessage)
  onMessageRef.current = params?.onWebSocketMessage
  const filtersRef = useRef<IdeaFilters>({ limit: 50 })

  const doFetch = useCallback(async (filters: IdeaFilters = {}) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchIdeas(filters)
      setIdeas(result.ideas)
      setStats(result.stats)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load ideas'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    doFetch()
  }, [doFetch])

  // Handle WebSocket messages
  useEffect(() => {
    const msg = lastMessage as Record<string, unknown> | null
    if (!msg) return

    onMessageRef.current?.(msg)

    if (msg.type === 'new_ideas') {
      doFetch(filtersRef.current)
    } else if (msg.type === 'stats' && typeof msg.payload === 'object' && msg.payload !== null) {
      setStats(msg.payload as Stats)
    }
  }, [lastMessage, doFetch])

  const refresh = useCallback(async (filters?: IdeaFilters) => {
    const effective = filters ?? filtersRef.current
    await doFetch(effective)
  }, [doFetch])

  const applyFilters = useCallback(async (newFilters: IdeaFilters) => {
    filtersRef.current = newFilters
    await doFetch(newFilters)
  }, [doFetch])

  const selectIdea = useCallback((id: string | null) => {
    setSelectedIdeaId(id)
  }, [])

  const selectedIdea = useMemo(() => {
    if (selectedIdeaId === null) return null
    return ideas.find((idea) => idea.id === selectedIdeaId) ?? null
  }, [ideas, selectedIdeaId])

  return {
    ideas,
    stats,
    selectedIdea,
    loading,
    error,
    connected,
    reconnecting,
    selectIdea,
    refresh,
    applyFilters,
  }
}
