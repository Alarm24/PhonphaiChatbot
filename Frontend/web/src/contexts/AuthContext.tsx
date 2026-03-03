import { createContext, useContext, useState, type ReactNode } from 'react'

const STORAGE_KEY_USER = 'phonphai_user'

interface AuthContextValue {
  user: string | null
  login: (username: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY_USER))

  const login = (username: string) => {
    localStorage.setItem(STORAGE_KEY_USER, username)
    setUser(username)
  }

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY_USER)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
