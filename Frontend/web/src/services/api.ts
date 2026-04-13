import type { ChatApiResponse } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8080'

// --- Auth API ---

export async function registerApi(
  email: string,
  password: string,
): Promise<{ message: string; email: string }> {
  const res = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? 'Registration failed')
  }
  return res.json()
}

export async function loginApi(
  email: string,
  password: string,
): Promise<{ message: string; email: string }> {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? 'Login failed')
  }
  return res.json()
}

export async function sendMessage(
  sessionId: string,
  message: string,
  userId: string = '',
): Promise<ChatApiResponse> {
  const res = await fetch(`${API_URL}/api/v1/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, user_id: userId }),
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
  userId: string = '',
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, user_id: userId }),
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
