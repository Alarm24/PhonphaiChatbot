import { useState, useRef, useEffect } from 'react';
import { Home, MessageSquare, Map, User, Trash2, Phone, Mic, Send, Menu } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { ScrollArea } from './ui/scroll-area';
import { Card } from './ui/card';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import { Separator } from './ui/separator';
import { QuickReplyChips } from './QuickReplyChips';
import { ChatMessage } from './ChatMessage';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface DesktopViewProps {
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  onSendMessage: (text: string) => void;
  onQuickReply: (text: string) => void;
  onClearChat: () => void;
  language: 'thai' | 'english';
  onToggleLanguage: () => void;
}

const navigationItems = [
  { icon: Home, label: 'Dashboard', active: false },
  { icon: MessageSquare, label: 'Chat', active: true },
  { icon: Map, label: 'Incident Map', active: false },
  { icon: User, label: 'Profile', active: false },
];

const suggestionCards = [
  { id: '1', title: 'System Manual', description: 'Learn how to use Phonphai effectively' },
  { id: '2', title: 'Request Relief Kit', description: 'Get emergency supplies delivered' },
  { id: '3', title: 'Find Nearest Shelter', description: 'Locate safe evacuation points' },
  { id: '4', title: 'Report Incident', description: 'Submit a disaster incident report' },
];

export function DesktopView({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  onQuickReply,
  onClearChat,
  language,
  onToggleLanguage,
}: DesktopViewProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const showWelcomeScreen = messages.length === 1;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSendMessage(inputValue);
  };

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
                  <span className="text-white">P</span>
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
                  <span className="text-xs text-gray-600">{language === 'thai' ? 'Thai' : 'English'}</span>
                  <Switch checked={language === 'english'} onCheckedChange={onToggleLanguage} />
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
                  <h2 className="text-xl text-gray-900">Phonphai Assistant</h2>
                  <p className="text-sm text-gray-600">AI-powered disaster management support</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  className="text-[#D32F2F] border-[#D32F2F] hover:bg-red-50"
                  aria-label="Call Staff"
                >
                  <Phone className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  onClick={onClearChat}
                  className="text-[#D32F2F] border-[#D32F2F] hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear Chat
                </Button>
              </div>
            </div>
          </header>

          {/* Chat Content */}
          <div className="flex-1 overflow-hidden bg-white">
            <ScrollArea className="h-full">
              <div ref={scrollRef} className="p-6">
                {showWelcomeScreen ? (
                  <div className="flex flex-col items-center justify-center min-h-[500px] space-y-8">
                    <div className="text-center space-y-3">
                      <h2 className="text-3xl text-gray-900">How can I help you today?</h2>
                      <p className="text-gray-600">Select a topic below or type your question</p>
                    </div>

                    {/* FAQ Grid */}
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
                ) : (
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Quick Reply Chips */}
          <div className="px-6 py-3 bg-white border-t border-gray-200">
            <QuickReplyChips onSelect={onQuickReply} />
          </div>

          {/* Input Area */}
          <div className="bg-white border-t border-gray-200 px-6 py-4">
            <form onSubmit={handleSubmit} className="flex items-center gap-3">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your question..."
                className="flex-1"
              />
              <Button
                type="button"
                size="icon"
                variant="outline"
                className="shrink-0"
                aria-label="Voice input"
              >
                <Mic className="w-5 h-5" />
              </Button>
              <Button
                type="submit"
                size="icon"
                className="shrink-0 bg-[#D32F2F] hover:bg-red-700"
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </Button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
