import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Home, MessageSquare, Map, User, Trash2, Send, Menu, LogOut, LogIn } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Switch } from './ui/switch'
import { ScrollArea } from './ui/scroll-area'
import { Card } from './ui/card'
import { Sheet, SheetContent } from './ui/sheet'
import { Separator } from './ui/separator'
import { QuickReplyChips } from './QuickReplyChips'
import { ChatMessage } from './ChatMessage'
import { useLanguage } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'
import type { Message } from '../types'

interface DesktopViewProps {
  messages: Message[]
  inputValue: string
  setInputValue: (value: string) => void
  onSendMessage: (text: string) => void
  onQuickReply: (text: string) => void
  onClearChat: () => void
  isThinking: boolean
}

const navigationItems = [
  { icon: Home, label: 'Dashboard', active: false },
  { icon: MessageSquare, label: 'Chat', active: true },
  { icon: Map, label: 'Incident Map', active: false },
  { icon: User, label: 'Profile', active: false },
]

export function DesktopView({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  onQuickReply,
  onClearChat,
  isThinking,
}: DesktopViewProps) {
  const { language, toggleLanguage, t } = useLanguage()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
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

  const suggestionCards = [
    { id: '1', title: t('card_manual'), description: t('card_manual_desc') },
    { id: '2', title: t('card_relief'), description: t('card_relief_desc') },
    { id: '3', title: t('card_shelter'), description: t('card_shelter_desc') },
    { id: '4', title: t('card_report'), description: t('card_report_desc') },
  ]

  return (
    <div className="flex h-full bg-gray-50">
      {/* Sidebar Sheet */}
      <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <aside className="h-full bg-white flex flex-col">
            {/* Logo */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#D32F2F] rounded-full flex items-center justify-center">
                  <span className="text-white font-bold">P</span>
                </div>
                <div>
                  <h1 className="text-lg text-[#D32F2F]">Phonphai</h1>
                  <p className="text-xs text-gray-600">Disaster Management</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="p-4 space-y-1">
              {navigationItems.map((item) => (
                <Button
                  key={item.label}
                  variant={item.active ? 'default' : 'ghost'}
                  className={`w-full justify-start ${
                    item.active ? 'bg-[#D32F2F] hover:bg-red-700' : 'hover:bg-gray-100'
                  }`}
                  onClick={() => setIsSidebarOpen(false)}
                >
                  <item.icon className="w-4 h-4 mr-3" />
                  {item.label}
                </Button>
              ))}
            </nav>

            <Separator />

            {/* Language Toggle */}
            <div className="mt-auto p-4 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Language</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600">{t('languageLabel')}</span>
                  <Switch checked={language === 'english'} onCheckedChange={toggleLanguage} />
                </div>
              </div>
            </div>
          </aside>
        </SheetContent>
      </Sheet>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col items-center">
        <div className="w-full max-w-4xl h-full flex flex-col">
          {/* Chat Header */}
          <header className="bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsSidebarOpen(true)}
                  aria-label="Open menu"
                >
                  <Menu className="w-5 h-5" />
                </Button>
                <div>
                  <h2 className="text-xl text-gray-900">{t('assistantTitle')}</h2>
                  <p className="text-sm text-gray-600">{t('assistantSubtitle')}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={onClearChat}
                  className="text-[#D32F2F] border-[#D32F2F] hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  {t('clearChat')}
                </Button>
                {user ? (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-700">{user}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={logout}
                      aria-label="Logout"
                      className="text-gray-500 hover:text-red-600"
                    >
                      <LogOut className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => navigate('/login')}
                    className="text-gray-600 border-gray-300 hover:bg-gray-50"
                  >
                    <LogIn className="w-4 h-4 mr-2" />
                    เข้าสู่ระบบ
                  </Button>
                )}
              </div>
            </div>
          </header>

          {/* Chat Content */}
          <div className="flex-1 overflow-hidden bg-white">
            <ScrollArea className="h-full">
              <div ref={scrollRef} className="p-6">
                <div className="space-y-4">
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))}
                </div>

                {messages.length === 1 && (
                  <div className="mt-6 space-y-3">
                    <p className="text-sm text-gray-500">{t('selectTopic')}</p>
                    <div className="grid grid-cols-2 gap-4 w-full max-w-2xl">
                      {suggestionCards.map((card) => (
                        <Card
                          key={card.id}
                          className="p-6 cursor-pointer hover:shadow-md transition-shadow border-gray-200 hover:border-[#D32F2F]"
                          onClick={() => onQuickReply(card.title)}
                        >
                          <h3 className="text-gray-900 mb-2">{card.title}</h3>
                          <p className="text-sm text-gray-600">{card.description}</p>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Quick Reply Chips */}
          <div className="px-6 py-3 bg-white border-t border-gray-200">
            <QuickReplyChips onSelect={onQuickReply} disabled={isThinking} />
          </div>

          {/* Input Area */}
          <div className="bg-white border-t border-gray-200 px-6 py-4">
            <form onSubmit={handleSubmit} className="flex items-center gap-3">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={t('placeholder')}
                className="flex-1"
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
      </main>
    </div>
  )
}
