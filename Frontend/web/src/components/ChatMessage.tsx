import { Avatar, AvatarFallback } from './ui/avatar'
import { Bot, User } from 'lucide-react'
import { ThinkingIndicator } from './ThinkingIndicator'
import type { Message } from '../types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

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
          {isBot ? (
            <div className="break-words text-sm leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  strong: ({ children }) => (
                    <strong className="font-semibold">{children}</strong>
                  ),
                  em: ({ children }) => <em className="italic">{children}</em>,
                  ul: ({ children }) => (
                    <ul className="list-disc pl-5 mb-2 last:mb-0 space-y-1">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal pl-5 mb-2 last:mb-0 space-y-1">{children}</ol>
                  ),
                  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                  h1: ({ children }) => (
                    <h1 className="text-base font-bold mb-2 mt-1">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-base font-semibold mb-2 mt-1">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-sm font-semibold mb-1 mt-1">{children}</h3>
                  ),
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#D32F2F] underline hover:no-underline"
                    >
                      {children}
                    </a>
                  ),
                  code: ({ className, children }) => {
                    const isInline = !className
                    return isInline ? (
                      <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[0.85em] font-mono">
                        {children}
                      </code>
                    ) : (
                      <code className={className}>{children}</code>
                    )
                  },
                  pre: ({ children }) => (
                    <pre className="bg-gray-100 rounded-md p-3 my-2 overflow-x-auto text-xs font-mono">
                      {children}
                    </pre>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-gray-300 pl-3 my-2 italic text-gray-700">
                      {children}
                    </blockquote>
                  ),
                  hr: () => <hr className="my-3 border-gray-200" />,
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-2">
                      <table className="min-w-full border-collapse text-sm">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-gray-300 px-2 py-1 bg-gray-50 font-semibold text-left">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-gray-300 px-2 py-1">{children}</td>
                  ),
                }}
              >
                {message.text}
              </ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-block w-[2px] h-[1em] ml-0.5 bg-gray-900 animate-pulse align-text-bottom" />
              )}
            </div>
          ) : (
            <p className="break-words">{message.text}</p>
          )}
        </div>
        <span className="text-xs text-gray-500 mt-1">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}
