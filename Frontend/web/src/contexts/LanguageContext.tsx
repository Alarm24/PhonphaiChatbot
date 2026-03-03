import { createContext, useContext, useState, type ReactNode } from 'react'

export type Language = 'thai' | 'english'

export type TranslationKey =
  | 'greeting'
  | 'placeholder'
  | 'clearChat'
  | 'thinking'
  | 'quickReply_flood'
  | 'quickReply_forgotPassword'
  | 'quickReply_shelter'
  | 'quickReply_contact'
  | 'quickReply_hotline'
  | 'quickReply_safety'
  | 'languageLabel'
  | 'assistantTitle'
  | 'assistantSubtitle'
  | 'howCanIHelp'
  | 'selectTopic'
  | 'errorMessage'
  | 'card_manual'
  | 'card_manual_desc'
  | 'card_relief'
  | 'card_relief_desc'
  | 'card_shelter'
  | 'card_shelter_desc'
  | 'card_report'
  | 'card_report_desc'

const translations: Record<Language, Record<TranslationKey, string>> = {
  english: {
    greeting:
      "Welcome to Phonphai! I'm here to help you with disaster management information. How can I assist you today?",
    placeholder: 'Type your question...',
    clearChat: 'Clear Chat',
    thinking: 'Thinking...',
    quickReply_flood: 'How to report a flood?',
    quickReply_forgotPassword: 'Forgot Password',
    quickReply_shelter: 'Where is the nearest shelter?',
    quickReply_contact: 'Contact Official',
    quickReply_hotline: 'Emergency Hotline',
    quickReply_safety: 'Safety Guidelines',
    languageLabel: 'EN',
    assistantTitle: 'Phonphai Assistant',
    assistantSubtitle: 'AI-powered disaster management support',
    howCanIHelp: 'How can I help you today?',
    selectTopic: 'Select a topic below or type your question',
    errorMessage: 'Sorry, I encountered an error. Please try again.',
    card_manual: 'System Manual',
    card_manual_desc: 'Learn how to use Phonphai effectively',
    card_relief: 'Request Relief Kit',
    card_relief_desc: 'Get emergency supplies delivered',
    card_shelter: 'Emergency Call Numbers',
    card_shelter_desc: 'View disaster emergency contact numbers',
    card_report: 'Report Incident',
    card_report_desc: 'Submit a disaster incident report',
  },
  thai: {
    greeting:
      'สวัสดีครับ! ผมคือผู้ช่วยพ้นภัย ผู้ช่วย AI สำหรับการใช้แอปพลิเคชันง่ายขึ้นและตอบคำถามภัยพิบบัติเบื้องต้น วันนี้ผมช่วยคุณได้อย่างไรบ้างครับ?',
    placeholder: 'พิมพ์คำถามของคุณ...',
    clearChat: 'ล้างการสนทนา',
    thinking: 'กำลังคิด...',
    quickReply_flood: 'วิธีรายงานน้ำท่วม?',
    quickReply_forgotPassword: 'ลืมรหัสผ่าน',
    quickReply_shelter: 'ศูนย์พักพิงที่ใกล้ที่สุดอยู่ที่ไหน?',
    quickReply_contact: 'ติดต่อเจ้าหน้าที่',
    quickReply_hotline: 'สายด่วนฉุกเฉิน',
    quickReply_safety: 'แนวทางความปลอดภัย',
    languageLabel: 'TH',
    assistantTitle: 'ผู้ช่วยพ้นภัย',
    assistantSubtitle: 'แชทบอทช่วยให้การใช้แอปพลิเคชันง่ายขึ้นและตอบคำถามภัยพิบบัติเบื้องต้น',
    howCanIHelp: 'วันนี้ผมช่วยคุณได้อย่างไรบ้าง?',
    selectTopic: 'เลือกหัวข้อด้านล่างหรือพิมพ์คำถาม',
    errorMessage: 'ขออภัย เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง',
    card_manual: 'คู่มือระบบ',
    card_manual_desc: 'เรียนรู้วิธีใช้งานแอปพลิเคชันพ้นภัย',
    card_relief: 'ขอชุดบรรเทาทุกข์',
    card_relief_desc: 'รับอุปกรณ์ฉุกเฉินส่งถึงที่',
    card_shelter: 'สายด่วนภัยพิบัติที่เกี่ยวข้อง',
    card_shelter_desc: 'ดูหมายเลขติดต่อฉุกเฉินภัยพิบัติ',
    card_report: 'รายงานเหตุการณ์',
    card_report_desc: 'ส่งรายงานเหตุภัยพิบัติ',
  },
}

interface LanguageContextValue {
  language: Language
  toggleLanguage: () => void
  t: (key: TranslationKey) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>('thai')

  const toggleLanguage = () =>
    setLanguage((prev) => (prev === 'thai' ? 'english' : 'thai'))

  const t = (key: TranslationKey): string => translations[language][key]

  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside LanguageProvider')
  return ctx
}
