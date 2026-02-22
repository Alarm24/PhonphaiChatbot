import { useState } from 'react';
import { MobileView } from './components/MobileView';
import { DesktopView } from './components/DesktopView';
import { useMediaQuery } from './hooks/useMediaQuery';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

export default function App() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Welcome to Phonphai! I\'m here to help you with disaster management information. How can I assist you today?',
      sender: 'bot',
      timestamp: new Date(),
    },
  ]);
  const [language, setLanguage] = useState<'thai' | 'english'>('english');
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');

    // Simulate bot response
    setTimeout(() => {
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Thank you for your message. I\'m processing your request. In a real application, I would provide specific disaster management information based on your query.',
        sender: 'bot',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }, 1000);
  };

  const handleQuickReply = (text: string) => {
    handleSendMessage(text);
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: '1',
        text: 'Welcome to Phonphai! I\'m here to help you with disaster management information. How can I assist you today?',
        sender: 'bot',
        timestamp: new Date(),
      },
    ]);
  };

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === 'thai' ? 'english' : 'thai'));
  };

  return (
    <div className="h-screen overflow-hidden">
      {isMobile ? (
        <MobileView
          messages={messages}
          inputValue={inputValue}
          setInputValue={setInputValue}
          onSendMessage={handleSendMessage}
          onQuickReply={handleQuickReply}
          language={language}
          onToggleLanguage={toggleLanguage}
        />
      ) : (
        <DesktopView
          messages={messages}
          inputValue={inputValue}
          setInputValue={setInputValue}
          onSendMessage={handleSendMessage}
          onQuickReply={handleQuickReply}
          onClearChat={handleClearChat}
          language={language}
          onToggleLanguage={toggleLanguage}
        />
      )}
    </div>
  );
}
