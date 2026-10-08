export type Role = 'worker' | 'assessor' | 'moderator' | 'admin'

export type Competency = {
  id: string
  title: string
  rubric: Record<string, string>
  checklist: string[]
}

export type TradePack = {
  pack_id: string
  title: string
  summary?: string
  version?: string
  nsqf_level?: number
  trade_code?: string
  pass_threshold?: number
  safety_critical_steps?: string[]
  checklist?: string[]
  rubric?: Record<string, string>
  nos?: Array<{ id: string; title: string; description: string; prerequisites?: string[]; keywords?: string[] }>
  keywords?: string[]
}

export type MatchResult = {
  pack_id: string
  title: string
  confidence: number
  skill_gaps: string[]
  summary: string
  matched_nos?: string[]
  missing_nos?: string[]
  bridge_training?: string[]
  pack_version?: string
  nsqf_level?: number
}

export type AuditLog = {
  id: number
  action: string
  details: string
  created_at: string
}

export type AppUser = {
  username: string
  role: Role
  name: string
}

export const competencyLevels = [1, 2, 3, 4, 5]
