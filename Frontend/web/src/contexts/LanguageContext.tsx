import { createContext, useContext, useState, type ReactNode } from "react";

export type Language = "thai" | "english";

export type TranslationKey =
  | "greeting"
  | "placeholder"
  | "clearChat"
  | "thinking"
  | "thinking_searching"
  | "thinking_almost"
  | "thinking_wait"
  | "quickReply_flood"
  | "quickReply_forgotPassword"
  | "quickReply_contact"
  | "quickReply_hotline"
  | "quickReply_manualDetails"
  | "quickReply_manualAgencyOptions"
  | "quickReply_disasterFloodBag"
  | "quickReply_disasterEarthquakeReturn"
  | "quickReply_disasterBirdFlu"
  | "quickReply_disasterFire"
  | "quickReply_disasterFlashFlood"
  | "quickReply_remedyAllTickets"
  | "quickReply_remedyYear2569"
  | "languageLabel"
  | "assistantTitle"
  | "assistantSubtitle"
  | "howCanIHelp"
  | "selectTopic"
  | "errorMessage"
  | "card_manual"
  | "card_manual_desc"
  | "card_relief"
  | "card_relief_desc"
  | "card_shelter"
  | "card_shelter_desc"
  | "card_report"
  | "card_report_desc";

const translations: Record<Language, Record<TranslationKey, string>> = {
  english: {
    greeting:
      "Welcome to Phonphai! I'm here to help you with disaster management information. How can I assist you today?",
    placeholder: "Type your question...",
    clearChat: "Clear Chat",
    thinking: "Thinking...",
    thinking_searching: "Searching for information...",
    thinking_almost: "Almost there...",
    thinking_wait: "Just a moment more...",
    quickReply_flood: "How to report a flood?",
    quickReply_forgotPassword: "Forgot Password",
    quickReply_contact: "Contact Official",
    quickReply_hotline: "Emergency Hotline",
    quickReply_manualDetails: "How do I view incident report details?",
    quickReply_manualAgencyOptions: "What options are available when selecting the helping agency?",
    quickReply_disasterFloodBag:
      "Floodwater is about to enter my house. What should I pack in an emergency flood bag?",
    quickReply_disasterEarthquakeReturn:
      "The earthquake has stopped. Should I go back into the building to get my wallet?",
    quickReply_disasterBirdFlu: "How should poultry farm workers protect themselves from bird flu?",
    quickReply_disasterFire: "What should I do during a fire?",
    quickReply_disasterFlashFlood: "Flash flood water is coming very fast. What should I do?",
    quickReply_remedyAllTickets: "Show all request numbers",
    quickReply_remedyYear2569: "Requests from year 2569",
    languageLabel: "EN",
    assistantTitle: "Phonphai Assistant",
    assistantSubtitle: "AI-powered application and disaster support",
    howCanIHelp: "How can I help you today?",
    selectTopic: "Select a topic below or type your question",
    errorMessage: "Sorry, I encountered an error. Please try again.",
    card_manual: "System Manual",
    card_manual_desc: "Learn how to use Phonphai effectively",
    card_relief: "Request Relief Kit",
    card_relief_desc: "Get emergency supplies delivered",
    card_shelter: "Emergency Call Numbers",
    card_shelter_desc: "View disaster emergency contact numbers",
    card_report: "Report Incident",
    card_report_desc: "Submit a disaster incident report",
  },
  thai: {
    greeting:
      "สวัสดีค่ะ! ฉันคือผู้ช่วยพ้นภัย ผู้ช่วย AI สำหรับการใช้แอปพลิเคชันง่ายขึ้นและตอบคำถามภัยพิบัติเบื้องต้น วันนี้ฉันช่วยคุณได้อย่างไรบ้างคะ?",
    placeholder: "พิมพ์คำถามของคุณ...",
    clearChat: "ล้างการสนทนา",
    thinking: "กำลังคิด...",
    thinking_searching: "กำลังค้นหาข้อมูล...",
    thinking_almost: "เกือบได้แล้ว...",
    thinking_wait: "รอสักครู่นะครับ...",
    quickReply_flood: "วิธีรายงานน้ำท่วม?",
    quickReply_forgotPassword: "ลืมรหัสผ่าน",
    quickReply_contact: "ติดต่อเจ้าหน้าที่",
    quickReply_hotline: "สายด่วนฉุกเฉิน",
    quickReply_manualDetails: "วิธีดูรายละเอียดแจ้งภัย?",
    quickReply_manualAgencyOptions: "การเลือกหน่วยงานที่ช่วยเหลือมีตัวเลือกอะไรบ้าง?",
    quickReply_disasterFloodBag: "น้ำกำลังจะเข้าบ้าน ควรเก็บอะไรลงถุงยังชีพหนีน้ำบ้าง?",
    quickReply_disasterEarthquakeReturn:
      "แผ่นดินไหวสงบแล้ว รีบกลับเข้าตึกไปหยิบกระเป๋าตังค์ดีไหม?",
    quickReply_disasterBirdFlu: "คนงานฟาร์มเป็ดไก่ ต้องป้องกันตัวจากหวัดนกยังไง?",
    quickReply_disasterFire: "ไฟไหม้ต้องทำยังไงบ้าง",
    quickReply_disasterFlashFlood: "น้ำมาเร็วมากทำยังไงดี",
    quickReply_remedyAllTickets: "หมายเลขคำร้องทั้งหมด",
    quickReply_remedyYear2569: "คำร้องของปี 2569",
    languageLabel: "TH",
    assistantTitle: "ผู้ช่วยพ้นภัย",
    assistantSubtitle:
      "แชทบอทช่วยให้การใช้แอปพลิเคชันง่ายขึ้นและตอบคำถามภัยพิบัติเบื้องต้น",
    howCanIHelp: "วันนี้ผมช่วยคุณได้อย่างไรบ้าง?",
    selectTopic: "เลือกหัวข้อด้านล่างหรือพิมพ์คำถาม",
    errorMessage: "ขออภัยครับเกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้งในภายหลังครับ",
    card_manual: "คู่มือระบบ",
    card_manual_desc: "เรียนรู้วิธีใช้งานแอปพลิเคชันพ้นภัย",
    card_relief: "ขอชุดบรรเทาทุกข์",
    card_relief_desc: "รับอุปกรณ์ฉุกเฉินส่งถึงที่",
    card_shelter: "สายด่วนภัยพิบัติที่เกี่ยวข้อง",
    card_shelter_desc: "ดูหมายเลขติดต่อฉุกเฉินภัยพิบัติ",
    card_report: "รายงานเหตุการณ์",
    card_report_desc: "ส่งรายงานเหตุภัยพิบัติ",
  },
};

interface LanguageContextValue {
  language: Language;
  toggleLanguage: () => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>("thai");

  const toggleLanguage = () =>
    setLanguage((prev) => (prev === "thai" ? "english" : "thai"));

  const t = (key: TranslationKey): string => translations[language][key];

  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside LanguageProvider");
  return ctx;
}
