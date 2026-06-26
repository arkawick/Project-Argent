"use client"
import { useState } from "react"
import useSWR from "swr"
import { useRequireAuth } from "@/lib/auth"
import { swrFetcher } from "@/lib/api"
import type { TicketOut, Paginated } from "@/lib/types"
import clsx from "clsx"

const PRIORITY_STYLE: Record<string, string> = {
  critical: "bg-red-900/40 text-red-300",
  high:     "bg-orange-900/40 text-orange-300",
  medium:   "bg-yellow-900/40 text-yellow-300",
  low:      "bg-gray-700 text-gray-400",
}

const STATUS_STYLE: Record<string, string> = {
  open:        "bg-blue-900/40 text-blue-300",
  in_progress: "bg-indigo-900/40 text-indigo-300",
  resolved:    "bg-green-900/40 text-green-300",
  closed:      "bg-gray-700 text-gray-400",
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" })
}

export default function TicketsPage() {
  const token = useRequireAuth()
  const [status, setStatus] = useState("")
  const [priority, setPriority] = useState("")
  const [page, setPage] = useState(0)
  const limit = 20

  const params = new URLSearchParams()
  if (status) params.set("status", status)
  if (priority) params.set("priority", priority)
  params.set("limit", String(limit))
  params.set("offset", String(page * limit))

  const { data } = useSWR<Paginated<TicketOut>>(
    token ? `/api/tickets?${params}` : null,
    swrFetcher,
    { refreshInterval: 10_000 }
  )

  const tickets = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-4 max-w-7xl">
      <h1 className="text-2xl font-bold">Tickets</h1>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          className="input max-w-[160px]"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(0) }}
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select
          className="input max-w-[160px]"
          value={priority}
          onChange={(e) => { setPriority(e.target.value); setPage(0) }}
        >
          <option value="">All priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <span className="ml-auto self-center text-sm text-gray-400">{total} tickets</span>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {["Title", "Priority", "Status", "Category", "Created"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs text-gray-400 font-medium uppercase tracking-wide">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickets.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-gray-500 text-sm">
                  No tickets found
                </td>
              </tr>
            )}
            {tickets.map((t) => (
              <tr key={t.id} className="border-b border-gray-800/50 table-row-hover">
                <td className="px-4 py-3 text-gray-100 max-w-xs truncate" title={t.title}>
                  {t.title}
                </td>
                <td className="px-4 py-3">
                  <span className={clsx("badge text-xs px-2 py-0.5", PRIORITY_STYLE[t.priority] ?? "bg-gray-700 text-gray-400")}>
                    {t.priority}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={clsx("badge text-xs px-2 py-0.5", STATUS_STYLE[t.status] ?? "bg-gray-700 text-gray-400")}>
                    {t.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400">{t.category ?? "—"}</td>
                <td className="px-4 py-3 text-gray-400">{formatDate(t.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>

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
