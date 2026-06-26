import clsx from "clsx"

const CONFIG: Record<string, { label: string; cls: string }> = {
  happy:       { label: "😊 Happy",       cls: "bg-green-900/40 text-green-300 border-green-800" },
  excited:     { label: "🎉 Excited",     cls: "bg-purple-900/40 text-purple-300 border-purple-800" },
  neutral:     { label: "😐 Neutral",     cls: "bg-gray-800 text-gray-300 border-gray-700" },
  confused:    { label: "🤔 Confused",    cls: "bg-yellow-900/40 text-yellow-300 border-yellow-800" },
  frustrated:  { label: "😤 Frustrated",  cls: "bg-orange-900/40 text-orange-300 border-orange-800" },
  angry:       { label: "😠 Angry",       cls: "bg-red-900/40 text-red-300 border-red-800" },
  sad:         { label: "😢 Sad",         cls: "bg-blue-900/40 text-blue-300 border-blue-800" },
}

export function EmotionBadge({ emotion }: { emotion: string | null }) {
  if (!emotion) return null
  const cfg = CONFIG[emotion.toLowerCase()] ?? { label: emotion, cls: "bg-gray-800 text-gray-300 border-gray-700" }
  return (
    <span className={clsx("badge border text-xs px-3 py-1", cfg.cls)}>
      {cfg.label}
    </span>
  )
}
