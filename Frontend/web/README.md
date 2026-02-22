# Phonphai Chatbot — Frontend

Responsive React SPA for the Phonphai disaster management chatbot.
Built with **Vite + React + TypeScript + Tailwind CSS v4**.

---

## Prerequisites

- Node.js 22 LTS — `nvm install 22 && nvm use 22` (v20.11.x is too old for Vite 7)
- The backend running at `http://localhost:8080` (see `Backend/README.md`)

---

## Getting Started (Local Dev)

### 1. Install dependencies

```bash
cd Frontend/web
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

The default `.env` already points to the local backend:
```
VITE_API_URL=http://localhost:8080
```

Change this if your backend runs on a different host or port.

### 3. Start the dev server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Other Commands

```bash
npm run build      # Type-check + production build → dist/
npm run preview    # Serve the production build locally
npm run lint       # ESLint
```

---

## Run with Docker

```bash
# From Frontend/web/
docker compose up --build
```

App is served at [http://localhost:3000](http://localhost:3000).

To point at a different backend at build time:

```bash
VITE_API_URL=http://your-backend:8080 docker compose up --build
```

> **Note:** `VITE_API_URL` is baked into the static bundle at build time (not a runtime env var). Always rebuild the Docker image when changing it.

---

## Project Structure

```
src/
├── App.tsx                        # Root — picks MobileView or DesktopView at 768px
├── main.tsx                       # Entry point — wraps App in LanguageProvider
├── globals.css                    # Tailwind v4 theme + CSS variables
├── types.ts                       # Shared Message & ChatApiResponse interfaces
├── contexts/
│   └── LanguageContext.tsx        # TH/EN toggle, t(key) translation function
├── hooks/
│   ├── useChatManager.ts          # All chat state, localStorage persistence, API calls
│   └── useMediaQuery.ts           # Responsive breakpoint detection
├── services/
│   └── api.ts                     # POST /api/v1/chat/ fetch wrapper
└── components/
    ├── DesktopView.tsx
    ├── MobileView.tsx
    ├── ChatMessage.tsx
    ├── ThinkingIndicator.tsx      # Animated 3-dot loading bubble
    ├── QuickReplyChips.tsx
    └── ui/                        # shadcn/ui primitives (10 components)
```

---

## Chat History

Conversation history is stored in the browser's **localStorage**:

| Key | Value |
|-----|-------|
| `phonphai_session_id` | UUID for the current session |
| `phonphai_messages` | Full message array (JSON) |

History is restored automatically on page reload. Use the **Clear Chat** button to reset.
