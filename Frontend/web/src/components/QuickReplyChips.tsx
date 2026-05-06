import { Badge } from './ui/badge'
import { useLanguage } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'

interface QuickReplyChipsProps {
  onSelect: (text: string) => void
  disabled?: boolean
}

export function QuickReplyChips({ onSelect, disabled }: QuickReplyChipsProps) {
  const { t } = useLanguage()
  const { user } = useAuth()

  const quickReplies = [
    t('quickReply_flood'),
    user ? 'ขอรายการคำร้องทั้งหมด' : t('quickReply_forgotPassword'),
    t('quickReply_contact'),
    t('quickReply_hotline'),
  ]

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
      {quickReplies.map((reply) => (
        <Badge
          key={reply}
          variant="outline"
          className={`cursor-pointer whitespace-nowrap px-4 py-2 border-[#D32F2F] text-[#D32F2F] hover:bg-[#D32F2F] hover:text-white transition-colors ${
            disabled ? 'opacity-50 pointer-events-none' : ''
          }`}
          onClick={() => !disabled && onSelect(reply)}
        >
          {reply}
        </Badge>
      ))}
    </div>
  )
}
