// TypeScript interfaces mirroring the backend Pydantic schemas

export interface CallOut {
  id: string
  customer_id: string | null
  livekit_room_id: string
  status: string
  started_at: string
  ended_at: string | null
  duration_secs: number | null
  agent_type: string | null
  transcript: TranscriptTurn[]
  summary: string | null
  sentiment_score: number | null
  outcome: string | null
  created_at: string
}

export interface TranscriptTurn {
  speaker: "user" | "agent"
  text: string
  ts: number
  emotion: string | null
  intent: string | null
}

export interface InsightOut {
  id: string
  call_id: string
  turn_number: number
  speaker: string
  text: string
  emotion: string | null
  intent: string | null
  latency_ms: number | null
}

export interface CustomerOut {
  id: string
  name: string | null
  phone: string | null
  email: string | null
  company: string | null
  tier: string
  lifetime_value: number
  first_contact: string
  last_contact: string | null
  preferences: Record<string, unknown>
  tags: string[]
  created_at: string
}

export interface CustomerSummary {
  id: string
  name: string | null
  phone: string | null
  tier: string
  last_contact: string | null
}

export interface TicketOut {
  id: string
  customer_id: string
  call_id: string | null
  title: string
  description: string | null
  priority: string
  status: string
  category: string | null
  resolution: string | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface AppointmentOut {
  id: string
  customer_id: string
  call_id: string | null
  title: string
  description: string | null
  scheduled_at: string
  duration_mins: number
  status: string
  agent_notes: string | null
  reminder_sent: boolean
  created_at: string
}

export interface OverviewMetrics {
  total_calls: number
  active_calls: number
  avg_duration_secs: number | null
  resolution_rate: number | null
  avg_sentiment: number | null
  total_customers: number
  open_tickets: number
  appointments_today: number
}

export interface EmotionDataPoint {
  date: string
  emotion: string
  count: number
}

export interface IntentDataPoint {
  intent: string
  count: number
}

export interface AgentStat {
  agent_type: string
  calls_handled: number
  avg_sentiment: number | null
  avg_duration_secs: number | null
  resolution_rate: number | null
}

// Dashboard WebSocket payload
export interface LiveMetrics {
  type: "metrics"
  active_calls: number
  emotion_counts: { emotion: string; count: number }[]
  intent_counts: { intent: string; count: number }[]
  avg_latency_ms: number | null
}

// Call WebSocket events
export type CallEvent =
  | { type: "transcript"; speaker: "user" | "agent"; text: string; emotion: string | null; intent: string | null }
  | { type: "turn_change"; state: "listening" | "processing" | "speaking" }
  | { type: "agent_route"; agent: string; confidence: number }
  | { type: "barge_in" }

export interface Paginated<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}
