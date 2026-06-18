import type { Idea, Stats } from './api'

const BASE = '/api'

export async function fetchIdeas(params?: {
  limit?: number
  offset?: number
  min_score?: number
  verdict?: string
}): Promise<{ ideas: Idea[]; stats: Stats }> {
  const sp = new URLSearchParams()
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  if (params?.min_score) sp.set('min_score', String(params.min_score))
  if (params?.verdict) sp.set('verdict', params.verdict)
  const qs = sp.toString()
  const res = await fetch(`${BASE}/ideas${qs ? '?' + qs : ''}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchIdeaDetail(id: string): Promise<Idea> {
  const res = await fetch(`${BASE}/idea/${id}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${BASE}/stats`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchSignals(params?: {
  limit?: number
  offset?: number
  source_type?: string
}): Promise<{ signals: import('./api').Signal[]; stats: Record<string, unknown> }> {
  const sp = new URLSearchParams()
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  if (params?.source_type) sp.set('source_type', params.source_type)
  const qs = sp.toString()
  const res = await fetch(`${BASE}/signals${qs ? '?' + qs : ''}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchSignalStats(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/signals/stats`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchProblems(
  limit: number = 20,
  offset: number = 0,
): Promise<{ problems: import('./api').DerivedProblem[] }> {
  const res = await fetch(`${BASE}/problems?limit=${limit}&offset=${offset}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
