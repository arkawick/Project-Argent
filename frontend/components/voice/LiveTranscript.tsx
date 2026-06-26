"use client"
import { useEffect, useRef } from "react"
import clsx from "clsx"
import type { CallEvent } from "@/lib/types"
import { EmotionBadge } from "./EmotionBadge"

interface Props {
  events: CallEvent[]
}

export function LiveTranscript({ events }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [events])

  const transcripts = events.filter((e): e is Extract<CallEvent, { type: "transcript" }> =>
    e.type === "transcript"
  )

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto pr-1">
      {transcripts.length === 0 && (
        <p className="text-sm text-gray-500 text-center mt-8">
          Transcript will appear here as you speak…
        </p>
      )}
      {transcripts.map((t, i) => {
        const isUser = t.speaker === "user"
        return (
          <div
            key={i}
            className={clsx(
              "flex flex-col gap-1 max-w-[85%]",
              isUser ? "self-end items-end" : "self-start items-start"
            )}
          >
            <span className="text-[10px] text-gray-500 uppercase tracking-wide px-1">
              {isUser ? "You" : "Agent"}
            </span>
            <div
              className={clsx(
                "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                isUser
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
              )}
            >
              {t.text}
            </div>
            {t.emotion && !isUser && (
              <EmotionBadge emotion={t.emotion} />
            )}
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
