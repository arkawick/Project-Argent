"use client"
import { useEffect, useRef, useState } from "react"
import type { LiveMetrics } from "@/lib/types"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

export function useLiveDashboard(): LiveMetrics | null {
  const [metrics, setMetrics] = useState<LiveMetrics | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`${WS_BASE}/ws/dashboard`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as LiveMetrics
          if (data.type === "metrics") setMetrics(data)
        } catch {}
      }

      ws.onclose = () => {
        // Reconnect after 3 s on unexpected close
        setTimeout(connect, 3000)
      }
    }

    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return metrics
}
