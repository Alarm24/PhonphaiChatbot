import { useState, useEffect, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { Message } from '../types'
import { sendMessage as apiSendMessage } from '../services/api'
import { useLanguage } from '../contexts/LanguageContext'

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
  const sessionIdRef = useRef<string>(getOrCreateSessionId())

  const [messages, setMessages] = useState<Message[]>(() => {
    const stored = loadMessages()
    return stored.length > 0 ? stored : [makeGreeting(greetingText)]
  })

  const [inputValue, setInputValue] = useState('')
  const [isThinking, setIsThinking] = useState(false)

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
    const toStore = messages.filter((m) => !m.isThinking)
    localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(toStore))
  }, [messages])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isThinking) return

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
      let data
      if (MOCK_DELAY_MS > 0) {
        await new Promise((r) => setTimeout(r, MOCK_DELAY_MS))
        data = {
          session_id: sessionIdRef.current,
          response: '[Mock] This is a test response from Phonphai.',
          sources: [],
        }
      } else {
        data = await apiSendMessage(sessionIdRef.current, text.trim())
      }
      const botMsg: Message = {
        id: uuidv4(),
        text: data.response,
        sender: 'bot',
        timestamp: new Date(),
      }
      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingId ? botMsg : m)),
      )
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
  }, [isThinking])

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
  }
}
