export interface Message {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
  isThinking?: boolean
  isStreaming?: boolean
}

export interface ChatApiResponse {
  session_id: string
  response: string
  sources: { title: string; theme: string; content: string }[]
}

export interface AuthUser {
  user_id: string
  username: string
  role: 'admin' | 'user'
  staff_id: number | null
}
