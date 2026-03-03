import { useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Phone, Send, Trash2, LogOut, LogIn } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Switch } from './ui/switch'
import { ScrollArea } from './ui/scroll-area'
import { QuickReplyChips } from './QuickReplyChips'
import { ChatMessage } from './ChatMessage'
import { useLanguage } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'
import type { Message } from '../types'

interface MobileViewProps {
  messages: Message[]
  inputValue: string
  setInputValue: (value: string) => void
  onSendMessage: (text: string) => void
  onQuickReply: (text: string) => void
  onClearChat: () => void
  isThinking: boolean
}

export function MobileView({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  onQuickReply,
  onClearChat,
  isThinking,
}: MobileViewProps) {
  const { language, toggleLanguage, t } = useLanguage()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isThinking) onSendMessage(inputValue)
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-[#D32F2F] text-white px-4 py-3 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
              <span className="text-[#D32F2F] font-bold text-sm">P</span>
            </div>
            <h1 className="text-lg">Phonphai</h1>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <span className="text-xs font-medium">{t('languageLabel')}</span>
              <Switch
                checked={language === 'english'}
                onCheckedChange={toggleLanguage}
                className="data-[state=checked]:bg-white/30 data-[state=unchecked]:bg-white/20"
              />
            </div>
            <Button
              size="icon"
              variant="ghost"
              onClick={onClearChat}
              className="text-white hover:bg-red-600"
              aria-label="Clear chat"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="text-white hover:bg-red-600"
              aria-label="Call Staff"
            >
              <Phone className="w-5 h-5" />
            </Button>
            {user ? (
              <Button
                size="icon"
                variant="ghost"
                onClick={logout}
                className="text-white hover:bg-red-600"
                aria-label="Logout"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                size="icon"
                variant="ghost"
                onClick={() => navigate('/login')}
                className="text-white hover:bg-red-600"
                aria-label="Login"
              >
                <LogIn className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div ref={scrollRef} className="p-4 space-y-4">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Quick Reply Chips */}
      <div className="px-4 py-2 bg-white border-t border-gray-200">
        <QuickReplyChips onSelect={onQuickReply} disabled={isThinking} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={t('placeholder')}
            className="flex-1 text-base"
            disabled={isThinking}
          />
          <Button
            type="submit"
            size="icon"
            className="shrink-0 bg-[#D32F2F] hover:bg-red-700"
            aria-label="Send message"
            disabled={isThinking || !inputValue.trim()}
          >
            <Send className="w-5 h-5" />
          </Button>
        </form>
      </div>
    </div>
  )
}
