import { Routes, Route } from 'react-router-dom'
import { useMediaQuery } from './hooks/useMediaQuery'
import { useChatManager } from './hooks/useChatManager'
import { useLanguage } from './contexts/LanguageContext'
import { MobileView } from './components/MobileView'
import { DesktopView } from './components/DesktopView'
import { LoginRequiredModal } from './components/LoginRequiredModal'
import { LoginPage } from './pages/LoginPage'

function ChatPage() {
  const isMobile = useMediaQuery('(max-width: 768px)')
  const { t } = useLanguage()
  const {
    messages,
    inputValue,
    setInputValue,
    isThinking,
    sendMessage,
    clearChat,
    showLoginRequired,
    dismissLoginRequired,
  } = useChatManager(t('greeting'))

  const sharedProps = {
    messages,
    inputValue,
    setInputValue,
    onSendMessage: sendMessage,
    onQuickReply: sendMessage,
    onClearChat: () => clearChat(t('greeting')),
    isThinking,
  }

  return (
    <div className="h-screen overflow-hidden">
      {isMobile ? <MobileView {...sharedProps} /> : <DesktopView {...sharedProps} />}
      <LoginRequiredModal open={showLoginRequired} onClose={dismissLoginRequired} />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="/login" element={<LoginPage />} />
    </Routes>
  )
}
