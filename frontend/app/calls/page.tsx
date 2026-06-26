"use client"
import { useState } from "react"
import useSWR from "swr"
import { useRequireAuth } from "@/lib/auth"
import { swrFetcher } from "@/lib/api"
import type { CallOut, Paginated } from "@/lib/types"
import clsx from "clsx"

const STATUS_STYLE: Record<string, string> = {
  active:    "bg-green-900/40 text-green-300",
  completed: "bg-gray-700 text-gray-300",
  deleted:   "bg-red-900/40 text-red-400",
}

function formatDuration(secs: number | null) {
  if (!secs) return "—"
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
}

export default function CallsPage() {
  const token = useRequireAuth()
  const [status, setStatus] = useState("")
  const [agentType, setAgentType] = useState("")
  const [page, setPage] = useState(0)
  const limit = 20

  const params = new URLSearchParams()
  if (status) params.set("status", status)
  if (agentType) params.set("agent_type", agentType)
  params.set("limit", String(limit))
  params.set("offset", String(page * limit))

  const { data } = useSWR<Paginated<CallOut>>(
    token ? `/api/calls?${params}` : null,
    swrFetcher,
    { refreshInterval: 5000 }
  )

  const calls = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-4 max-w-7xl">
      <h1 className="text-2xl font-bold">Calls</h1>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          className="input max-w-[160px]"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(0) }}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
        </select>
        <select
          className="input max-w-[180px]"
          value={agentType}
          onChange={(e) => { setAgentType(e.target.value); setPage(0) }}
        >
          <option value="">All agents</option>
          <option value="sales_agent">Sales</option>
          <option value="support_agent">Support</option>
          <option value="booking_agent">Booking</option>
          <option value="analytics_agent">Analytics</option>
        </select>
        <span className="ml-auto self-center text-sm text-gray-400">{total} total</span>
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {["Room ID", "Status", "Agent", "Started", "Duration", "Outcome", "Sentiment"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs text-gray-400 font-medium uppercase tracking-wide">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {calls.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-500 text-sm">
                  No calls found
                </td>
              </tr>
            )}
            {calls.map((c) => (
              <tr key={c.id} className="border-b border-gray-800/50 table-row-hover">
                <td className="px-4 py-3 font-mono text-xs text-gray-400 truncate max-w-[160px]">
                  {c.livekit_room_id}
                </td>
                <td className="px-4 py-3">
                  <span className={clsx("badge text-xs px-2 py-0.5", STATUS_STYLE[c.status] ?? "bg-gray-700 text-gray-300")}>
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-300">{c.agent_type ?? "—"}</td>
                <td className="px-4 py-3 text-gray-400">{formatDate(c.started_at)}</td>
                <td className="px-4 py-3 text-gray-400">{formatDuration(c.duration_secs)}</td>
                <td className="px-4 py-3 text-gray-400">{c.outcome ?? "—"}</td>
                <td className="px-4 py-3 text-gray-400">
                  {c.sentiment_score != null ? Number(c.sentiment_score).toFixed(2) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        {total > limit && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40"
            >
              ← Prev
            </button>
            <span className="text-xs text-gray-400">
              Page {page + 1} of {Math.ceil(total / limit)}
            </span>
            <button
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage((p) => p + 1)}
              className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
