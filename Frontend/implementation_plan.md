# Phonphai Chatbot Frontend Implementation Plan

This plan details the steps to build a responsive, Dockerized React frontend for the Phonphai chatbot, fulfilling all user requirements while cleanly tying into the existing Python backend.

## User Review Required
> [!IMPORTANT]
> Please review this plan before I proceed. Specifically, let me know if you are okay with initializing the project inside `Frontend/web` using Vite (React + TypeScript). 

## Proposed Architecture

1. **Framework:** We will use Vite with React and TypeScript. Since no authentication is required immediately, we don't strictly need Next.js serverside rendering; a fast Single Page Application (SPA) is perfect for this.
2. **Styling:** We will adapt the Figma-generated UI found in `Frontend/figma/components`. If it relies on Tailwind CSS, we will configure Tailwind.
3. **State Management & History:** We will use modern React Hooks (`useState`, `useEffect`) and store the chat history in the browser's `localStorage`. This complies with the requirement for handling history without a backend database.
4. **Internationalization:** We will implement a lightweight context for TH/EN translations.
5. **Backend Integration:** The chat will communicate with the backend via `POST http://localhost:8080/api/v1/chat/`.

## Proposed Changes

### Frontend Infrastructure Setup
- Initialize Vite project in `/Users/alarmirl/Documents/GitHub/PhonphaiChatbot/Frontend/web`.
- Configure environment variables to point to the backend API (`VITE_API_URL=http://localhost:8080`).

### Core Features Implementation
#### [NEW] `Frontend/web/src/hooks/useChat.ts`
- Manage chat session ID using `uuid`.
- Load and save chat history from `localStorage` keyed by `session_id`.
- Function to clear chat (generates new `session_id` and empties state).
- Provide a `sendMessage` function that appends a user message, sets `isThinking` to `true`, calls the API, and appends the AI reply.

#### [NEW] `Frontend/web/src/contexts/LanguageContext.tsx`
- Manage TH/ENG locale strings. Provide translations for "How can I help you today?", etc.

#### UI Components Integration
- Copy the existing components from `Frontend/figma/components` to `Frontend/web/src/components`.
- Wire up `DesktopView` and `MobileView` to use the `useChat` hook.
- Implement the "initial greeting" by pushing an AI message to the chat trace when a new session is created.
- Implement "thinking state" by showing a typing indicator or loading spinner when `isThinking` is true.

### Dockerization
#### [NEW] `Frontend/web/Dockerfile`
- Multi-stage build: use Node to build the Vite app, and serve it via Caddy or Nginx for optimal local and production performance.

#### [NEW] `Frontend/web/docker-compose.yml`
- We will set up a local `docker-compose.yml` to run the frontend independently or seamlessly next to the microservices.

## Verification Plan

### Manual Verification
- **Run the Development Server:** Use `npm run dev` to test interactions locally.
- **Language Switcher:** Ensure toggling TH/ENG updates static text immediately.
- **Chat History:** Refresh the page to ensure history is persisted.
- **Clear Session:** Verify that clearing the session resets the chat and generates the initial greeting again.
- **Docker Build:** Run `docker-compose up -d` to verify the frontend works properly in an isolated container hitting the API Gateway.
