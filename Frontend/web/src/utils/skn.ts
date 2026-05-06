// Mirror of the backend pattern in services/api-gateway/routers/chat.py.
// The backend is the real gate; this is just for UX so users see the modal
// before the request goes out.
export const TICKET_CODE_PATTERN = /\b[A-Z]{3}[-\s]?\d{4}[-\s]?\d{4}\b/i

export function containsSknCode(text: string): boolean {
  return TICKET_CODE_PATTERN.test(text)
}
