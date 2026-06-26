"use client"
import { createContext, useContext, useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"

interface AuthCtx {
  token: string | null
  login: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthCtx>({ token: null, login: () => {}, logout: () => {} })

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem("ai_frontdesk_token")
    if (stored) setToken(stored)
  }, [])

  const login = useCallback((t: string) => {
    localStorage.setItem("ai_frontdesk_token", t)
    setToken(t)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("ai_frontdesk_token")
    setToken(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

/** Redirect to /login if not authenticated. Use inside page components. */
export function useRequireAuth() {
  const { token } = useAuth()
  const router = useRouter()
  useEffect(() => {
    if (token === null) {
      const stored = localStorage.getItem("ai_frontdesk_token")
      if (!stored) router.replace("/login")
    }
  }, [token, router])
  return token
}
