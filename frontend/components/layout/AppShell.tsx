"use client"
import { usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { Sidebar } from "@/components/layout/Sidebar"

export function AppShell({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const pathname = usePathname()
  const isPublic = pathname === "/login"

  if (isPublic || !token) {
    return <>{children}</>
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}
