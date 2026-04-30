import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { loginRequest } from '../services/api'
import type { AuthUser } from '../types'

const STORAGE_KEY_TOKEN = 'phonphai_token'
const STORAGE_KEY_USER = 'phonphai_user'

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEY_USER)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY_TOKEN))
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())

  // Keep storage in sync if values change in other tabs.
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY_TOKEN) setToken(e.newValue)
      if (e.key === STORAGE_KEY_USER) setUser(readStoredUser())
    }
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [])

  const login = async (username: string, password: string) => {
    const result = await loginRequest(username, password)
    localStorage.setItem(STORAGE_KEY_TOKEN, result.token)
    localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(result.user))
    setToken(result.token)
    setUser(result.user)
  }

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY_TOKEN)
    localStorage.removeItem(STORAGE_KEY_USER)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>{children}</AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
