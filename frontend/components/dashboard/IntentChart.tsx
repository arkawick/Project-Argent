"use client"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts"
import type { IntentDataPoint } from "@/lib/types"

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#a78bfa", "#06b6d4"]

interface Props {
  data: IntentDataPoint[]
}

export function IntentChart({ data }: Props) {
  const chartData = data.slice(0, 6) // top 6 intents

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Intent Breakdown</h3>
      {chartData.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-8">No data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="count"
              nameKey="intent"
              cx="50%"
              cy="45%"
              outerRadius={80}
              innerRadius={40}
              paddingAngle={3}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
              labelStyle={{ color: "#e5e7eb" }}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, color: "#9ca3af" }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
