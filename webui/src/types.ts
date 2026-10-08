/* 快照类型：与后端 src/house/web/presenter.py 一一对应 */

export interface GeneInfo {
  id: string
  name: string
  state: 1 | 2 // 1 隐性携带 / 2 显性
  group: string | null
  level: number
  polarity: 'positive' | 'negative' | 'neutral'
}

export interface TraitInfo {
  id: string
  name: string
  polarity: 'positive' | 'negative' | 'neutral'
}

export interface OpinionInfo {
  id: number
  name: string
  value: number
}

export interface CharacterInfo {
  id: number
  name: string
  gender: 'male' | 'female'
  birth_year: number
  death_year: number | null
  death_reason: string | null
  alive: boolean
  age: number
  is_adult: boolean
  dynasty: number | null
  father: number | null
  mother: number | null
  spouse: number | null
  patrilineal: boolean
  children: number[]
  attributes: Record<string, number>
  potential: Record<string, number>
  genes: GeneInfo[]
  traits: TraitInfo[]
  education: string | null
  education_name: string
  health: number
  health_tier: string | null
  health_norm: number
  money: number
  prestige: number
  piety: number
  opinions: OpinionInfo[]
  children_born: number
  pregnant: boolean
  pregnancy_months_left: number | null
  relation: string | null
  culture: string
  culture_label: string
  /* 教养（CK3） */
  childhood_trait: { id: string; name: string; focus: string } | null
  education_focus: string | null
  education_focus_label: string | null
  education_score: number
  guardian: number | null
  guardian_name: string | null
  betrothed: { id: number; name: string | null; patrilineal: boolean } | null
}

export interface EventInfo {
  year: number | null
  month: number | null
  xun: number | null
  type: string
  text: string
  actors: number[]
}

export interface NamingEntry {
  child_id: number
  suggested: string
  child_name: string
  gender: 'male' | 'female'
  culture: string
  culture_label: string
  relation: string
  suggestions: string[]
}

export interface TutoringEntry {
  child_id: number
  name: string
  gender: 'male' | 'female'
  age: number
  childhood_trait: { id: string; name: string } | null
  relation: string | null
  suggested_focus: string
  focus_options: { key: string; label: string }[]
  guardian_candidates: {
    id: number
    name: string
    age: number
    skill: number
    learning: number
    suggested: boolean
  }[]
}

export interface LegacyTree {
  id: string
  label: string
  desc: string
  level: number
  max: number
  cost: number | null
  affordable: boolean
}

export interface LegacyInfo {
  renown: number
  dynasty: number | null
  trees: LegacyTree[]
}

export interface DynastyInfo {
  id: number
  name: string
  culture: string
  culture_label: string
  head: number | null
  head_name: string | null
  renown: number
  members: number
  alive_members: number
  legacies: Record<string, number>
}

export interface PopulationInfo {
  alive: number
  total: number
  soft_cap: number
  hard_cap: number
}

export interface StatsInfo {
  start_year: number
  years_played: number
  generations: number
  births: number
  deaths: number
  marriages: number
}

export interface MetaInfo {
  attrs: { key: string; label: string }[]
  xun_names: string[]
  health_tiers: { floor: number | null; label: string }[]
  consort_limit: number
  start_year: number
  cultures: Record<string, string>
  gender_laws: Record<string, string>
}

export interface Snapshot {
  date: { year: number; month: number; xun: number; label: string }
  player_id: number
  over: boolean
  over_reason: string
  gender_law: string
  gender_law_label: string
  characters: CharacterInfo[]
  dynasties: DynastyInfo[]
  events: EventInfo[]
  naming_queue: NamingEntry[]
  tutoring_queue: TutoringEntry[]
  legacies: LegacyInfo
  population: PopulationInfo
  heir: CharacterInfo | null
  stats: StatsInfo
  meta: MetaInfo
}

export interface SaveInfo {
  path: string
  name: string
  year: number | string
  month: number | string
  mtime: number
}

export interface ApiResponse {
  ok: boolean
  message: string | null
  state?: Snapshot
  exists?: boolean
  saves?: SaveInfo[]
  candidates?: CharacterInfo[]
  own?: CharacterInfo[]
  other?: CharacterInfo[]
}
