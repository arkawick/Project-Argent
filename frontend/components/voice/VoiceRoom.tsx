"use client"
import "@livekit/components-styles"
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useTrackToggle,
  useConnectionState,
} from "@livekit/components-react"
import { ConnectionState, Track } from "livekit-client"
import clsx from "clsx"
import type { CallEvent } from "@/lib/types"
import { LiveTranscript } from "./LiveTranscript"
import { EmotionBadge } from "./EmotionBadge"

// ── Inner component (must be inside LiveKitRoom) ──────────────────────────────

function CallControls({ onEnd }: { onEnd: () => void }) {
  const { toggle, enabled } = useTrackToggle({ source: Track.Source.Microphone })
  const state = useConnectionState()
  const isConnected = state === ConnectionState.Connected

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => toggle()}
        disabled={!isConnected}
        className={clsx(
          "btn text-sm px-5 py-2.5",
          enabled
            ? "bg-green-700 hover:bg-green-600 text-white"
            : "bg-gray-700 hover:bg-gray-600 text-gray-300"
        )}
      >
        {enabled ? "🎙 Mute" : "🔇 Unmute"}
      </button>
      <button
        onClick={onEnd}
        className="btn bg-red-700 hover:bg-red-600 text-white px-5 py-2.5"
      >
        📵 End Call
      </button>
    </div>
  )
}

function ConnectionIndicator() {
  const state = useConnectionState()
  const label: Record<ConnectionState, string> = {
    [ConnectionState.Connecting]: "Connecting…",
    [ConnectionState.Connected]: "Connected",
    [ConnectionState.Disconnected]: "Disconnected",
    [ConnectionState.Reconnecting]: "Reconnecting…",
    [ConnectionState.SignalReconnecting]: "Reconnecting signal…",
  }
  const dot =
    state === ConnectionState.Connected ? "bg-green-500" : "bg-yellow-500 animate-pulse"

  return (
    <div className="flex items-center gap-2">
      <span className={clsx("w-2 h-2 rounded-full", dot)} />
      <span className="text-xs text-gray-400">{label[state]}</span>
    </div>
  )
}

// ── VoiceRoom props ────────────────────────────────────────────────────────────

interface Props {
  token: string
  serverUrl: string
  events: CallEvent[]
  onEnd: () => void
}

export function VoiceRoom({ token, serverUrl, events, onEnd }: Props) {
  // Derive display state from events
  const lastTurnEvent = [...events]
    .reverse()
    .find((e): e is Extract<CallEvent, { type: "turn_change" }> => e.type === "turn_change")
  const lastAgentEvent = [...events]
    .reverse()
    .find((e): e is Extract<CallEvent, { type: "agent_route" }> => e.type === "agent_route")
  const lastTranscript = [...events]
    .reverse()
    .find((e): e is Extract<CallEvent, { type: "transcript" }> => e.type === "transcript")

  const turnState = lastTurnEvent?.state ?? "listening"
  const agentName = lastAgentEvent?.agent ?? "—"
  const emotion = lastTranscript?.speaker === "user" ? lastTranscript.emotion : null

  const turnLabel: Record<string, string> = {
    listening: "🎙 Listening…",
    processing: "⚙️ Processing…",
    speaking: "🔊 Agent speaking",
  }

  const AGENT_LABEL: Record<string, string> = {
    sales_agent: "Alex (Sales)",
    support_agent: "Jordan (Support)",
    booking_agent: "Riley (Booking)",
    analytics_agent: "Analytics",
    fallback_node: "Fallback",
    unknown: "—",
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={true}
      video={false}
      data-lk-theme="default"
    >
      {/* Plays agent TTS through browser speaker */}
      <RoomAudioRenderer />

      <div className="flex flex-col h-full gap-4">
        {/* Status bar */}
        <div className="card flex items-center justify-between py-3">
          <ConnectionIndicator />
          <span className="text-sm text-gray-300">{turnLabel[turnState]}</span>
          <div className="flex items-center gap-3">
            {emotion && <EmotionBadge emotion={emotion} />}
            <span className="text-xs text-gray-500">
              Agent: <span className="text-indigo-400">{AGENT_LABEL[agentName] ?? agentName}</span>
            </span>
          </div>
        </div>

        {/* Live transcript — scrollable */}
        <div className="card flex-1 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
          <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-3">Live Transcript</h3>
          <div className="flex-1 overflow-y-auto">
            <LiveTranscript events={events} />
          </div>
        </div>

        {/* Controls */}
        <div className="flex justify-center">
          <CallControls onEnd={onEnd} />
        </div>
      </div>
    </LiveKitRoom>
  )
}
