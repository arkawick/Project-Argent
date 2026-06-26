"use client"
import { useState, useCallback } from "react"
import { useRequireAuth } from "@/lib/auth"
import { api } from "@/lib/api"
import { useCallSocket } from "@/lib/hooks/useCallSocket"
import { VoiceRoom } from "@/components/voice/VoiceRoom"

const LK_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "ws://localhost:7880"
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function generateId() {
  return "call-" + Math.random().toString(36).slice(2, 10)
}

type Phase = "idle" | "connecting" | "active" | "ended"

export default function DemoPage() {
  useRequireAuth()
  const [phase, setPhase] = useState<Phase>("idle")
  const [callId, setCallId] = useState<string | null>(null)
  const [lkToken, setLkToken] = useState<string | null>(null)
  const { events, endCall } = useCallSocket(phase === "active" ? callId : null)

  const startCall = useCallback(async () => {
    setPhase("connecting")
    try {
      const id = generateId()
      // Get LiveKit user token from backend
      const resp = await fetch(
        `${API_BASE}/api/livekit/token?room=${id}&identity=user-${Date.now()}`
      )
      const { token } = await resp.json()

      setCallId(id)
      setLkToken(token)
      setPhase("active")
    } catch (err) {
      console.error("Failed to start call:", err)
      setPhase("idle")
    }
  }, [])

  const handleEnd = useCallback(() => {
    endCall()
    setPhase("ended")
    setCallId(null)
    setLkToken(null)
  }, [endCall])

  // ── Idle screen ───────────────────────────────────────────────────────────────
  if (phase === "idle" || phase === "connecting") {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-8 text-center">
        <div className="space-y-3">
          <div className="text-6xl">◎</div>
          <h1 className="text-3xl font-bold">AI FrontDesk Demo</h1>
          <p className="text-gray-400 max-w-md">
            Click the button below to start a live voice conversation with the AI agent.
            The system will detect your intent and route you to the best specialist.
          </p>
        </div>

        <div className="flex gap-4 flex-wrap justify-center text-sm text-gray-500">
          {["Sales · Alex", "Support · Jordan", "Booking · Riley", "Analytics"].map((a) => (
            <span key={a} className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1">
              {a}
            </span>
          ))}
        </div>

        <button
          onClick={startCall}
          disabled={phase === "connecting"}
          className="btn-primary text-base px-8 py-4 rounded-xl shadow-lg shadow-indigo-900/30 disabled:opacity-60"
        >
          {phase === "connecting" ? "Connecting…" : "🎙 Start Demo Call"}
        </button>

        <p className="text-xs text-gray-600">
          Your browser will request microphone permission when you click.
        </p>
      </div>
    )
  }

  // ── Ended screen ──────────────────────────────────────────────────────────────
  if (phase === "ended") {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div className="text-5xl">✓</div>
        <h2 className="text-2xl font-semibold">Call ended</h2>
        <p className="text-gray-400">
          The call transcript and insights have been saved to the database.
        </p>
        <div className="flex gap-3">
          <button onClick={() => setPhase("idle")} className="btn-primary px-6 py-2.5">
            New Call
          </button>
          <a href="/calls" className="btn-ghost px-6 py-2.5">
            View Calls
          </a>
        </div>
      </div>
    )
  }

  // ── Active call ───────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-bold">Live Call</h1>
        <span className="badge bg-green-900/40 text-green-300 border border-green-800 animate-pulse">
          ● LIVE
        </span>
        <span className="text-xs text-gray-500 ml-auto">Room: {callId}</span>
      </div>

      <div className="flex-1 min-h-0">
        {lkToken && (
          <VoiceRoom
            token={lkToken}
            serverUrl={LK_URL}
            events={events}
            onEnd={handleEnd}
          />
        )}
      </div>
    </div>
  )
}
