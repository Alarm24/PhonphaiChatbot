import type { AuthUser, ChatApiResponse } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8080'

const STORAGE_KEY_TOKEN = 'phonphai_token'

function getToken(): string | null {
  return localStorage.getItem(STORAGE_KEY_TOKEN)
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export interface LoginResponse {
  token: string
  user: AuthUser
}

export async function loginRequest(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail || 'Login failed')
  }
  return res.json() as Promise<LoginResponse>
}

export async function fetchMe(): Promise<AuthUser> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { ...authHeaders() },
  })
  if (!res.ok) throw new Error('Not authenticated')
  return res.json() as Promise<AuthUser>
}

export async function sendMessage(
  sessionId: string,
  message: string,
): Promise<ChatApiResponse> {
  const res = await fetch(`${API_URL}/api/v1/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<ChatApiResponse>
}

export async function sendMessageStream(
  sessionId: string,
  message: string,
  onToken: (token: string) => void,
  onDone: (data: ChatApiResponse) => void,
  onError: (error: string) => void,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ session_id: sessionId, message }),
  })

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const parsed = JSON.parse(line.slice(6))

      if (parsed.type === 'token') {
        onToken(parsed.content)
      } else if (parsed.type === 'done') {
        onDone({
          session_id: parsed.session_id,
          response: parsed.response,
          sources: parsed.sources,
        })
      } else if (parsed.type === 'error') {
        onError(parsed.message)
      }
    }
  }
}
