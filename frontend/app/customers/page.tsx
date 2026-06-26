"use client"
import { useState } from "react"
import useSWR from "swr"
import { useRequireAuth } from "@/lib/auth"
import { swrFetcher } from "@/lib/api"
import type { CustomerSummary, Paginated } from "@/lib/types"
import clsx from "clsx"

const TIER_STYLE: Record<string, string> = {
  vip:      "bg-yellow-900/40 text-yellow-300 border border-yellow-800",
  premium:  "bg-purple-900/40 text-purple-300 border border-purple-800",
  standard: "bg-gray-800 text-gray-300 border border-gray-700",
}

function formatDate(iso: string | null) {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" })
}

export default function CustomersPage() {
  const token = useRequireAuth()
  const [tier, setTier] = useState("")
  const [page, setPage] = useState(0)
  const limit = 20

  const params = new URLSearchParams()
  if (tier) params.set("tier", tier)
  params.set("limit", String(limit))
  params.set("offset", String(page * limit))

  const { data } = useSWR<Paginated<CustomerSummary>>(
    token ? `/api/customers?${params}` : null,
    swrFetcher,
    { refreshInterval: 15_000 }
  )

  const customers = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-4 max-w-7xl">
      <h1 className="text-2xl font-bold">Customers</h1>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          className="input max-w-[160px]"
          value={tier}
          onChange={(e) => { setTier(e.target.value); setPage(0) }}
        >
          <option value="">All tiers</option>
          <option value="vip">VIP</option>
          <option value="premium">Premium</option>
          <option value="standard">Standard</option>
        </select>
        <span className="ml-auto self-center text-sm text-gray-400">{total} customers</span>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              {["Name", "Phone", "Tier", "Last Contact"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs text-gray-400 font-medium uppercase tracking-wide">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {customers.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-gray-500 text-sm">
                  No customers found
                </td>
              </tr>
            )}
            {customers.map((c) => (
              <tr key={c.id} className="border-b border-gray-800/50 table-row-hover">
                <td className="px-4 py-3 text-gray-100 font-medium">{c.name ?? "—"}</td>
                <td className="px-4 py-3 text-gray-400 font-mono text-xs">{c.phone ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={clsx("badge text-xs px-2 py-0.5", TIER_STYLE[c.tier] ?? TIER_STYLE.standard)}>
                    {c.tier}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400">{formatDate(c.last_contact)}</td>
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
