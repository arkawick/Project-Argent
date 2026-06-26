"use client"
import type { OverviewMetrics, LiveMetrics } from "@/lib/types"

interface Props {
  overview?: OverviewMetrics
  live?: LiveMetrics | null
}

function Stat({ label, value, sub, color = "text-white" }: {
  label: string
  value: string | number
  sub?: string
  color?: string
}) {
  return (
    <div className="card flex flex-col gap-1">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </div>
  )
}

export function MetricsGrid({ overview, live }: Props) {
  const activeCalls = live?.active_calls ?? overview?.active_calls ?? "—"
  const totalCalls = overview?.total_calls ?? "—"
  const openTickets = overview?.open_tickets ?? "—"
  const resolution = overview?.resolution_rate != null
    ? `${(overview.resolution_rate * 100).toFixed(1)}%`
    : "—"
  const sentiment = overview?.avg_sentiment != null
    ? overview.avg_sentiment.toFixed(2)
    : "—"
  const customers = overview?.total_customers ?? "—"
  const latency = live?.avg_latency_ms != null
    ? `${Math.round(live.avg_latency_ms)} ms`
    : "—"
  const appts = overview?.appointments_today ?? "—"

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Stat label="Active Calls" value={activeCalls} sub="live" color="text-green-400" />
      <Stat label="Total Calls" value={totalCalls} />
      <Stat label="Resolution Rate" value={resolution} />
      <Stat label="Avg Sentiment" value={sentiment} sub="0 = neutral, ±1 extreme" />
      <Stat label="Customers" value={customers} />
      <Stat label="Open Tickets" value={openTickets} color={typeof openTickets === "number" && openTickets > 0 ? "text-yellow-400" : "text-white"} />
      <Stat label="Appts Today" value={appts} />
      <Stat label="Avg Latency" value={latency} sub="turn-around time" />
    </div>
  )
}
