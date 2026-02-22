import { Avatar, AvatarFallback } from './ui/avatar'
import { Bot, User } from 'lucide-react'
import { ThinkingIndicator } from './ThinkingIndicator'
import type { Message } from '../types'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.isThinking) return <ThinkingIndicator />

  const isBot = message.sender === 'bot'

  return (
    <div className={`flex gap-3 ${isBot ? '' : 'flex-row-reverse'}`}>
      <Avatar className={`shrink-0 ${isBot ? 'bg-[#D32F2F]' : 'bg-gray-600'}`}>
        <AvatarFallback className="text-white">
          {isBot ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
        </AvatarFallback>
      </Avatar>

      <div className={`flex flex-col ${isBot ? 'items-start' : 'items-end'} max-w-[75%]`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isBot
              ? 'bg-white border border-gray-200 text-gray-900'
              : 'bg-[#D32F2F] text-white'
          }`}
        >
          <p className="break-words">{message.text}</p>
        </div>
        <span className="text-xs text-gray-500 mt-1">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}
