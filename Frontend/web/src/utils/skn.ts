// Mirror of the backend pattern in services/api-gateway/routers/chat.py.
// The backend is the real gate; this is just for UX so users see the modal
// before the request goes out.
<<<<<<< Updated upstream
export const SKN_PATTERN = /\bSKN[-\s]?\d{4}[-\s]?\d{4}\b/i

export function containsSknCode(text: string): boolean {
  return SKN_PATTERN.test(text)
=======
export const TICKET_CODE_PATTERN = /\b[A-Z]{3}[-\s]?\d{4}[-\s]?\d{4}\b/i
export const TICKET_SUFFIX_PATTERN = /^\s*\d{4}\s*$/
export const TICKET_YEAR_SUFFIX_PATTERN = /^\s*25\d{2}[-\s/]?\d{4}\s*$/
export const TICKET_SUFFIX_WITH_CONTEXT_PATTERN =
  /(?:ticket|request|คำร้อง|หมายเลข).*\b\d{4}\b|\b\d{4}\b.*(?:ticket|request|คำร้อง|หมายเลข)/i

export function containsSknCode(text: string): boolean {
  return (
    TICKET_CODE_PATTERN.test(text) ||
    TICKET_SUFFIX_PATTERN.test(text) ||
    TICKET_YEAR_SUFFIX_PATTERN.test(text) ||
    TICKET_SUFFIX_WITH_CONTEXT_PATTERN.test(text)
  )
>>>>>>> Stashed changes
}
