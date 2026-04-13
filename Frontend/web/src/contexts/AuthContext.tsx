import { createContext, useContext, useState, type ReactNode } from 'react'
import { loginApi, registerApi } from '../services/api'

const STORAGE_KEY_USER = 'phonphai_user'

interface AuthContextValue {
  user: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY_USER))

  const login = async (email: string, password: string) => {
    const data = await loginApi(email, password)
    localStorage.setItem(STORAGE_KEY_USER, data.email)
    setUser(data.email)
  }

  const register = async (email: string, password: string) => {
    await registerApi(email, password)
    // Auto-login after registration
    const data = await loginApi(email, password)
    localStorage.setItem(STORAGE_KEY_USER, data.email)
    setUser(data.email)
  }

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY_USER)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, register, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
