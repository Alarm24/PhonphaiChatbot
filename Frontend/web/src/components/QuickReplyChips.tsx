import { Badge } from './ui/badge'
import { useLanguage, type TranslationKey } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

interface QuickReplyChipsProps {
  onSelect: (text: string) => void
  disabled?: boolean
}

export function QuickReplyChips({ onSelect, disabled }: QuickReplyChipsProps) {
  const { t } = useLanguage()
  const { user } = useAuth()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)
  const isLoggedInUserOrAdmin = user?.role === 'user' || user?.role === 'admin'

  const quickReplyKeys: TranslationKey[] = [
    ...(isLoggedInUserOrAdmin
      ? (['quickReply_remedyAllTickets', 'quickReply_remedyYear2569'] as const)
      : (['quickReply_manualDetails', 'quickReply_manualAgencyOptions'] as const)),
    'quickReply_disasterFloodBag',
    'quickReply_disasterEarthquakeReturn',
    'quickReply_disasterBirdFlu',
    'quickReply_disasterFire',
    'quickReply_disasterFlashFlood',
  ]

  const updateScrollButtons = () => {
    const scroller = scrollRef.current
    if (!scroller) return

    setCanScrollLeft(scroller.scrollLeft > 0)
    setCanScrollRight(scroller.scrollLeft + scroller.clientWidth < scroller.scrollWidth - 1)
  }

  const scrollChips = (direction: 'left' | 'right') => {
    scrollRef.current?.scrollBy({
      left: direction === 'left' ? -280 : 280,
      behavior: 'smooth',
    })
  }

  useEffect(() => {
    updateScrollButtons()
    window.addEventListener('resize', updateScrollButtons)
    return () => window.removeEventListener('resize', updateScrollButtons)
  }, [quickReplyKeys.length])

  return (
    <div className="flex min-w-0 items-center gap-2">
      <button
        type="button"
        aria-label="Scroll quick replies left"
        className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-200 bg-white text-[#D32F2F] shadow-sm transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-30 sm:flex"
        disabled={disabled || !canScrollLeft}
        onClick={() => scrollChips('left')}
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div
        ref={scrollRef}
        className="flex min-w-0 flex-1 gap-2 overflow-x-auto pb-1 scrollbar-hide"
        onScroll={updateScrollButtons}
      >
        {quickReplyKeys.map((key) => {
          const reply = t(key)
          return (
            <Badge
              key={key}
              variant="outline"
              className={`cursor-pointer whitespace-nowrap px-4 py-2 border-[#D32F2F] text-[#D32F2F] hover:bg-[#D32F2F] hover:text-white transition-colors ${
                disabled ? 'opacity-50 pointer-events-none' : ''
              }`}
              onClick={() => !disabled && onSelect(reply)}
            >
              {reply}
            </Badge>
          )
        })}
      </div>

      <button
        type="button"
        aria-label="Scroll quick replies right"
        className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-200 bg-white text-[#D32F2F] shadow-sm transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-30 sm:flex"
        disabled={disabled || !canScrollRight}
        onClick={() => scrollChips('right')}
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  )
}
