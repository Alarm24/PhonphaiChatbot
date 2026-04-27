import { useState, useEffect, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { Message } from '../types'
import { sendMessageStream } from '../services/api'
import { useLanguage } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'
import { containsSknCode } from '../utils/skn'

const STORAGE_KEY_SESSION = 'phonphai_session_id'
const STORAGE_KEY_MESSAGES = 'phonphai_messages'

const MOCK_DELAY_MS = Number(import.meta.env.VITE_MOCK_THINKING_MS ?? 0)

function makeGreeting(greetingText: string): Message {
  return {
    id: uuidv4(),
    text: greetingText,
    sender: 'bot',
    timestamp: new Date(),
  }
}

function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_MESSAGES)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Array<Record<string, unknown>>
    return parsed.map((m) => ({
      ...(m as Omit<Message, 'timestamp'>),
      timestamp: new Date(m.timestamp as string),
      isThinking: false,
    }))
  } catch {
    return []
  }
}

function getOrCreateSessionId(): string {
  const stored = localStorage.getItem(STORAGE_KEY_SESSION)
  if (stored) return stored
  const id = uuidv4()
  localStorage.setItem(STORAGE_KEY_SESSION, id)
  return id
}

export function useChatManager(greetingText: string) {
  const { t } = useLanguage()
  const { user } = useAuth()
  const sessionIdRef = useRef<string>(getOrCreateSessionId())

  const [messages, setMessages] = useState<Message[]>(() => {
    const stored = loadMessages()
    return stored.length > 0 ? stored : [makeGreeting(greetingText)]
  })

  const [inputValue, setInputValue] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [showLoginRequired, setShowLoginRequired] = useState(false)

  // When language changes, retranslate the greeting if no conversation has started yet
  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].sender === 'bot') {
        return [{ ...prev[0], text: greetingText }]
      }
      return prev
    })
  }, [greetingText])

  // Persist messages to localStorage (skip thinking bubbles)
  useEffect(() => {
    const toStore = messages.filter((m) => !m.isThinking && !m.isStreaming)
    localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(toStore))
  }, [messages])

  const dismissLoginRequired = useCallback(() => setShowLoginRequired(false), [])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isThinking) return

    // Anonymous users can chat freely, but ticket queries require login.
    // The backend re-checks; this just gives instant feedback.
    if (!user && containsSknCode(text)) {
      setShowLoginRequired(true)
      return
    }

    const userMsg: Message = {
      id: uuidv4(),
      text: text.trim(),
      sender: 'user',
      timestamp: new Date(),
    }

    const thinkingId = uuidv4()
    const thinkingMsg: Message = {
      id: thinkingId,
      text: '',
      sender: 'bot',
      timestamp: new Date(),
      isThinking: true,
    }

    setMessages((prev) => [...prev, userMsg, thinkingMsg])
    setInputValue('')
    setIsThinking(true)

    try {
      if (MOCK_DELAY_MS > 0) {
        // Simulate streaming with a mock response
        const mockText =
          '[Mock] สวัสดีครับ นี่คือข้อความทดสอบจากระบบ Phonphai Chatbot ที่แสดงผลแบบ streaming ทีละคำ เพื่อให้ผู้ใช้เห็นข้อความปรากฏขึ้นอย่างต่อเนื่อง'
        const words = mockText.split(' ')
        const botMsgId = uuidv4()

        // Show thinking for a bit first
        await new Promise((r) => setTimeout(r, MOCK_DELAY_MS))

        // Replace thinking with empty streaming message
        setMessages((prev) =>
          prev.map((m) =>
            m.id === thinkingId
              ? { id: botMsgId, text: '', sender: 'bot' as const, timestamp: new Date(), isStreaming: true }
              : m,
          ),
        )

        // Stream words one by one
        for (let i = 0; i < words.length; i++) {
          await new Promise((r) => setTimeout(r, 60))
          const token = i === 0 ? words[i] : ' ' + words[i]
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId ? { ...m, text: m.text + token } : m,
            ),
          )
        }

        // Finalize
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId ? { ...m, isStreaming: false } : m,
          ),
        )
      } else {
        const botMsgId = uuidv4()
        let firstToken = true

        await sendMessageStream(
          sessionIdRef.current,
          text.trim(),
          // onToken
          (token) => {
            if (firstToken) {
              // Replace thinking bubble with streaming message
              firstToken = false
              const streamMsg: Message = {
                id: botMsgId,
                text: token,
                sender: 'bot',
                timestamp: new Date(),
                isStreaming: true,
              }
              setMessages((prev) =>
                prev.map((m) => (m.id === thinkingId ? streamMsg : m)),
              )
            } else {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botMsgId ? { ...m, text: m.text + token } : m,
                ),
              )
            }
          },
          // onDone
          (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botMsgId
                  ? { ...m, text: data.response, isStreaming: false }
                  : m,
              ),
            )
          },
          // onError
          (_errorMsg) => {
            const targetId = firstToken ? thinkingId : botMsgId
            setMessages((prev) =>
              prev.map((m) =>
                m.id === targetId
                  ? {
                      id: uuidv4(),
                      text: t('errorMessage'),
                      sender: 'bot' as const,
                      timestamp: new Date(),
                    }
                  : m,
              ),
            )
          },
        )
      }
    } catch {
      const errMsg: Message = {
        id: uuidv4(),
        text: t('errorMessage'),
        sender: 'bot',
        timestamp: new Date(),
      }
      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingId ? errMsg : m)),
      )
    } finally {
      setIsThinking(false)
    }
  }, [isThinking, user, t])

  const clearChat = useCallback((newGreetingText: string) => {
    const newId = uuidv4()
    sessionIdRef.current = newId
    localStorage.setItem(STORAGE_KEY_SESSION, newId)
    setMessages([makeGreeting(newGreetingText)])
    setInputValue('')
    setIsThinking(false)
  }, [])

  return {
    messages,
    inputValue,
    setInputValue,
    isThinking,
    sendMessage,
    clearChat,
    showLoginRequired,
    dismissLoginRequired,
  }
}

