export interface IdeaScore {
  composite: number
  problem_quality: number
  market_viability: number
  sentiment_signal: number
  founder_fit: number
  verdict: 'STRONG' | 'PROMISING' | 'WEAK' | 'TARPIT' | 'REJECT'
  justification: string
  sentiment_flags: string[]
  risks: string[]
  tarpit: Record<string, unknown> | null
}

export interface Idea {
  id: string
  title: string
  description: string | null
  source_type: string
  source_url: string
  source_tier: number
  composite: number | null
  verdict: string | null
  discovered_at: string
  mentions: Mention[]
  score: IdeaScore | null
}

export interface Mention {
  id: string
  source_type: string
  source_url: string
  text: string
  extracted_at: string
}

export interface Stats {
  total_ideas: number
  total_signals: number
  by_verdict: Record<string, number>
}

export interface Signal {
  id: number
  title: string
  text: string
  url: string
  source_type: string
  source_tier: number
  discovered_at: string
  processed: boolean
}

export interface DerivedProblem {
  id: string
  title: string
  description: string
  category: string
  affected_demographic: string
  signal_count: number
  severity: number
  problem_quality: number
  market_viability: number
  composite_score: number
  framework_scores: Record<string, unknown>
  risks: string[]
  tarpit_check: Record<string, unknown> | null
  innovative_solutions: InnovationSolution[]
  created_at: string
}

export interface InnovationSolution {
  title: string
  description: string
  approach: 'first_principles' | 'inversion'
  fundamental_insight: string
  feasibility: number
  novelty: number
  impact: number
  composite: number
}
