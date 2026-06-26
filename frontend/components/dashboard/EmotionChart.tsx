"use client"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import type { EmotionDataPoint } from "@/lib/types"

const EMOTION_COLORS: Record<string, string> = {
  happy: "#22c55e",
  excited: "#a78bfa",
  neutral: "#9ca3af",
  confused: "#fbbf24",
  frustrated: "#f97316",
  angry: "#ef4444",
  sad: "#60a5fa",
}

function getColor(emotion: string) {
  return EMOTION_COLORS[emotion.toLowerCase()] ?? "#6366f1"
}

interface Props {
  data: EmotionDataPoint[]
}

export function EmotionChart({ data }: Props) {
  // Aggregate by emotion across dates for the bar chart
  const aggregated = data.reduce<Record<string, number>>((acc, d) => {
    acc[d.emotion] = (acc[d.emotion] ?? 0) + d.count
    return acc
  }, {})

  const chartData = Object.entries(aggregated)
    .map(([emotion, count]) => ({ emotion, count }))
    .sort((a, b) => b.count - a.count)

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Emotion Distribution</h3>
      {chartData.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-8">No data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="emotion"
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
              labelStyle={{ color: "#e5e7eb" }}
              itemStyle={{ color: "#9ca3af" }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.emotion} fill={getColor(entry.emotion)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
