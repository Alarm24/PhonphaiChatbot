import { useState, useEffect } from 'react'
import { Avatar, AvatarFallback } from './ui/avatar'
import { Bot } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'

const PHASE_THRESHOLDS = [0, 5, 12, 20] as const

export function ThinkingIndicator() {
  const { t } = useLanguage()
  const [elapsedSec, setElapsedSec] = useState(0)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => setElapsedSec((s) => s + 1), 1000)
    return () => clearInterval(interval)
  }, [])

  // Compute current phase (0–3)
  const phase = PHASE_THRESHOLDS.filter((threshold) => elapsedSec >= threshold).length - 1

  const phaseMessages = [
    t('thinking'),
    t('thinking_searching'),
    t('thinking_almost'),
    t('thinking_wait'),
  ]

  // Fade out → update text → fade in on phase change
  useEffect(() => {
    setVisible(false)
    const timer = setTimeout(() => setVisible(true), 200)
    return () => clearTimeout(timer)
  }, [phase])

  return (
    <div className="flex gap-3">
      <Avatar className="shrink-0 bg-[#D32F2F]">
        <AvatarFallback className="text-white">
          <Bot className="w-5 h-5" />
        </AvatarFallback>
      </Avatar>
      <div className="flex flex-col items-start max-w-[75%]">
        <div className="rounded-2xl px-4 py-3 bg-white border border-gray-200 text-gray-900">
          <span
            className="block text-sm text-gray-500 mb-2 transition-opacity duration-200"
            style={{ opacity: visible ? 1 : 0 }}
          >
            {phaseMessages[phase]}
          </span>
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
