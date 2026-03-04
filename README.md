# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

```
PhonphaiChatbot/
├── Backend/                  # Python microservices (Docker Compose)
│   ├── docker-compose.yml
│   ├── pyproject.toml        # ruff linting/formatting config
│   ├── protos/               # Protobuf definitions + auto-generated *_pb2.py files
│   └── services/
│       ├── api-gateway/      # FastAPI HTTP server (port 8000 → exposed 8080)
│       ├── agent/            # LangGraph + Gemini gRPC server (port 50052)
│       └── retriever/        # ChromaDB + MongoDB gRPC server (port 50051)
└── Frontend/
    ├── figma/                # Figma-Make export — reference only, not runnable as-is
    ├── design/               # UI mockup PNGs
    └── web/                  # Vite + React + TypeScript SPA
        ├── src/
        │   ├── App.tsx
        │   ├── main.tsx
        │   ├── globals.css
        │   ├── types.ts
        │   ├── contexts/LanguageContext.tsx
        │   ├── hooks/useChatManager.ts
        │   ├── hooks/useMediaQuery.ts
        │   ├── services/api.ts
        │   └── components/
        │       ├── ui/            (10 shadcn/ui primitives)
        │       ├── ChatMessage.tsx
        │       ├── ThinkingIndicator.tsx
        │       ├── QuickReplyChips.tsx
        │       ├── DesktopView.tsx
        │       └── MobileView.tsx
        ├── Dockerfile
        └── docker-compose.yml
```

## Frontend Commands

All commands run from `Frontend/web/`:

```bash
npm run dev        # Start dev server at http://localhost:5173
npm run build      # TypeScript check + Vite production build
npm run lint       # ESLint
npm run preview    # Preview production build locally
```

Docker:
```bash
# From Frontend/web/
docker compose up --build
# App served at http://localhost:3000
# Override API URL: VITE_API_URL=http://your-host:8080 docker compose up --build
```

Dependencies installed (for reference when adding packages or recreating the project):
```
# Runtime
uuid, lucide-react, class-variance-authority, clsx, tailwind-merge
@radix-ui/react-slot, @radix-ui/react-avatar, @radix-ui/react-switch
@radix-ui/react-separator, @radix-ui/react-scroll-area, @radix-ui/react-dialog

# Dev (beyond the vite react-ts scaffold)
@types/uuid, tailwindcss, @tailwindcss/vite
```

## Backend Commands

All commands run from `Backend/`:

```bash
# Start all services (requires GEMINI_API_KEY in environment)
GEMINI_API_KEY=your_key docker compose up --build

# Rebuild a single service
docker compose up --build api-gateway

# Python linting/formatting (ruff, configured in pyproject.toml)
ruff check .
ruff format .
```

Services start in dependency order: mongo + chroma → retriever → agent → api-gateway.

## System Architecture

### Request Flow
```
Browser → POST http://localhost:8080/api/v1/chat/
        → api-gateway (FastAPI)
        → agent:50052 (gRPC AgentService.Chat)
        → LangGraph ReAct loop (Gemini gemini-2.5-flash-lite)
              ↕ tool calls
        → retriever:50051 (gRPC RetrieverService.Search)
        → ChromaDB (vector search, all-MiniLM-L6-v2 embeddings)
```

### Backend Service Internals

**api-gateway** (`services/api-gateway/`): FastAPI app that opens persistent gRPC channels to `agent` and `retriever` on startup (stored in `state.gRPCState`). Exposes `/api/v1/chat/` and `/api/v1/files/` REST endpoints. Config via env vars `AGENT_HOST` and `RETRIEVER_HOST`.

**agent** (`services/agent/`): LangGraph `StateGraph` with two nodes — `agent` (Gemini LLM) and `tools` (ToolNode). Bound with 3 tools: `search_remedy_tickets`, `search_disaster_protocols`, `search_user_manuals`. Each chat invocation starts fresh — session history is **not** persisted between calls. The persistent gRPC connection to retriever is stored in `AgentState`.

