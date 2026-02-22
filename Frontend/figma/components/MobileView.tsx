import { useRef, useEffect } from 'react';
import { Phone, Mic, Send } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { ScrollArea } from './ui/scroll-area';
import { QuickReplyChips } from './QuickReplyChips';
import { ChatMessage } from './ChatMessage';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface MobileViewProps {
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  onSendMessage: (text: string) => void;
  onQuickReply: (text: string) => void;
  language: 'thai' | 'english';
  onToggleLanguage: () => void;
}

export function MobileView({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  onQuickReply,
  language,
  onToggleLanguage,
}: MobileViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

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
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-[#D32F2F] text-white px-4 py-3 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
              <span className="text-[#D32F2F]">P</span>
            </div>
            <h1 className="text-lg">Phonphai</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs">{language === 'thai' ? 'TH' : 'EN'}</span>
              <Switch checked={language === 'english'} onCheckedChange={onToggleLanguage} />
            </div>
            <Button
              size="icon"
              variant="ghost"
              className="text-white hover:bg-red-600"
              aria-label="Call Staff"
            >
              <Phone className="w-5 h-5" />
            </Button>
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
        <QuickReplyChips onSelect={onQuickReply} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your question..."
            className="flex-1 text-base"
          />
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="shrink-0 text-gray-600"
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
  );
}
