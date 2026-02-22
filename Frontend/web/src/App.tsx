import { useMediaQuery } from './hooks/useMediaQuery'
import { useChatManager } from './hooks/useChatManager'
import { useLanguage } from './contexts/LanguageContext'
import { MobileView } from './components/MobileView'
import { DesktopView } from './components/DesktopView'

export default function App() {
  const isMobile = useMediaQuery('(max-width: 768px)')
  const { t } = useLanguage()
  const { messages, inputValue, setInputValue, isThinking, sendMessage, clearChat } =
    useChatManager(t('greeting'))

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
    </div>
  )
}
