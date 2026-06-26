"use client"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import clsx from "clsx"

const nav = [
  { href: "/", label: "Dashboard", icon: "▤" },
  { href: "/demo", label: "Demo Call", icon: "◎" },
  { href: "/calls", label: "Calls", icon: "📞" },
  { href: "/customers", label: "Customers", icon: "👥" },
  { href: "/tickets", label: "Tickets", icon: "🎫" },
]

export function Sidebar() {
  const pathname = usePathname()
  const { logout } = useAuth()
  const router = useRouter()

  const handleLogout = () => {
    logout()
    router.push("/login")
  }

  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <span className="text-lg font-bold text-indigo-400">AI FrontDesk</span>
        <p className="text-xs text-gray-500 mt-0.5">Autonomous voice OS</p>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ href, label, icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                active
                  ? "bg-indigo-600/20 text-indigo-300 font-medium"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              )}
            >
              <span className="text-base leading-none">{icon}</span>
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-gray-800">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition-colors"
        >
          <span className="text-base leading-none">↩</span>
          Sign out
        </button>
      </div>
    </aside>
  )
}
