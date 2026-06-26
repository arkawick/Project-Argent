"use client"
import { useEffect, useRef, useState } from "react"
import type { CallEvent } from "@/lib/types"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"
const MAX_EVENTS = 200

export function useCallSocket(callId: string | null) {
  const [events, setEvents] = useState<CallEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!callId) return

    const ws = new WebSocket(`${WS_BASE}/ws/calls/${callId}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as CallEvent
        setEvents((prev) => [...prev.slice(-(MAX_EVENTS - 1)), event])
      } catch {}
    }

    ws.onclose = () => {
      setConnected(false)
      wsRef.current = null
    }

    return () => {
      try {
        ws.send(JSON.stringify({ type: "end_call" }))
      } catch {}
      ws.close()
    }
  }, [callId])

  const endCall = () => {
    try {
      wsRef.current?.send(JSON.stringify({ type: "end_call" }))
    } catch {}
  }

  return { events, connected, endCall }
}