**retriever** (`services/retriever/`): Dual-storage system. MongoDB stores raw file bytes + metadata. ChromaDB holds vectorized chunks for semantic search. Three themed collections (`remedy`, `disaster`, `manual`) each handled by a subclass of `BaseTheme`. File upload is a client-streaming gRPC call: first message = metadata, subsequent messages = `chunk_data` bytes.

### Protobuf / gRPC

Auto-generated files (`*_pb2.py`, `*_pb2_grpc.py`) live in `Backend/protos/` and are copied into each service's Docker build context. **Do not edit** these generated files. To regenerate after modifying `.proto` files:

```bash
cd Backend/protos
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chatbot.proto retriever.proto
```

### Frontend Architecture

The React SPA (`Frontend/web/src/`) uses:

- **`LanguageContext`** — TH/EN toggle via `t(key)` translation function; wraps the entire app in `main.tsx`
- **`useChatManager(greetingText)`** — all chat state: `sessionId` (uuid), `messages` array, `isThinking` flag. Called as `useChatManager(t('greeting'))` in `App.tsx` so the greeting reflects the current language. Thinking bubbles (`isThinking: true` on `Message`) are never persisted and replaced in-place when the API responds. `clearChat(newGreetingText)` generates a new session ID.
- **`services/api.ts`** — single `sendMessage()` function; reads `VITE_API_URL` (baked in at build time, default `http://localhost:8080`)
- **`components/ui/`** — contains only the **10 files actually used** (`utils.ts`, `button.tsx`, `input.tsx`, `avatar.tsx`, `switch.tsx`, `scroll-area.tsx`, `separator.tsx`, `sheet.tsx`, `badge.tsx`, `card.tsx`). The other 38 from `Frontend/figma/components/ui/` are not copied. Versioned esm.sh import specifiers are stripped when copying (e.g. `@radix-ui/react-dialog@1.1.6` → `@radix-ui/react-dialog`).

Desktop vs. Mobile layout is switched at 768px via `useMediaQuery`.

**localStorage keys:**
- `phonphai_session_id` — uuid for the current session; reset on `clearChat()`
- `phonphai_messages` — `Message[]` serialized as JSON (thinking bubbles excluded)

**`LanguageContext` translation keys** — all strings passed to `t()`:
`greeting`, `placeholder`, `clearChat`, `thinking`, `languageLabel`, `assistantTitle`, `assistantSubtitle`, `howCanIHelp`, `selectTopic`, `errorMessage`,
`quickReply_flood`, `quickReply_forgotPassword`, `quickReply_shelter`, `quickReply_contact`, `quickReply_hotline`, `quickReply_safety`,
`card_manual`, `card_manual_desc`, `card_relief`, `card_relief_desc`, `card_shelter`, `card_shelter_desc`, `card_report`, `card_report_desc`

### Tailwind CSS v4

The frontend uses Tailwind v4 with the `@tailwindcss/vite` plugin — there is no `tailwind.config.ts`. Theme tokens are defined as CSS variables in `src/globals.css` using `@theme inline`. The brand red is `#D32F2F`.

## Key Environment Variables

| Variable | Service | Description |
|---|---|---|
| `GEMINI_API_KEY` | agent | Google Gemini API key (required) |
| `RETRIEVER_HOST` | api-gateway, agent | `host:port` for retriever gRPC (default `retriever:50051`) |
| `AGENT_HOST` | api-gateway | `host:port` for agent gRPC (default `agent:50052`) |
| `MONGO_URI` | retriever | MongoDB connection string (default `mongodb://mongo:27017`) |
| `CHROMA_HOST` | retriever | ChromaDB hostname (default `chroma`) |
| `VITE_API_URL` | frontend | Backend base URL, baked in at build time (default `http://localhost:8080`) |

## Known Issues

- The agent service does not maintain conversation history across requests — each call to `AgentService.Chat` starts a fresh LangGraph invocation with only the current message.
- `Backend/services/api-gateway/routers/files.py` has two `@router.get("/")` handlers; only the first is reachable by FastAPI.
