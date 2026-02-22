import { Avatar, AvatarFallback } from './ui/avatar'
import { Bot } from 'lucide-react'

export function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <Avatar className="shrink-0 bg-[#D32F2F]">
        <AvatarFallback className="text-white">
          <Bot className="w-5 h-5" />
        </AvatarFallback>
      </Avatar>
      <div className="flex flex-col items-start max-w-[75%]">
        <div className="rounded-2xl px-4 py-3 bg-white border border-gray-200 text-gray-900">
          <div className="flex items-center gap-1">
            <span
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: '0ms' }}
            />
            <span
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: '150ms' }}
            />
            <span
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: '300ms' }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
