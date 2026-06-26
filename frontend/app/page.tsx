"use client"
import { useRequireAuth } from "@/lib/auth"
import { useLiveDashboard } from "@/lib/hooks/useDashboard"
import useSWR from "swr"
import { swrFetcher } from "@/lib/api"
import { MetricsGrid } from "@/components/dashboard/MetricsGrid"
import { EmotionChart } from "@/components/dashboard/EmotionChart"
import { IntentChart } from "@/components/dashboard/IntentChart"
import type { OverviewMetrics, EmotionDataPoint, IntentDataPoint } from "@/lib/types"
import Link from "next/link"

export default function DashboardPage() {
  const token = useRequireAuth()
  const live = useLiveDashboard()

  const { data: overview } = useSWR<OverviewMetrics>(
    token ? "/api/analytics/overview" : null,
    swrFetcher,
    { refreshInterval: 30_000 }
  )
  const { data: emotionsResp } = useSWR<{ data: EmotionDataPoint[] }>(
    token ? "/api/analytics/emotions?period=week" : null,
    swrFetcher,
    { refreshInterval: 30_000 }
  )
  const { data: intentsResp } = useSWR<{ data: IntentDataPoint[] }>(
    token ? "/api/analytics/intents?period=week" : null,
    swrFetcher,
    { refreshInterval: 30_000 }
  )

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">Live metrics update every 2 seconds</p>
        </div>
        <Link href="/demo" className="btn-primary px-5 py-2.5 text-sm">
          ◎ Start Demo Call
        </Link>
      </div>

      {/* KPI grid */}
      <MetricsGrid overview={overview} live={live} />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EmotionChart data={emotionsResp?.data ?? []} />
        <IntentChart data={intentsResp?.data ?? []} />
      </div>

      {/* Live feed pill */}
      {live && live.active_calls > 0 && (
        <div className="flex items-center gap-3 bg-green-900/20 border border-green-800 rounded-xl px-5 py-3">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm text-green-300">
            {live.active_calls} active {live.active_calls === 1 ? "call" : "calls"} in progress
          </span>
        </div>
      )}
    </div>
  )
}
