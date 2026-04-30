// Mirror of the backend pattern in services/api-gateway/routers/chat.py.
// The backend is the real gate; this is just for UX so users see the modal
// before the request goes out.
export const SKN_PATTERN = /\bSKN[-\s]?\d{4}[-\s]?\d{4}\b/i

export function containsSknCode(text: string): boolean {
  return SKN_PATTERN.test(text)
}
