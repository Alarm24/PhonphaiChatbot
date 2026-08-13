# Phonphai Chatbot — เอกสารสถาปัตยกรรมระบบและคู่มือการเชื่อมต่อ

> **กลุ่มผู้อ่าน:** วิศวกรซอฟต์แวร์ที่ต้องรัน ตั้งค่า ต่อยอด หรือเชื่อมต่อกับระบบนี้
> **ขอบเขต:** Backend ทั้งหมด (`backend/`) และ Frontend เว็บ (`Frontend/web/`)
> **ฉบับภาษาอังกฤษ:** [`ARCHITECTURE.md`](./ARCHITECTURE.md)

---

## ⚠️ อ่านก่อน — ข้อแก้ไข 2 เรื่อง

**1. `README.md` ที่ root ล้าสมัยแล้ว** โดยอธิบายสถาปัตยกรรมเก่า (ChromaDB, Google Gemini SDK, `GEMINI_API_KEY`, embedding `all-MiniLM-L6-v2`, `CHROMA_HOST`) **ซึ่งไม่เป็นความจริงอีกต่อไป** ระบบปัจจุบันใช้ **Qdrant + PostgreSQL + MongoDB + OpenRouter + `intfloat/multilingual-e5-large`** และ README นั้นยังไม่ได้กล่าวถึง service `postgres` เลย เอกสารฉบับนี้ใช้แทน README ดังกล่าว

**2. `backend/data/chroma_data/` เป็นข้อมูลตกค้างที่ไม่ได้ใช้แล้ว** ค้นทั้ง repo ด้วยคำว่า `chroma` ไม่พบการอ้างอิงในโค้ดเลยแม้แต่ที่เดียว เป็นของเหลือจากสถาปัตยกรรมก่อนย้ายมาใช้ Qdrant สามารถลบทิ้งได้

---

## สารบัญ

1. [ระบบนี้คืออะไร](#1-ระบบนี้คืออะไร)
2. [เริ่มต้นใช้งาน](#2-เริ่มต้นใช้งาน)
3. [สถาปัตยกรรม](#3-สถาปัตยกรรม)
4. [รายละเอียดแต่ละ Service](#4-รายละเอียดแต่ละ-service)
5. [ที่เก็บข้อมูล — อะไรอยู่ที่ไหน](#5-ที่เก็บข้อมูล--อะไรอยู่ที่ไหน)
6. [คู่มือการตั้งค่า (Configuration)](#6-คู่มือการตั้งค่า-configuration)
7. [REST API Reference](#7-rest-api-reference)
8. [gRPC / สัญญาการสื่อสารภายใน](#8-grpc--สัญญาการสื่อสารภายใน)
9. [คู่มือการเชื่อมต่อ (Integration)](#9-คู่มือการเชื่อมต่อ-integration)
10. [ตำราการปรับเปลี่ยนระบบ](#10-ตำราการปรับเปลี่ยนระบบ)
11. [การจัดการฐานความรู้ (Knowledge Base)](#11-การจัดการฐานความรู้-knowledge-base)
12. [ระบบประเมินผล (Evaluation)](#12-ระบบประเมินผล-evaluation)
13. [ความปลอดภัยและปัญหาที่ทราบแล้ว](#13-ความปลอดภัยและปัญหาที่ทราบแล้ว)
14. [การแก้ปัญหาเบื้องต้น](#14-การแก้ปัญหาเบื้องต้น)
15. [แผนผังไฟล์](#15-แผนผังไฟล์)

---

## 1. ระบบนี้คืออะไร

**Phonphai** คือ **แชทบอทแบบ Retrieval-Augmented Generation (RAG)** สองภาษา (ไทย/อังกฤษ) ที่พัฒนาให้ **สภากาชาดไทย** โดยตอบคำถาม 3 ประเภทหลัก ซึ่งแต่ละประเภทใช้แหล่งข้อมูลต่างกัน

| ประเภท | คำไทย | แหล่งข้อมูล | ต้อง Login |
|---|---|---|---|
| **Manual** — วิธีใช้งานแอป คู่มือผู้ใช้ ขั้นตอนปฏิบัติงาน (SOP) การรายงาน | คู่มือ | ค้นหาแบบ vector ใน Qdrant จาก PDF ที่อัปโหลด | ไม่ต้อง |
| **Disaster** — เหตุฉุกเฉิน การอพยพ สาธารณสุข ความต่อเนื่องทางธุรกิจ | ภัยพิบัติ | ค้นหาแบบ vector ใน Qdrant จาก PDF ที่อัปโหลด | ไม่ต้อง |
| **Remedy** — ตรวจสอบสถานะคำร้อง (`SKN-2567-0006`) | คำร้อง | **Query SQL บน PostgreSQL** ไม่ใช่ vector search | **ต้อง** |

มีการตัดสินใจเชิงออกแบบ 2 ข้อที่เป็นหัวใจของระบบ

1. **ข้อมูลคำร้อง (Remedy) ไม่เคยเข้าไปอยู่ใน context ของ LLM เลย** ผลลัพธ์จาก SQL ถูกส่งกลับเป็น *artifact* นอกช่องทางที่โมเดลมองไม่เห็น และข้อความสุดท้ายที่ผู้ใช้เห็นถูกสร้างจาก **เทมเพลตภาษาไทยแบบตายตัว** ไม่ใช่จาก LLM วิธีนี้ป้องกันการที่โมเดลจะ hallucinate สถานะคำร้อง และบังคับสิทธิ์การเข้าถึงข้อมูลระดับแถว (row-level) ตามผู้ใช้แต่ละคน
2. **คำตอบถูกออกแบบให้สั้นกระชับสำหรับสถานการณ์เร่งด่วน** คำตอบหมวดภัยพิบัติตั้งค่าเริ่มต้นไว้ที่ 1 ประโยค พร้อมมีการเรียก LLM อีกรอบเพื่อบีบอัดคำตอบให้สั้นลง และมีคำตอบสำเร็จรูปแบบตายตัว (safety override) สำหรับ 4 สถานการณ์วิกฤตเรื่องน้ำท่วมและแผ่นดินไหว

### สรุปเทคโนโลยีที่ใช้

| ชั้น | เทคโนโลยี |
|---|---|
| Frontend | React 19, TypeScript 5.9, Vite 7, Tailwind CSS v4, Radix UI (shadcn/ui), react-router-dom 7 |
| API Gateway | Python 3.11, FastAPI, uvicorn, PyJWT, bcrypt |
| Agent | Python 3.11, LangGraph, LangChain, OpenRouter (`google/gemini-2.5-flash`) |
| Retriever | Python 3.11 บน CUDA 12.4, sentence-transformers, Qdrant client, rank_bm25 |
| Vector store | Qdrant 1.10.1 — 1024 มิติ, cosine |
| Embeddings | `intfloat/multilingual-e5-large` (รันในเครื่อง, HuggingFace) |
| Reranker | `BAAI/bge-reranker-v2-m3` (cross-encoder รันในเครื่อง, GPU) |
| ฐานข้อมูลเชิงสัมพันธ์ | PostgreSQL 16 (Alpine) |
| ฐานข้อมูลเอกสาร | MongoDB 8.2 |
| RPC ระหว่าง service | gRPC (protobuf 3) |
| Observability | LangSmith tracing, loguru |

---

## 2. เริ่มต้นใช้งาน

### สิ่งที่ต้องมี

- Docker Engine 24+ และ Docker Compose v2
- **NVIDIA GPU พร้อม container toolkit** — service `retriever` ประกาศจอง GPU ไว้ใน `docker-compose.yml` ถ้าไม่มี `docker compose up` จะล้มเหลว ดูวิธีถอดข้อกำหนดนี้ที่ [§10.6](#106-เปลี่ยน-reranker--รันโดยไม่ใช้-gpu)
- Node.js 20+ (เฉพาะกรณีรัน Frontend นอก Docker)
- Python 3.10+ พร้อม `ruff` (เฉพาะการ lint)

### 1. ตั้งค่า Secret

สร้างไฟล์ `backend/.env`

```env
OPENROUTER_API_KEY=
LANGCHAIN_API_KEY=
```

ทั้งสอง key จำเป็นสำหรับการทำงานเต็มรูปแบบ
- `OPENROUTER_API_KEY` — **จำเป็นต้องมี** service agent จะโยน `ValidationError` ตั้งแต่ตอน import ถ้าไม่มี และ retriever ก็ใช้ key นี้ในการแปลง PDF ด้วย
- `LANGCHAIN_API_KEY` — สำหรับ LangSmith tracing ซึ่ง**เปิดใช้งานเป็นค่าเริ่มต้น** (`LANGCHAIN_TRACING_V2=true`) ถ้า key ว่าง SDK จะพยายามส่ง trace แล้วล้มเหลว ซึ่งไม่เป็นอันตรายแต่จะมี log รบกวน

> **หมายเหตุ:** `backend/README.md` อ้างถึงไฟล์ `backend/.env.example` แต่ **ไฟล์นั้นไม่มีอยู่จริง** ใน repo ต้องสร้าง `.env` เองด้วยมือ

### 2. เริ่มระบบ Backend

```bash
cd backend
docker compose up -d          # หรือ: make up
docker compose logs -f        # หรือ: make logs
```

ลำดับการเริ่มถูกบังคับด้วย health check: `postgres` + `qdrant` + `mongo` → `retriever` (healthy) → `agent` (healthy) → `api-gateway`

การ build `retriever` **ครั้งแรก** จะดาวน์โหลดและฝัง model weights ประมาณ 3 GB ลงใน image ดังนั้นจะใช้เวลานาน

- API Gateway → http://localhost:8080
- เอกสาร API แบบโต้ตอบ → http://localhost:8080/docs
- Qdrant dashboard → http://localhost:6333/dashboard
- Postgres → `localhost:5432` (`phonphai` / `phonphai` / `phonphai`)

### 3. เริ่ม Frontend

```bash
cd Frontend/web
npm install
npm run dev          # → http://localhost:5173
```

หรือผ่าน Docker

```bash
cd Frontend/web
docker compose up --build     # → http://localhost:3000
```

### 4. เข้าสู่ระบบ

ระบบสร้างบัญชี 2 บัญชีให้อัตโนมัติตอนบูตครั้งแรก (ดู [§6.1](#61-api-gateway))

| ชื่อผู้ใช้ | รหัสผ่าน | บทบาท | staff_id |
|---|---|---|---|
| `admin` | `a1234567` | admin | — |
| `user` | `a1234567` | user | `13266` |

บัญชี `admin` อัปโหลดไฟล์เข้าฐานความรู้ได้ที่ `/admin/files` ส่วนบัญชี `user` ค้นคำร้องที่เป็นของเจ้าหน้าที่รหัส `13266` ได้

### 5. ทดสอบ

```bash
# เข้าสู่ระบบ
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"a1234567"}'

# ถามคำถาม (หมวด manual/disaster ไม่ต้อง login)
curl -X POST http://localhost:8080/api/v1/chat/ \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"test-1","message":"น้ำท่วมชั้นล่าง ต้องทำอย่างไร"}'
```

---

## 3. สถาปัตยกรรม

### 3.1 โครงสร้าง Container

```mermaid
graph TB
    subgraph browser["เบราว์เซอร์"]
        FE["Frontend SPA<br/>nginx :80 → host :3000<br/>(หรือ Vite dev :5173)"]
    end

    subgraph ragnet["Docker network: rag_net"]
        GW["api-gateway<br/>FastAPI :8000 → host :8080"]
        AG["agent<br/>gRPC :50052"]
        RT["retriever<br/>gRPC :50051<br/>GPU"]
        PG[("postgres 16<br/>:5432")]
        MG[("mongo 8.2<br/>:27017")]
        QD[("qdrant 1.10.1<br/>:6333")]
    end

    subgraph ext["ภายนอก"]
        OR["OpenRouter API<br/>google/gemini-2.5-flash"]
        LS["LangSmith"]
    end

    FE -->|"HTTPS/JSON + SSE"| GW
    GW -->|"gRPC Chat / ChatStream"| AG
    GW -->|"gRPC Upload/List/Delete"| RT
    GW --> MG
    AG -->|"gRPC Search"| RT
    AG -->|"SQL issue_logs"| PG
    AG --> OR
    AG --> LS
    RT --> QD
    RT --> MG
    RT -->|"แปลง PDF"| OR
    RT --> LS
```

### 3.2 ลำดับการทำงานของคำขอแชท

```mermaid
sequenceDiagram
    participant C as Client
    participant G as api-gateway
    participant A as agent
    participant R as retriever
    participant Q as Qdrant
    participant P as Postgres
    participant L as OpenRouter

    C->>G: POST /api/v1/chat/stream
    G->>G: ถอดรหัส JWT → CurrentUser (หรือ anonymous)
    G->>G: _enforce_ticket_login (401 ถ้า anonymous + พบรหัสคำร้อง)
    G->>G: session_id = user_id ถ้า login แล้ว
    G->>A: gRPC ChatStream(session_id, message, role, staff_id, username)

    A->>A: censor_bad_words (กรองคำหยาบขาเข้า)
    A->>L: เรียก LLM พร้อม tool 4-5 ตัว
    L-->>A: tool_calls: search_user_manuals("...")

    alt Manual / Disaster
        A->>R: gRPC Search(query, theme, limit)
        R->>Q: ค้นหา vector แบบ dense (top 25)
        R->>R: ค้นหา BM25 แบบ sparse (top 25)
        R->>R: รวมผลด้วย weighted RRF (0.6 / 0.4, k=60)
        R->>R: จัดอันดับใหม่ด้วย BGE cross-encoder
        R-->>A: chunk อันดับต้น N รายการ
    else Remedy
        A->>A: ตรวจสิทธิ์ (anonymous → ปฏิเสธ; ไม่ใช่ admin → เห็นเฉพาะ staff_id ตัวเอง)
        A->>P: SELECT ... FROM issue_logs WHERE code = ...
        P-->>A: แถวข้อมูล (เก็บไว้นอก context ของ LLM ในรูป artifact)
    end

    A->>L: LLM เรียบเรียงคำตอบจากผลของ tool
    L-->>A: คำตอบร่าง
    A->>A: censor_bad_words (กรองคำหยาบขาออก)
    A->>A: safety override / บีบอัดคำตอบภัยพิบัติ
    A->>A: ticket override — แทนที่ข้อความด้วยเทมเพลตไทย
    A-->>G: stream: token ครั้งละ 2 ตัวอักษร ทุก 25ms แล้วตามด้วย final_response
    G-->>C: SSE frames: data: {"type":"token"|"done"|"error"}
```

### 3.3 ข้อเท็จจริงสำคัญเชิงสถาปัตยกรรม

**Streaming เป็นการจำลอง ไม่ใช่ streaming จริง** `ChatStream` สมัครรับ `messages` mode ของ LangGraph แต่ **ทิ้ง token ของ LLM ทุกตัว** (`agent/server.py:193-197`) เพราะคำตอบร่างอาจถูกเซ็นเซอร์ ถูกแทนที่ด้วย safety override หรือถูกเขียนใหม่ในภายหลัง เมื่อ graph ทำงานเสร็จแล้วเท่านั้น ระบบจึงเล่นข้อความที่เสร็จสมบูรณ์กลับมาแบบเครื่องพิมพ์ดีดที่ **2 ตัวอักษรทุก 25 มิลลิวินาที** (`agent/server.py:175-184`) **เวลาที่รอ token แรกจึงเท่ากับเวลาสร้างคำตอบทั้งหมด** อย่าออกแบบ UX ที่สมมติว่ามีการสร้างข้อความแบบค่อยเป็นค่อยไป

**การเลือกเส้นทาง (Routing) ขับเคลื่อนด้วย prompt ไม่ใช่โค้ด** ไม่มีตัวจำแนกเจตนา (intent classifier) LLM ที่เรียก tool ได้เป็นผู้เลือกเองจาก tool 4-5 ตัว โดยอาศัยหัวข้อ 1 ของ system prompt (`agent/prompts/prompt.py:3-12`) และ docstring ของแต่ละ tool **การแก้ docstring ส่งผลต่อพฤติกรรมการเลือกเส้นทางมากกว่าการแก้ system prompt**

**คำตอบเรื่องคำร้องเป็นแบบตายตัว** เมื่อ tool หมวด Remedy ทำงาน ข้อความที่ LLM เขียนจะ**ถูกทิ้งทั้งหมด** (`agent/server.py:143-144`) แล้วแทนที่ด้วยเทมเพลต
- พบข้อมูล: `คำร้องหมายเลข {code} มีสถานะ {status} และมีการดำเนินการระดับ {process_level}`
- ไม่พบ: `ไม่พบข้อมูลคำร้องหมายเลข {code}`

**Agent ไม่มีสถานะ (stateless) เป็นค่าเริ่มต้น** `CHAT_HISTORY_ENABLED` มีค่าเริ่มต้นเป็น `False` และ **ไม่ได้ตั้งค่าไว้ใน `docker-compose.yml`** ดังนั้นตามค่าที่มาให้ ทุกคำขอจะเริ่ม LangGraph ใหม่โดยมีเพียงข้อความปัจจุบันเท่านั้น tool `load_conversation_history` ไม่ถูกผูกเข้ากับโมเดลด้วยซ้ำ ดู [§10.2](#102-เปิดใช้งานประวัติการสนทนา)

**Retriever ไม่เคยคืนผลลัพธ์ว่าง** สำหรับ collection ที่มีข้อมูล หลังการกรองด้วยคะแนน ถ้าไม่มีอะไรผ่านเกณฑ์เลย ระบบจะบังคับใส่ผลอันดับ 1 กลับเข้ามา (`retriever/themes/base.py:217-219`)

---

## 4. รายละเอียดแต่ละ Service

### 4.1 `api-gateway` — ช่องทางสาธารณะเพียงทางเดียว

`backend/services/api-gateway/`

จุดเข้า HTTP เพียงจุดเดียวของระบบ ทำหน้าที่รับ JSON ตรวจสอบตัวตน บังคับสิทธิ์ตามบทบาท และแปลงคำขอเป็นการเรียก gRPC เป็นเจ้าของที่เก็บบัญชีผู้ใช้และเป็นผู้เขียนประวัติการสนทนา แต่**ไม่ทำ** retrieval และไม่เรียก LLM เอง

| คุณสมบัติ | ค่า |
|---|---|
| Framework | FastAPI + uvicorn, worker เดียว |
| จุดเริ่ม | `main.py:108` (app), `main.py:122-123` (server) |
| พอร์ตใน container | 8000 → host **8080** |
| เอกสารอัตโนมัติ | `/docs`, `/redoc`, `/openapi.json` (เปิดใช้งาน) |
| Health endpoint | **ไม่มี** — ไม่มี `/health` และไม่มี healthcheck ใน compose |
| Base image | `python:3.11-slim`, build 2 stage ด้วย `uv` |

**ลำดับการเริ่มทำงาน** (`main.py:65-104`)
1. เปิด gRPC aio channel แบบ **insecure** ถาวรไปยัง `RETRIEVER_HOST` และ `AGENT_HOST`
2. เก็บ stub ไว้บนคลาส global `gRPCState` (`state.py:4-8`) — ไม่ใช่ `app.state`
3. สร้าง user store ผ่าน `make_user_store(settings)` แล้วสร้างบัญชี admin และ user เริ่มต้น
4. ถ้า `CHAT_HISTORY_ENABLED` ให้สร้าง chat-history store
5. ตอนปิด ให้ปิด channel ทั้งสอง *(แต่ Mongo client / Postgres pool ไม่เคยถูกปิด)*

**ข้อสังเกต:** service นี้ **ไม่มีการเรียก `os.getenv` เลยแม้แต่ที่เดียว** การตั้งค่าทั้งหมดประกาศเป็น field ของ `pydantic-settings` ใน `config.py` และถูก cache ด้วย `@lru_cache()` — **การเปลี่ยนค่าตั้งค่าใด ๆ ต้อง restart เสมอ**

### 4.2 `agent` — ตัวควบคุมลำดับงานด้วย LangGraph

`backend/services/agent/`

| คุณสมบัติ | ค่า |
|---|---|
| Framework | LangGraph `StateGraph` compile โดย **ไม่มี checkpointer** |
| จุดเริ่ม | `main.py:14` (`serve()`), `main.py:54-55` |
| พอร์ต | gRPC **50052**, `[::]`, insecure |
| Server | `grpc.aio.server()` **ไม่ส่ง argument ใด ๆ** — เป็น asyncio ล้วน ไม่จำกัด thread pool ไม่มี `maximum_concurrent_rpcs` |
| I/O ที่บล็อก | ย้ายไป thread ด้วย `asyncio.to_thread(...)` |
| Base image | `python:3.11-slim` |

**โครงสร้าง Graph** (`core/graph.py:434-449`)

```
START → agent ⇄ tools
          ↓ (ไม่มี tool_calls)
      format_answer → END
```

**Node `agent`** (`core/graph.py:239`)
1. กรองขาเข้า — `censor_bad_words` บนข้อความล่าสุดของผู้ใช้ โดยคง `id` เดิมไว้ เพื่อให้ `add_messages` เขียนทับแทนที่จะต่อท้าย
2. ใส่ `SystemMessage(SYSTEM_PROMPT)` ไว้ข้างหน้า — ใส่ใหม่**ทุกรอบ**ของ loop ไม่เคยเก็บลง state
3. เรียกโมเดลที่ผูก tool ไว้
4. **ตรวจงบ tool** — ถ้า `tool_call_rounds > MAX_TOOL_CALL_ROUNDS` (ค่าเริ่มต้น 3) ให้ทิ้ง tool call แล้วเรียกโมเดล*ที่ไม่ผูก tool*อีกครั้งพร้อมข้อความว่าใช้ tool ครบโควตาแล้ว
5. **กู้คืนกรณีคำตอบว่าง** — ถ้าเนื้อหาว่างแต่มี chunk อยู่ ให้ลองใหม่แบบไม่ผูก tool 1 ครั้ง ถ้ายังว่างอีก ให้ตกไปใช้ regex ดึงจำนวนขั้นตอนออกจาก chunk

**Node `tools`** — ใช้ `langgraph.prebuilt.ToolNode` มาตรฐาน มี edge กลับไป `agent` แบบไม่มีเงื่อนไข

**Node `format_answer`** (`core/graph.py:353`)
1. กรองขาออก — `censor_bad_words`
2. รวบรวม artifact โดยไล่ message **ย้อนกลับ และหยุดที่ human message แรก** (นับเฉพาะเทิร์นปัจจุบัน)
3. **Safety override หมวดภัยพิบัติ** — คำตอบตายตัว 4 ชุด (ดูด้านล่าง)
4. **บีบอัดคำตอบภัยพิบัติ** — เรียก LLM เพิ่มอีกรอบ เฉพาะเมื่อ override *ไม่*ทำงาน และเก็บผลใหม่ก็ต่อเมื่อสั้นลงจริง
5. รวมยอดค่าใช้จ่ายจากทุก message

**คำตอบสำเร็จรูปภาษาไทย (Safety Override)** (`core/graph.py:102-146`) — ทำงานเมื่อมี chunk หมวด `Disaster` อยู่ ข้อความคำถามถูก normalize โดยตัดทุกอักขระนอกช่วง U+0E00–U+0E7F และแก้ `น้ํา→น้ำ`, `ทํา→ทำ`

| คำสำคัญที่กระตุ้น | คำตอบสำเร็จรูป |
|---|---|
| `น้ำท่วม` + `ชั้นล่าง` + `ชั้นสอง` | อยู่กับที่ อย่าว่ายน้ำ กดขอความช่วยเหลือฉุกเฉิน |
| `น้ำลด` + (`ทำความสะอาด` \| `โคลน`) | สวมรองเท้าบูตและถุงมือยาง ขอชุดทำความสะอาด |
| `เรือ` + (`อพยพ` \| `น้ำหลาก`) | สวมเสื้อชูชีพ กระจายน้ำหนัก อย่ายืน |
| `แผ่นดินไหว` + (`ไฟดับ` \| `มองไม่เห็น`) | ใช้ไฟฉาย ห้ามใช้เทียน/ไฟแช็ก (แก๊สรั่ว) |

**Tools** (`tools/retriever_tool.py:314-319` และ tool ประวัติที่เพิ่มตามเงื่อนไข)

| Tool | Signature | แหล่งข้อมูล | ขีดจำกัด |
|---|---|---|---|
| `search_remedy_tickets` | `(ticket_code: str)` | Postgres `issue_logs` | — |
| `list_my_remedy_tickets` | `()` | Postgres `issue_logs` | — |
| `search_disaster_protocols` | `(query: str)` | Retriever gRPC, `theme=DISASTER` | 4 chunk, ตัดข้อความ 900 ตัวอักษร |
| `search_user_manuals` | `(query: str)` | Retriever gRPC, `theme=MANUAL` | 8 chunk, ตัดข้อความ 1800 ตัวอักษร |
| `load_conversation_history` | `(turns: int = 10)` | Mongo/Postgres | จำกัดอยู่ในช่วง [1, 20] |

ทุก tool ใช้ `@tool(response_format="content_and_artifact")` → คืนค่าเป็น `tuple[str, list]` โดย **string** ส่งให้โมเดล ส่วน **list** กลายเป็น `ToolMessage.artifact` ซึ่ง **ไม่เคยถูกแสดงให้ LLM เห็น** นี่คือกลไกความเป็นส่วนตัวที่ทำให้ข้อมูลคำร้องไม่หลุดเข้า prompt

**การตรวจสิทธิ์คำร้อง** (`tools/retriever_tool.py:177-194`, `:250-263`) — บังคับที่ฝั่ง server เป็นการป้องกันซ้อนชั้นหลังด่าน regex ของ gateway
- Anonymous → คืนข้อความปฏิเสธ **ไม่แตะฐานข้อมูลเลย**
- Admin → `staff_filter = None` (เห็นทั้งหมด)
- ผู้ใช้ทั่วไป → `staff_filter = auth.staff_id` (เห็นเฉพาะของตัวเอง)
- ผู้ใช้ที่ไม่มี `staff_id` → คืนข้อความปฏิเสธ

**การตีความรูปแบบรหัสคำร้อง** (`tools/retriever_tool.py:10-43`) แยกเป็น `lookup_kind` 4 แบบ ซึ่งเลือกใช้เมธอด SQL ต่างกัน

| รูปแบบที่ผู้ใช้พิมพ์ | `lookup_kind` |
|---|---|
| `SKN-2567-0006`, `BKK 2569 0001` | `code` |
| `2569 0001`, `2569-0001` | `year_suffix` |
| `2569` | `year` |
| `0001` | `suffix` |

### 4.3 `retriever` — ชั้นฐานความรู้

`backend/services/retriever/`

| คุณสมบัติ | ค่า |
|---|---|
| จุดเริ่ม | `main.py:10-21` |
| พอร์ต | gRPC **50051**, `[::]`, insecure |
| Server | `grpc.server(ThreadPoolExecutor(max_workers=10))` |
| Base image | `nvidia/cuda:12.4.1-runtime-ubuntu22.04` + Python 3.11 |
| GPU | จองไว้ใน compose แต่ใช้เฉพาะ **reranker เท่านั้น** |
| Volume | **ไม่มี** — model ถูกฝังลง image ตอน build |

**ทะเบียน Theme** (`server.py:16-19`) — สำคัญเชิงโครงสร้าง

```python
self.themes = {
    retriever_pb2.DISASTER: DisasterTheme(),
    retriever_pb2.MANUAL: ManualTheme(),
}
```

`REMEDY` ถูกประกาศไว้ใน proto และ map ไว้ในเส้นทาง upload/delete แต่ **ไม่มี handler สำหรับการค้นหา** การเรียก `Search(theme=REMEDY)` จะ abort ด้วย `INVALID_ARGUMENT` ข้อมูล Remedy อยู่ใน Postgres

**ขั้นตอนการค้นคืน ตามลำดับ**

| ขั้น | รายละเอียด | ตำแหน่ง |
|---|---|---|
| 0. เริ่มระบบ | ดึง **ทุก point** ออกจาก collection (ครั้งละ 256) เพื่อสร้าง index `BM25Okapi` ในหน่วยความจำ | `themes/base.py:51`, `:57-69` |
| 1. เตรียม query | Dense: เติม `"query: "` ข้างหน้า (E5 asymmetric prefix) · Sparse: token ภาษาอังกฤษ **+ trigram อักขระไทย** | `db/qdrant.py:55`, `themes/base.py:16-29` |
| 2. Dense | ค้น Qdrant แบบ cosine, `limit=RETRIEVAL_K` (25) ไม่มี filter ไม่มีเกณฑ์คะแนน | `themes/base.py:114-126` |
| 3. Sparse | BM25 top-25 โดยตัดเอกสารที่คะแนน `<= 0` ทิ้ง | `themes/base.py:128-144` |
| 4. รวมผล | Weighted RRF, `k_rrf = 60` **ฝังตายตัว** — `(1/(60+rank+1)) * weight` | `themes/base.py:146-162` |
| 5. Rerank | `BAAI/bge-reranker-v2-m3` CrossEncoder ให้คะแนน **ทั้ง 25 รายการ** | `themes/base.py:188-196` |
| 6. กรอง | ตัดที่ต่ำกว่า `RERANK_SCORE_THRESHOLD` (0.0) · **ถ้าไม่เหลือเลย ให้เก็บอันดับ 1 ไว้** | `themes/base.py:212-219` |
| 7. ตัดจำนวน | `[:limit]` — ใช้ `limit` ที่ผู้เรียกส่งมา หรือ `RERANK_TOP_K` ถ้า `limit == 0` | `themes/base.py:221` |

> คะแนนของ BGE cross-encoder เป็น **logit ดิบและติดลบได้บ่อย** ดังนั้นเกณฑ์เริ่มต้น `0.0` ตัดทิ้งไปเยอะพอสมควรอยู่แล้ว ตั้งเป็น `-10` เพื่อปิดการกรองโดยปริยาย

**สิ่งที่ยังไม่ได้ทำ:** MMR/diversity, metadata filter, การ normalize คะแนน, query rewriting/HyDE, parent-document retrieval, sparse vector แบบ native ของ Qdrant, multi-query fusion

**ข้อควรระวังเรื่อง BM25:** index อยู่ในโปรเซสและสร้างตอนเริ่มระบบ การแก้ไข Qdrant นอกช่องทางปกติ (สคริปต์บำรุงรักษา หรือเรียก REST ตรง) จะทำให้ index ฝั่ง sparse ของ server ที่กำลังรัน **ล้าสมัยจนกว่าจะ restart**

**การนำเข้าเอกสาร**

- **PDF** → ทั้งไฟล์ถูกเข้ารหัส base64 เป็น data URL แล้วส่งไป OpenRouter → `google/gemini-2.5-flash` ที่ `temperature=0.1` พร้อม JSON schema แบบเข้มงวด `{pages: [{page_number, markdown_content}]}` prompt (`utils/prompt.py:1-12`) สั่งให้ถอดความเป็น markdown ทีละหน้า พร้อมใส่ placeholder `[IMAGE: <ชื่อ>]` สำหรับรูปภาพ ระบบติดตาม offset ของแต่ละหน้า ทำให้ chunk ที่คร่อมหน้าได้ค่า `"[3,4]"`
- **ไฟล์อื่น ๆ** → `bytes.decode("utf-8", errors="ignore")` และทุก chunk ได้ `"page": "[1,1]"`
- ทั้งสองเส้นทางใช้ `RecursiveCharacterTextSplitter(chunk_size=550, chunk_overlap=90)`

> **`.csv`, `.docx`, `.xlsx` ไม่ถูกแปลงอย่างถูกต้อง** ไฟล์เหล่านี้ตกไปเส้นทาง plain-text และถูก decode เป็น UTF-8 จาก byte ดิบ ทำให้ได้ chunk ที่เป็นขยะ ไม่มีเส้นทาง OCR และไม่รองรับการนำเข้ารูปภาพ **รองรับเฉพาะ PDF และ plain text (`.txt`, `.md`) เท่านั้น**

### 4.4 `postgres` (build จาก `services/sql_data`)

`backend/services/sql_data/` **ไม่ใช่ service** แต่เป็น build context ของ Docker ที่มี 3 ไฟล์ ซึ่งสร้าง image `postgres:16-alpine` ที่โหลดข้อมูลคำร้องไว้ล่วงหน้า

```dockerfile
FROM postgres:16-alpine
COPY services/sql_data/init.sql /docker-entrypoint-initdb.d/10-init.sql
COPY services/sql_data/dump.csv /docker-entrypoint-initdb.d/dump.csv
```

พาธอ้างอิงจาก `backend/` เพราะ build context ใน compose คือ `.`

**Schema** (`init.sql` ทั้งไฟล์)

```sql
CREATE TABLE IF NOT EXISTS issue_logs (
    code VARCHAR(50) NOT NULL,
    issue_id INTEGER,
    "user" INTEGER,
    status VARCHAR(100),
    process_level VARCHAR(100),
    updated_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_issue_logs_code ON issue_logs (code);

COPY issue_logs(code, issue_id, "user", status, process_level, updated_date)
FROM '/docker-entrypoint-initdb.d/dump.csv'
WITH (FORMAT csv, HEADER true);
```

- `"user"` ต้องใส่ **เครื่องหมายคำพูดคู่เสมอ** เพราะเป็นคำสงวน เก็บ *staff id* ของเจ้าของคำร้อง และเชื่อมโยงเชิงตรรกะ (แต่ไม่มี FK) กับ `auth_users.staff_id`
- **ไม่มี primary key ไม่มี unique constraint ไม่มี foreign key** `issue_logs` เป็น event log แบบเพิ่มอย่างเดียว — หนึ่งแถวต่อการเปลี่ยนสถานะหนึ่งครั้ง หนึ่ง `code` มีได้หลายแถว

**ข้อมูลตั้งต้น** (`dump.csv`) — 39 แถว, รหัสคำร้อง 12 รหัส, เจ้าหน้าที่ 8 คน

| ฟิลด์ | ค่า |
|---|---|
| รหัส | `SKN-2568-1001/1002`, `SKN-2567-0001/0003/0004/0006`, `SKN-2569-0001/0002`, `BKK-2569-0001/0002`, `UTH-2569-0001/0002` |
| Staff id | `24501`, `13266`, `30001`, `30002`, `31001`, `31002`, `32001`, `32002` |
| สถานะ | `รอคัดกรอง`, `รับเรื่อง`, `กำลังดำเนินการ`, `กำลังช่วยเหลือ`, `จบคำร้อง`, `ลบ`, `ส่งต่อ` |
| ระดับดำเนินการ | `ผู้ใหญ่บ้าน`, `อปท.`, `อำเภอ`, `จังหวัด` |

> ⚠️ **`/docker-entrypoint-initdb.d/*` จะทำงานก็ต่อเมื่อ data directory ว่างเปล่าเท่านั้น** repo นี้มี cluster ที่มีข้อมูลอยู่แล้วที่ `backend/data/postgres_data/` ดังนั้น `docker compose up` จะ **ไม่** โหลดข้อมูลใหม่ ถ้าต้องการบังคับให้โหลดใหม่: `docker compose down` → ลบ `backend/data/postgres_data` → `docker compose up --build postgres`

**มีอีก 2 ตารางอยู่ในฐานข้อมูลเดียวกัน** ซึ่ง api-gateway สร้างตอนรันไทม์ (ไม่ได้อยู่ใน `init.sql`) คือ `auth_users` และ `chat_messages` ดู [§5](#5-ที่เก็บข้อมูล--อะไรอยู่ที่ไหน)

### 4.5 Frontend

`Frontend/web/`

| คุณสมบัติ | ค่า |
|---|---|
| Stack | React 19, TypeScript 5.9 (strict), Vite 7, Tailwind v4 (ไม่มีไฟล์ config — ใช้ CSS `@theme inline`) |
| State | **ไม่มี** Redux/Zustand/TanStack Query — ใช้ React Context 2 ตัว + custom hook 1 ตัว |
| Router | react-router-dom 7, `BrowserRouter` |
| Markdown | react-markdown + remark-gfm |
| Test | **ไม่มี** |
| พอร์ต dev | 5173 (ค่าเริ่มต้นของ Vite) |
| Docker | build ด้วย `node:20-alpine` → เสิร์ฟด้วย `nginx:alpine` พอร์ต 80 → host **3000** |

**เส้นทาง (Routes)** (`src/App.tsx:43-51`)

| เส้นทาง | Component | การป้องกัน |
|---|---|---|
| `/` | `ChatPage` → `MobileView` / `DesktopView` ที่จุดตัด 768px | สาธารณะ |
| `/login` | `LoginPage` | สาธารณะ |
| `/admin/files` | `AdminFilesPage` | ป้องกัน **ภายใน component** ไม่ใช่ด้วย route wrapper |

**ไม่มี catch-all route `*`** — URL ที่ไม่รู้จักจะแสดงหน้าว่าง

**การเรียกเครือข่ายทั้งหมดอยู่ในไฟล์เดียว: `src/services/api.ts`** ไม่มี component หรือ hook ใดเรียก `fetch` โดยตรง ไม่มี axios ไม่มี interceptor ไม่มี query client

**คีย์ใน localStorage**

| คีย์ | เนื้อหา |
|---|---|
| `phonphai_token` | JWT ดิบ |
| `phonphai_user` | `JSON.stringify(AuthUser)` |
| `phonphai_session_id:<user_id>` หรือ `:anonymous` | UUID v4 |
| `phonphai_messages:<user_id>` หรือ `:anonymous` | อาร์เรย์ข้อความ (ไม่รวมฟองกำลังคิด/กำลังสตรีม) |

> `README.md` ของ Frontend ระบุสองคีย์หลังไว้เป็น `phonphai_session_id` / `phonphai_messages` เฉย ๆ ซึ่ง **ล้าสมัยแล้ว** — โค้ดจริงแยก namespace ตามผู้ใช้

**ผู้ใช้ทำอะไรได้บ้าง**

- **แชท** (`/`) — ส่งข้อความ รับคำตอบแบบสตรีม ล้างแชท ใช้งานแบบไม่ล็อกอินได้ แต่ถ้าพิมพ์รหัสคำร้องขณะไม่ล็อกอิน ระบบจะเปิด modal ให้เข้าสู่ระบบแทนการส่ง มีการ์ดแนะนำ 4 ใบบนเดสก์ท็อป แสดงเฉพาะตอนยังไม่เริ่มสนทนา ชิปตอบด่วนเปลี่ยนตามบทบาท (ผู้ที่ล็อกอินแล้วได้ชิปเรื่องคำร้อง ผู้ที่ไม่ล็อกอินได้ชิปเรื่องคู่มือ)
- **สลับภาษา** — ไทย/อังกฤษ **ไม่ถูกบันทึก** — รีเซ็ตกลับเป็นภาษาไทยทุกครั้งที่โหลดหน้าใหม่
- **เข้าสู่ระบบ** (`/login`) — มีเพียงชื่อผู้ใช้และรหัสผ่าน **ไม่มีหน้าสมัครสมาชิก และไม่มีการรีเซ็ตรหัสผ่าน** การสร้างบัญชีทำได้ผ่าน API ฝั่ง admin เท่านั้น
- **จัดการข้อมูล** (`/admin/files` เฉพาะ admin) — อัปโหลดไฟล์พร้อมเลือกหมวด ดูรายการไฟล์ ลบไฟล์ ใช้ `<input type="file">` แบบพื้นฐาน ไม่มี drag-and-drop ไม่มีตัวกรองชนิดไฟล์ ไม่ตรวจขนาด ไม่มีแถบความคืบหน้า การลบใช้ `window.confirm` / `window.alert`

> **Admin เข้า `/admin/files` จากมือถือไม่ได้** เพราะลิงก์อยู่ในแถบข้างของเดสก์ท็อปเท่านั้น ต้องพิมพ์ URL เอง

**เมนูแถบข้าง 4 รายการเป็นแค่ placeholder** (Dashboard, Chat, Incident Map, Profile) — `onClick` เพียงปิดแผงเท่านั้น

---

## 5. ที่เก็บข้อมูล — อะไรอยู่ที่ไหน

```mermaid
graph LR
    subgraph pg["PostgreSQL :5432 — db: phonphai"]
        T1["issue_logs<br/>คำร้อง Remedy (โหลดไว้ล่วงหน้า)"]
        T2["auth_users<br/>เฉพาะเมื่อ USER_DB_BACKEND=postgres"]
        T3["chat_messages<br/>เฉพาะเมื่อ CHAT_HISTORY_BACKEND=postgres"]
    end
    subgraph mg["MongoDB :27017 — db: rag_db"]
        C1["users<br/>ที่เก็บบัญชีเริ่มต้น"]
        C2["chat_messages<br/>ที่เก็บประวัติเริ่มต้น"]
        C3["files<br/>metadata ของไฟล์ (ไม่เก็บ byte)"]
    end
    subgraph qd["Qdrant :6333"]
        V1["collection: manual<br/>1024 มิติ cosine"]
        V2["collection: disaster<br/>1024 มิติ cosine"]
    end
```

### 5.1 PostgreSQL — `phonphai`

**`issue_logs`** — เป็นของ `services/sql_data` และถูกอ่านโดย agent ดู schema ที่ [§4.4](#44-postgres-build-จาก-servicessql_data)

**`auth_users`** — สร้างตอนรันไทม์โดย `PostgresUserStore.__init__` (`api-gateway/db/postgres.py:36-37`) เฉพาะเมื่อ `USER_DB_BACKEND=postgres` มีไฟล์ migration แยกอยู่ที่ `api-gateway/db/migrations/postgres_users.sql`

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS auth_users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username      TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin', 'user')),
  staff_id      INTEGER,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS auth_users_username_uniq ON auth_users (username);
```

ตั้งชื่อว่า `auth_users` ไม่ใช่ `users` โดยเจตนา เพื่อไม่ให้ชนกับ schema เดิมขององค์กร

**`chat_messages`** — สร้างโดย `PostgresChatHistoryStore.__init__` เฉพาะเมื่อ `CHAT_HISTORY_BACKEND=postgres`

```sql
CREATE TABLE IF NOT EXISTS chat_messages (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  TEXT NOT NULL,
  user_id     TEXT NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS chat_messages_session_idx ON chat_messages (session_id, created_at);
CREATE INDEX IF NOT EXISTS chat_messages_user_idx ON chat_messages (user_id);
```

> ⚠️ **มี 2 จุดที่ต้องระวัง** (1) `_CHAT_SCHEMA_SQL` ใช้ `gen_random_uuid()` แต่ **ไม่ได้สร้าง extension `pgcrypto` เอง** ดังนั้นการใช้ `CHAT_HISTORY_BACKEND=postgres` โดยไม่ตั้ง `USER_DB_BACKEND=postgres` บนฐานข้อมูลที่ไม่มี pgcrypto จะล้มเหลว (2) store ทั้งสองสร้างจาก **`POSTGRES_USER_DSN`** ซึ่งเป็นตัวแปรคนละตัวกับชุด `POSTGRES_*` ที่ agent ใช้กับคำร้อง ตารางเหล่านี้จึงไปอยู่ที่ใดก็ตามที่ DSN นั้นชี้ ซึ่งอาจไม่ใช่ `phonphai`

### 5.2 MongoDB — `rag_db`

| Collection | เจ้าของ | โครงสร้าง |
|---|---|---|
| `users` | api-gateway | `{username (unique idx), password_hash (bcrypt), role, staff_id, created_at}` โดย `user_id` = `str(_id)` เป็นสตริง hex 24 ตัว |
| `chat_messages` | api-gateway เขียน, agent อ่าน | `{session_id, user_id, role, content, created_at}` มี index บน `(session_id, created_at)` และ `user_id` |
| `files` | retriever | `{file_name, theme, content_type, size_bytes, created_at}` |

> **Mongo ไม่เก็บ byte ของไฟล์ต้นฉบับ** `retriever/db/mongo.py:16-17` ระบุชัดว่า *"Saves file metadata without storing raw bytes in MongoDB."* ข้อความใน README เดิมที่ root นั้นผิด ดูคำเตือนเรื่องการสำรองข้อมูลที่ [§11.4](#114-สำรองและกู้คืนข้อมูล)

### 5.3 Qdrant

มี 2 collection คือ `manual` และ `disaster` ตั้งชื่อตาม `theme_name.lower()` **ไม่มี collection ชื่อ `remedy`**

| การตั้งค่า | ค่า |
|---|---|
| มิติ | **1024** — ตรวจสอบตอนรันไทม์ ไม่ได้ฝังตายตัว |
| ระยะทาง | Cosine |
| Named vector | ไม่มี (vector เดี่ยวไม่มีชื่อ) |
| HNSW | ค่าเริ่มต้นของ Qdrant: `m=16`, `ef_construct=100`, `full_scan_threshold=10000` |
| การเก็บ payload | `on_disk_payload: true` |
| Shard / replica | 1 / 1 |
| Quantization | ไม่มี |
| Payload index | **ไม่ได้สร้างไว้เลย** |

**Point ID เป็นแบบกำหนดได้แน่นอน** — `uuid5(NAMESPACE, "{collection}:{filename}_chunk_{i}")` ดังนั้นการอัปโหลดไฟล์ชื่อเดิมซ้ำจะ **เขียนทับ** ไม่ใช่สร้างซ้ำ

**โครงสร้าง payload ต่อ point**

| คีย์ | ค่า |
|---|---|
| `content` | ตัวข้อความของ chunk — **เป็นสำเนาเดียวของเอกสารที่แปลงแล้ว** |
| `doc_id` | `"{filename}_chunk_{i}"` |
| `source` | ชื่อไฟล์ต้นฉบับ (เขียนทับเสมอ) |
| `theme` | `"manual"` \| `"disaster"` |
| `page` | `"[start,end]"` หรือ `"[1,1]"` สำหรับ plain text |
| `rechunked`, `parent_doc_id`, `chunk_part` | เฉพาะ point ที่เกิดจาก `rechunk_collection.py` |

> ฟิลด์ `theme` ใน payload ถูกเขียนไว้แต่ **ไม่เคยถูกนำมา query** การแยกข้อมูลอาศัย collection ล้วน ๆ — `search()` ไม่ส่ง `query_filter` เลย

### 5.4 ไดเรกทอรีบนเครื่อง

ทั้งหมดเป็น bind mount และถูกกันออกจาก Docker build ด้วย `.dockerignore`

| พาธ | เจ้าของ |
|---|---|
| `backend/data/postgres_data/` | postgres |
| `backend/data/mongo_data/` | mongo |
| `backend/data/qdrant_data/` | qdrant |
| `backend/data/chroma_data/` | **ไม่ได้ใช้แล้ว — ไม่มีโค้ดอ้างอิง ลบได้** |

ลบไดเรกทอรีเพื่อรีเซ็ตสถานะของที่เก็บนั้น ๆ

---

## 6. คู่มือการตั้งค่า (Configuration)

**ทั้งสาม Python service ใช้ `pydantic-settings`** ชื่อ field *คือ* ชื่อตัวแปรสภาพแวดล้อม การค้นหาไม่สนตัวพิมพ์เล็กใหญ่ และ `get_settings()` ถูกครอบด้วย `@lru_cache()` — **การเปลี่ยนตัวแปรใด ๆ ต้อง restart container เสมอ**

ลำดับความสำคัญ: ตัวแปรระบบปฏิบัติการ > ไฟล์ `.env` > ค่าเริ่มต้นในโค้ด

> `.env` ถูกอ้างอิงจาก CWD ของโปรเซส (`/app` ใน container) และ `backend/.dockerignore` กัน `.env` ออกจาก build context **ดังนั้นภายใน Docker การตั้งค่าทั้งหมดมาจาก `docker-compose.yml`** ส่วน `backend/.env` ที่ root ถูกใช้เพียงเพื่อการแทนค่า `${VAR}` ของ compose และสำหรับสคริปต์ที่รันบนเครื่องโดยตรง

### 6.0 Secret — `backend/.env`

```env
OPENROUTER_API_KEY=
LANGCHAIN_API_KEY=

> ### 🔴 คำเตือนด้านความปลอดภัย
>
> **ค่าข้างต้นคือ key จริงที่อยู่ใน `backend/.env` ปัจจุบัน นำมาแสดงตามที่เจ้าของโครงการร้องขอโดยตรง**
>
> `backend/.env` ถูก gitignore ไว้อย่างถูกต้อง — **แต่เอกสารฉบับนี้ไม่ได้ถูก ignore** การ commit `ARCHITECTURE_TH.md` จะทำให้ key ทั้งสองเข้าไปอยู่ในประวัติ git ซึ่งการลบทีหลัง **ไม่ได้** ทำให้มันหายไป
>
> **สิ่งที่ควรทำ**
> 1. **เปลี่ยน key ทั้งสอง** ที่ [openrouter.ai/keys](https://openrouter.ai/keys) และ [smith.langchain.com](https://smith.langchain.com/) ก่อนที่ไฟล์นี้จะไปอยู่ใน repo ที่แชร์หรือเป็นสาธารณะ
> 2. แทนที่บล็อกนี้ด้วย placeholder (`sk-or-v1-<your-key>`) และเก็บค่าจริงไว้ใน `.env` เท่านั้น
> 3. หาก repo เป็นสาธารณะอยู่แล้ว ให้ถือว่า key ทั้งสองรั่วไหลแล้ว — key ของ OpenRouter มีความเสี่ยงเรื่องค่าใช้จ่ายโดยตรง

### 6.1 `api-gateway`

`backend/services/api-gateway/config.py`

| ตัวแปร | ค่าเริ่มต้น | ค่าใน compose | ควบคุมอะไร |
|---|---|---|---|
| `APP_NAME` | `"Phonphai API Gateway"` | — | **ไม่มีผล** — ประกาศไว้แต่ไม่เคยถูกใช้ |
| `CHUNK_SIZE` | `65536` (64 KB) | — | **ขนาด frame ของ gRPC ตอนอัปโหลด** ไม่เกี่ยวกับ chunk ข้อความ 550 ตัวอักษรของ retriever |
| `RETRIEVER_HOST` | `retriever:50051` | เหมือนกัน | ปลายทาง gRPC ของ retriever |
| `AGENT_HOST` | `agent:50052` | เหมือนกัน | ปลายทาง gRPC ของ agent |
| `USER_DB_BACKEND` | `mongo` | `${USER_DB_BACKEND:-mongo}` | `mongo` \| `postgres` ค่าอื่น → `ValueError` ตอนเริ่มระบบ |
| `MONGO_URI` | `mongodb://mongo:27017` | เหมือนกัน | จำเป็นถ้ามี backend ใดเป็น `mongo` |
| `MONGO_DB` | `rag_db` | เหมือนกัน | จำเป็นถ้ามี backend ใดเป็น `mongo` |
| `POSTGRES_USER_DSN` | `""` | `${POSTGRES_USER_DSN:-}` | **จำเป็น** ถ้ามี backend ใดเป็น `postgres` ค่าว่างจะโยน `ValueError` |
| `CHAT_HISTORY_ENABLED` | `False` | **ไม่ได้ตั้ง → ปิด** | สวิตช์หลักของการบันทึกประวัติ และ `DELETE /api/v1/chat/history` |
| `CHAT_HISTORY_BACKEND` | `mongo` | — | `mongo` \| `postgres` |
| `CHAT_HISTORY_WINDOW` | `10` | — | **ไม่มีผลที่นี่** — ใช้แค่ในบรรทัด log |
| `JWT_SECRET` | `"change-me-in-production"` | `${JWT_SECRET:-please-change-me}` | คีย์เซ็น HMAC **ค่าเริ่มต้นทั้งสองไม่ปลอดภัยและไม่มีการตรวจสอบ** |
| `JWT_ALGORITHM` | `HS256` | `HS256` | อัลกอริทึมเซ็นและตรวจสอบ |
| `JWT_EXPIRES_HOURS` | `168` (7 วัน) | `168` | อายุ token |
| `INITIAL_ADMIN_USERNAME` | `""` | `${...:-admin}` | สร้าง admin เริ่มต้น เฉพาะเมื่อยังไม่มี admin |
| `INITIAL_ADMIN_PASSWORD` | `""` | `${...:-a1234567}` | " |
| `INITIAL_USER_USERNAME` | `""` | `${...:-user}` | สร้างผู้ใช้ทั่วไปเริ่มต้น |
| `INITIAL_USER_PASSWORD` | `""` | `${...:-a1234567}` | " |
| `INITIAL_USER_STAFF_ID` | `0` | `${...:-13266}` | **ต้องมากกว่า 0** ไม่เช่นนั้นจะข้ามการสร้างผู้ใช้ |

`ANONYMIZED_TELEMETRY=False` ถูกตั้งไว้ใน compose แต่ **ไม่ได้ประกาศเป็น field** จึงไม่มีผล

### 6.2 `agent`

`backend/services/agent/config.py`

| ตัวแปร | ค่าเริ่มต้น | compose | ควบคุมอะไร |
|---|---|---|---|
| `OPENROUTER_API_KEY` | **ไม่มี** | `${OPENROUTER_API_KEY}` | **จำเป็น** — service พังตั้งแต่ import ถ้าไม่มี |
| `PORT` | `50052` | — | พอร์ต gRPC |
| `APP_NAME` | `"Phonphai Agent Service"` | — | คำนำหน้าใน log |
| `MAX_TOOL_CALL_ROUNDS` | `3` | `3` | จำนวนรอบสูงสุดของ agent↔tools ก่อนบังคับตอบโดยไม่ใช้ tool |
| `RETRIEVER_HOST` | `retriever:50051` | เหมือนกัน | ปลายทาง gRPC ของ retriever |
| `RETRIEVER_SEARCH_LIMIT` | `8` | `8` | `SearchRequest.limit` สำหรับ **Manual** |
| `DISASTER_RETRIEVER_SEARCH_LIMIT` | `4` | `4` | `SearchRequest.limit` สำหรับ **Disaster** |
| `DISASTER_EXCERPT_MAX_CHARS` | `900` | `900` | จำกัดความยาวข้อความต่อ chunk หมวดภัยพิบัติ (หมวดอื่น**ฝังตายตัวที่ 1800**) |
| `DISASTER_CONCISE_REWRITE_ENABLED` | `True` | `true` | เรียก LLM เพิ่มเพื่อบีบอัดคำตอบภัยพิบัติ |
| `POSTGRES_HOST` | `postgres` | `postgres` | ฐานข้อมูลคำร้อง |
| `POSTGRES_PORT` | `5432` | `5432` | " |
| `POSTGRES_DB` | `phonphai` | `phonphai` | " |
| `POSTGRES_USER` | `phonphai` | `phonphai` | " |
| `POSTGRES_PASSWORD` | `phonphai` | `phonphai` | **ค่าเริ่มต้นเป็นข้อความธรรมดา — ต้องเปลี่ยนก่อนใช้จริง** |
| `POSTGRES_CHAT_DSN` | `""` | — | แทนที่ DSN ที่ประกอบขึ้นสำหรับประวัติการสนทนา |
| `MONGO_URI` | `mongodb://mongo:27017` | — | ประวัติการสนทนา ถ้า backend = mongo |
| `MONGO_DB` | `rag_db` | — | " |
| `CHAT_HISTORY_ENABLED` | `False` | **ไม่ได้ตั้ง → ปิด** | ควบคุมด้วยว่าจะผูก `load_conversation_history` เข้ากับโมเดลหรือไม่ |
| `CHAT_HISTORY_BACKEND` | `mongo` | — | `mongo` \| `postgres` |
| `CHAT_HISTORY_WINDOW` | `10` | — | **ไม่ถูกบังคับใช้** — ค่าจริงที่ใช้คือ `min(max(turns,1),20)` |
| `LANGCHAIN_TRACING_V2` | `"true"` | `true` | LangSmith tracing **เปิดเป็นค่าเริ่มต้น** |
| `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | เหมือนกัน | |
| `LANGCHAIN_API_KEY` | `""` | `${LANGCHAIN_API_KEY}` | |
| `LANGCHAIN_PROJECT` | `phonphai-agent` | เหมือนกัน | |

**สิ่งที่ตั้งผ่านตัวแปรสภาพแวดล้อมไม่ได้:** ชื่อโมเดล `google/gemini-2.5-flash`, `temperature=0` และ base URL ของ OpenRouter ล้วน **ฝังตายตัว** ใน `core/graph.py:42-50` ดู [§10.4](#104-เปลี่ยนโมเดล-llm-หรือผู้ให้บริการ)

### 6.3 `retriever`

`backend/services/retriever/config.py`

| ตัวแปร | ค่าเริ่มต้น | compose | ควบคุมอะไร |
|---|---|---|---|
| `APP_NAME` | `"Phonphai Retriever Service"` | — | log ตอนเริ่ม |
| `PORT` | `50051` | — | พอร์ต gRPC |
| `APP_URL` | `https://github.com/PhonphaiChatbot` | — | header `HTTP-Referer` ที่ส่งไป OpenRouter |
| `MONGO_URI` | `mongodb://mongo:27017` | เหมือนกัน | ⚠️ **`db/mongo.py:11` ข้าม Settings ทั้งหมด** — ใช้ `os.getenv("MONGO_URI", "mongodb://localhost:27017")` ซึ่งมีค่าเริ่มต้น*คนละค่า* |
| `QDRANT_HOST` | `qdrant` | `qdrant` | โฮสต์ของ vector DB |
| `QDRANT_PORT` | `6333` | `6333` | พอร์ต REST (`prefer_grpc=False`) |
| `EMBEDDING_MODEL_NAME` | `intfloat/multilingual-e5-large` | เหมือนกัน | และใช้ตรวจจับ E5 prefix อัตโนมัติด้วย |
| `RERANK_MODEL_NAME` | `BAAI/bge-reranker-v2-m3` | เหมือนกัน | โมเดล CrossEncoder |
| `RERANK_DEVICE` | `auto` | **ไม่ได้ตั้ง** | `auto` \| `cpu` \| `cuda` — ใช้กับ reranker เท่านั้น |
| `HYBRID_SEMANTIC_WEIGHT` | `0.6` | `0.6` | น้ำหนัก RRF ฝั่ง dense |
| `HYBRID_BM25_WEIGHT` | `0.4` | `0.4` | น้ำหนัก RRF ฝั่ง sparse (ไม่ normalize อัตโนมัติ) |
| `RETRIEVAL_K` | `25` | `25` | จำนวนผู้เข้าชิงต่อวิธีค้นหา **และ** ขนาด batch ของ rerank — เป็นตัวกำหนด latency หลัก |
| `RERANK_TOP_K` | `5` | **`10`** ⚠️ | จำนวนผลสุดท้าย — **เฉพาะเมื่อผู้เรียกส่ง `limit=0`** ดูคำเตือนด้านล่าง |
| `RERANK_SCORE_THRESHOLD` | `0.0` | `0.0` | คะแนน logit ขั้นต่ำจาก cross-encoder |
| `CHUNK_SIZE` | `550` | `550` | ขนาด chunk เป็น **จำนวนตัวอักษร** (ใช้ตอนนำเข้าเท่านั้น) |
| `CHUNK_OVERLAP` | `90` | `90` | ส่วนซ้อนทับ (ใช้ตอนนำเข้าเท่านั้น) |
| `OPENROUTER_API_KEY` | `""` | `${OPENROUTER_API_KEY}` | **จำเป็นสำหรับการนำเข้า PDF** — ค่าว่างจะโยน `ValueError` แต่การค้นหายังทำงานได้โดยไม่มี key |
| `LANGCHAIN_*` | ดูที่ agent | เหมือนกัน | project คือ `phonphai-phaser` |
| `RETRIEVER_RERANKER_SCOPE` | `shared` | — | `shared` \| `thread` อ่านผ่าน `os.environ` **ไม่ใช่** field ของ Settings |
| `HF_HOME` | `/root/.cache/huggingface` | Dockerfile | ที่เก็บ cache ของโมเดล |

> ### ⚠️ `RERANK_TOP_K` ไม่มีผลใด ๆ ในการใช้งานจริง
>
> agent ซึ่งเป็นผู้เรียกเพียงรายเดียวในระบบจริง **ส่ง `limit` มาอย่างชัดเจนเสมอ** (8 สำหรับ Manual, 4 สำหรับ Disaster) โดย `themes/base.py:207` จะถอยไปใช้ `RERANK_TOP_K` เฉพาะเมื่อ `limit == 0` เท่านั้น **การปรับ `RERANK_TOP_K` จึงไม่ส่งผลต่อทราฟฟิกจริง** ให้ไปแก้ `RETRIEVER_SEARCH_LIMIT` / `DISASTER_RETRIEVER_SEARCH_LIMIT` ที่ฝั่ง *agent* แทน (และสังเกตว่าค่าเริ่มต้นในโค้ดคือ `5` ซึ่งไม่ตรงกับค่าใน compose ที่เป็น `10`)

**ค่าที่ฝังตายตัว ปรับผ่าน config ไม่ได้**

| ค่า | ตัวเลข | ตำแหน่ง |
|---|---|---|
| ค่าปรับเรียบของ RRF (`k_rrf`) | 60 | `themes/base.py:148` |
| คะแนน BM25 ขั้นต่ำ | `> 0` | `themes/base.py:136` |
| ความยาวข้อความสูงสุดหมวดที่ไม่ใช่ภัยพิบัติ | 1800 ตัวอักษร | `agent/tools/retriever_tool.py:120` |
| ขนาดหน้าตอน scroll | 256 | `db/qdrant.py:178` |
| อุปกรณ์ที่ใช้ทำ embedding | `"cpu"` | `db/qdrant.py:40` |
| ขนาด/ความหน่วงของ stream | 2 ตัวอักษร / 25 ms | `agent/server.py:175-184` |
| ช่วงจำกัดจำนวนเทิร์นประวัติ | `[1, 20]` | `agent/tools/chat_history_tool.py:24` |

### 6.4 Frontend

มีการอ่าน `import.meta.env` เพียง **2 จุด**

| ตัวแปร | file:line | ค่าเริ่มต้น | ควบคุมอะไร |
|---|---|---|---|
| `VITE_API_URL` | `src/services/api.ts:3` | `http://localhost:8080` | Base URL ของทั้ง 8 endpoint **ถูกฝังลงบันเดิลตอน build** |
| `VITE_MOCK_THINKING_MS` | `src/hooks/useChatManager.ts:12` | `0` (ปิด) | **โหมดจำลองแบบออฟไลน์** — เมื่อ `> 0` จะข้ามการเรียกเครือข่ายทั้งหมดและปลอม stream ที่ 60 ms ต่อคำ ไม่มีเอกสารระบุไว้ แต่มีประโยชน์มากสำหรับงาน UI ที่ไม่ต้องรัน backend |

> **ไม่มีไฟล์ `.env` ใด ๆ อยู่ใน `Frontend/web`** ทั้งที่ `README.md` ของ Frontend บอกให้ `cp .env.example .env` แต่ **ไฟล์นั้นไม่มีอยู่จริง** ต้องสร้างเองด้วยมือ
> ```env
> VITE_API_URL=http://localhost:8080
> ```

> **ข้อควรระวังเรื่องค่าว่าง:** `api.ts:3` ใช้ `??` (nullish coalescing) การตั้ง `VITE_API_URL=""` จะได้ `""` ซึ่ง *ไม่ใช่* nullish ค่าเริ่มต้นจึง**ไม่**ทำงาน และทุก URL จะกลายเป็นพาธสัมพัทธ์บนโดเมนเดียวกัน (`/api/v1/...`) ซึ่งบังเอิญใช้งานได้เมื่ออยู่หลัง reverse proxy โดเมนเดียวกัน แต่เป็นผลข้างเคียงของโค้ด ไม่ใช่ฟีเจอร์ที่ตั้งใจออกแบบ

---

## 7. REST API Reference

**Base URL:** `http://localhost:8080`
**เอกสารแบบโต้ตอบ:** `/docs` · **OpenAPI:** `/openapi.json`

### 7.1 ข้อตกลงร่วม

- **การยืนยันตัวตน:** `Authorization: Bearer <jwt>` ไม่ใช้ cookie และ `allow_credentials` เป็น `False`
- **ข้อผิดพลาด:** `{"detail": "<ข้อความ>"}` ส่วนข้อผิดพลาดจากการตรวจสอบของ Pydantic คืนค่า **422** มาตรฐานของ FastAPI ในรูป `{"detail": [{"loc": [...], "msg": ..., "type": ...}]}`
- **เครื่องหมาย `/` ท้าย path สำคัญมาก** `/api/v1/chat/` และ `/api/v1/files/` ประกาศไว้พร้อม `/` ท้าย การเรียกโดยไม่ใส่จะได้ **307 Temporary Redirect** ซึ่ง client ที่ไม่ใช่เบราว์เซอร์และไม่ส่ง body ซ้ำตอน 307 จะพัง **ให้ใช้รูปแบบที่มี `/` ท้ายเสมอ**

### 7.2 CORS — อุปสรรคอันดับ 1 ในการเชื่อมต่อ

```python
# api-gateway/main.py:110-115
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

- **Origin ฝังตายตัวในซอร์สโค้ด ไม่มีตัวแปรสภาพแวดล้อม** การ deploy เบราว์เซอร์จากโฮสต์ พอร์ต หรือ scheme อื่น (รวมถึง `https://`) **ต้องแก้โค้ด** ดู [§10.12](#1012-เปลี่ยน-cors-origins)
- `PUT` และ `PATCH` จะถูกปฏิเสธตอน preflight
- Header ที่กำหนดเอง (เช่น `X-Request-Id`) จะไม่ผ่าน preflight
- ไม่ได้ตั้ง `expose_headers` — JavaScript อ่านได้เฉพาะ header ที่อยู่ใน safelist ของ CORS
- ไม่ได้ตั้ง `max_age` → ใช้ค่าเริ่มต้น 600 วินาทีของ Starlette

**ไม่มี middleware อื่นเลย** — ไม่มี GZip ไม่มี TrustedHost ไม่มี request ID และ **ไม่มี rate limiting ที่ใดเลย**

### 7.3 ตาราง Endpoint

| # | Method | Path | สิทธิ์ | สำเร็จ |
|---|---|---|---|---|
| 1 | POST | `/api/v1/auth/login` | — | 200 |
| 2 | GET | `/api/v1/auth/me` | Bearer | 200 |
| 3 | POST | `/api/v1/auth/users` | **Admin** | **201** |
| 4 | POST | `/api/v1/chat/` | ไม่บังคับ | 200 |
| 5 | POST | `/api/v1/chat/stream` | ไม่บังคับ | 200 (SSE) |
| 6 | DELETE | `/api/v1/chat/history` | Bearer | **204** |
| 7 | POST | `/api/v1/files/upload` | **Admin** | 200 |
| 8 | GET | `/api/v1/files/` | **Admin** | 200 |
| 9 | DELETE | `/api/v1/files/{file_id}` | **Admin** | 200 |

---

### 1. `POST /api/v1/auth/login`

**Request**
```json
{ "username": "admin", "password": "a1234567" }
```

**200**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": { "user_id": "6839...", "username": "admin", "role": "admin", "staff_id": null }
}
```

**401** `{"detail": "Invalid username or password"}`

**Claim ใน JWT:** `sub` (user_id), `username`, `role`, `staff_id`, `iat`, `exp` ไม่มี `aud` ไม่มี `iss` ไม่มี `jti` ใช้ HS256 อายุ 168 ชั่วโมง **ไม่มี refresh token และไม่มีการเพิกถอน**

---

### 2. `GET /api/v1/auth/me`

คืนค่า `{user_id, username, role, staff_id}` **นี่เป็นวิธีเดียวในการตรวจสอบความถูกต้องของ token** ดูคำเตือนเรื่องหมดอายุที่ [§9.1](#91-เรียกใช้-rest-api)

---

### 3. `POST /api/v1/auth/users` — เฉพาะ admin

**Request**
```json
{ "username": "somchai", "password": "secret123", "role": "user", "staff_id": 13266 }
```

| ฟิลด์ | ข้อจำกัด |
|---|---|
| `username` | ความยาวอย่างน้อย 1 |
| `password` | **ความยาวอย่างน้อย 6** |
| `role` | ต้องตรงกับ `^(admin|user)$` |
| `staff_id` | `int` หรือ `null` — **จำเป็นในทางปฏิบัติสำหรับ `role: "user"`** เพราะเป็นตัวกำหนดว่าค้นคำร้องใดได้บ้าง |

**201** → `UserPublic` · **409** ถ้าชื่อผู้ใช้ซ้ำ

> การสร้างผู้ใช้ชื่อเดียวกันพร้อมกันไม่ได้ถูกจัดการ — โค้ดตรวจก่อนแล้วค่อย insert โดยไม่ดัก `DuplicateKeyError` / `UniqueViolation` ทำให้เกิด race แล้วออกมาเป็น **500**

---

### 4. `POST /api/v1/chat/` — ไม่สตรีม

**Request**
```json
{ "session_id": "any-client-uuid", "message": "วิธีขอชุดบรรเทาทุกข์" }
```

**200**
```json
{
  "session_id": "...",
  "response": "…",
  "sources": [{ "title": "User Manual.pdf", "theme": "Manual", "content": "…" }],
  "cost": 0.0000842
}
```

> ### ⚠️ `session_id` ถูกเขียนทับสำหรับผู้ใช้ที่ล็อกอิน
> ```python
> effective_session_id = user.user_id if user else request.session_id
> ```
> ผู้ใช้ที่ล็อกอินแล้วมี **เธรดสนทนาฝั่งเซิร์ฟเวอร์เพียงเธรดเดียว ผูกกับ user id ของตน** ไม่สามารถมีหลาย session ขนานกันได้ และการกด "แชทใหม่" ใน client ก็ไม่ได้สร้างที่เก็บประวัติใหม่ฝั่งเซิร์ฟเวอร์ มีเพียงผู้ใช้ที่ไม่ล็อกอินเท่านั้นที่ควบคุม `session_id` ของตนเองได้

> ### ⚠️ อาร์เรย์ `sources` ถูกใช้งานหลายวัตถุประสงค์
> agent ยัด metadata นอกช่องทางเข้าไปใน `sources` โดยใช้ค่า `theme` พิเศษ **ต้องกรองออกก่อนแสดงเป็นแหล่งอ้างอิง**
>
> | `theme` | ความหมาย |
> |---|---|
> | `Manual` / `Disaster` | แหล่งอ้างอิงจริง |
> | `__retrieved_chunk__` | chunk ดิบที่ค้นมาได้ ไม่ใช่แหล่งอ้างอิง |
> | `__meta__` (title `__selected_tools__`) | รายชื่อ tool ที่ agent เลือก คั่นด้วย `\|` |
> | `ticket_lookup` | `content` คือ `json.dumps(rows)` |
> | `ticket_list` | `content` คือ `json.dumps(codes)` |

**ด่านกันคำร้องสำหรับผู้ไม่ล็อกอิน — 401** ถ้าผู้เรียกไม่ได้ล็อกอิน **และ** ข้อความตรงกับ regex ใด ๆ ใน 4 รูปแบบ ระบบจะปฏิเสธด้วย `{"detail": "Login required to query Remedy tickets (PPP-XXXX-XXXX)."}`

| รูปแบบ | ตรงกับ |
|---|---|
| `\b[A-Z]{3}[-\s]?\d{4}[-\s]?\d{4}\b` (ไม่สนตัวพิมพ์) | `SKN-2567-0006`, `BKK 2569 0001` |
| `^\s*\d{4}\s*$` | ข้อความที่มีแค่ตัวเลข 4 หลัก |
| `^\s*25\d{2}[-\s/]?\d{4}\s*$` | `2569-0001` |
| `(?:ticket\|request\|คำร้อง\|หมายเลข).*\b\d{4}\b` (และแบบกลับด้าน) | "ticket 0006", "หมายเลข 1234" |

---

### 5. `POST /api/v1/chat/stream` — SSE

Request เหมือนข้อ 4 ตอบกลับเป็น `text/event-stream` พร้อม `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`

**รูปแบบข้อมูล:** `data: <compact-json>\n\n`

- **ไม่มีฟิลด์ `event:`** ไม่มี `id:` ไม่มี `retry:` ไม่มี keepalive comment ดังนั้น `EventSource` มาตรฐานจะเห็นทุก frame เป็น event `message` เริ่มต้น
- **ไม่มีสัญญาณ `[DONE]`** stream แค่จบไปเฉย ๆ **ให้ถือว่า `type: "done"` คือจุดสิ้นสุด**
- **สถานะ HTTP เป็น 200 ทันทีที่เริ่มสตรีม** ความล้มเหลวหลังจากนั้นจะมาในรูป frame `type: "error"` ไม่ใช่รหัสข้อผิดพลาด HTTP ส่วนการปฏิเสธสิทธิ์เกิดขึ้น*ก่อน*เริ่มสตรีม จึงเป็น 401 จริงพร้อม JSON body

**Frame 3 ชนิด**

```jsonc
{"type":"token","content":"ส"}                       // ครั้งละ 2 ตัวอักษร
{"type":"done","session_id":"…","response":"…","sources":[…],"cost":0.00008}
{"type":"error","message":"…"}
```

> **Streaming เป็นการจำลอง** ทุก frame มาถึง*หลัง*สร้างคำตอบเสร็จแล้ว ที่ 2 ตัวอักษร / 25 ms ดู [§3.3](#33-ข้อเท็จจริงสำคัญเชิงสถาปัตยกรรม)

**ตัวอย่างการรับข้อมูล** (นี่คือสิ่งที่ Frontend ที่มาพร้อมระบบทำ — ใช้ `EventSource` ไม่ได้เพราะคำขอต้องเป็น `POST` + มี body + มี header `Authorization`)

```js
const res = await fetch(`${API_URL}/api/v1/chat/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  body: JSON.stringify({ session_id: sessionId, message }),
});
if (!res.ok) throw new Error(`API error: ${res.status}`);

const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  // ต้องใส่ { stream: true } — ข้อความไทยเป็น multi-byte และถูกตัดคร่อม chunk ได้
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop() ?? '';          // เก็บบรรทัดสุดท้ายที่อาจยังไม่สมบูรณ์ไว้

  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;   // ทิ้งบรรทัดว่างที่คั่นแต่ละ frame
    const parsed = JSON.parse(line.slice(6));
    if (parsed.type === 'token')      appendToken(parsed.content);
    else if (parsed.type === 'done')  finish(parsed);
    else if (parsed.type === 'error') fail(parsed.message);
  }
}
```

---

### 6. `DELETE /api/v1/chat/history`

ลบข้อความที่บันทึกไว้ทั้งหมดของผู้ใช้ที่ล็อกอิน คืน **204 No Content**

**ตามค่าที่มาให้ จะคืน 404** `{"detail": "Chat history is not enabled."}` เพราะ `CHAT_HISTORY_ENABLED` ไม่ได้ตั้งไว้ใน `docker-compose.yml`

---

### 7. `POST /api/v1/files/upload` — เฉพาะ admin

`multipart/form-data`

| ฟิลด์ | ชนิด | จำเป็น |
|---|---|---|
| `file` | binary | ใช่ |
| `theme` | `remedy` \| `disaster` \| `manual` | ใช่ |

```bash
curl -X POST http://localhost:8080/api/v1/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./User Manual.pdf" \
  -F "theme=manual"
```

**200** `{"file_id": "6839...", "message": "…", "success": true}`

**ข้อจำกัด: ไม่มีเลย** ไม่จำกัดขนาด ไม่มี allowlist ของ MIME และ `await file.read()` ดึงไฟล์ทั้งไฟล์เข้าหน่วยความจำก่อนเริ่มสตรีม เป็นช่องทางทำให้หน่วยความจำหมดผ่าน endpoint ที่ต้องเป็น admin ควรตั้งขีดจำกัด body ที่ reverse proxy เมื่อใช้งานจริง

> ### ⚠️ รหัสข้อผิดพลาดใน router นี้ผิด
> `routers/files.py` ไม่มีคำสั่ง `except HTTPException: raise` แบบที่ `chat.py` มี ทำให้ **ข้อผิดพลาด 4xx ที่ตั้งใจทุกตัวถูกเขียนใหม่เป็น 500** พร้อมข้อความที่มีคำนำหน้า
> - หมวดไม่ถูกต้อง → `500 {"detail": "400: Invalid theme. Must be remedy, disaster, or manual."}`
> - retriever ล้มเหลว → `500 {"detail": "500: <ข้อความ>"}`
> - ลบไม่สำเร็จ → `500 {"detail": "400: <ข้อความ>"}`
>
> นอกจากนี้ `files.py:89` ส่งค่า `Ellipsis` ของ Python ตรง ๆ เป็น `detail=...` ซึ่งแปลงเป็น JSON ไม่ได้ ดังนั้นเมื่อ RPC ไปยัง retriever ล้มเหลว จะเกิด error ตอน render แทนที่จะได้ `502` ที่สะอาด **client ต้องอ่านคำนำหน้า `"NNN: "` ที่อยู่ใน `detail` แทนที่จะเชื่อสถานะ HTTP**

---

### 8. `GET /api/v1/files/` — เฉพาะ admin

```json
{
  "files": [
    { "file_id": "…", "file_name": "User Manual.pdf", "theme": "3",
      "created_at": "2026-05-01T09:10:00", "size_bytes": 2481920 }
  ]
}
```

> `theme` ที่นี่เป็น **ตัวเลข enum ในรูปสตริง** (`"1"`/`"2"`/`"3"`) ไม่ใช่ชื่อหมวด ซึ่งไม่สมมาตรกับ endpoint อัปโหลดที่รับ `"manual"`

---

### 9. `DELETE /api/v1/files/{file_id}` — เฉพาะ admin

**Query parameter ที่จำเป็น** (ต้องมีทั้งคู่ ไม่งั้นได้ 422)

| พารามิเตอร์ | หมายเหตุ |
|---|---|
| `filename` | ต้องตรงกับ payload `source` ใน Qdrant **แบบเป๊ะ ๆ** |
| `theme` | สตริงตัวพิมพ์เล็ก **ถูกส่งต่อโดยไม่ตรวจสอบและไม่แปลงรูป** ต่างจากตอนอัปโหลดที่มีการแปลงเป็นตัวพิมพ์เล็กและตรวจสมาชิก |

```bash
curl -X DELETE "http://localhost:8080/api/v1/files/6839...?filename=User%20Manual.pdf&theme=manual" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. gRPC / สัญญาการสื่อสารภายใน

มีไฟล์ proto 2 ไฟล์: `backend/protos/chatbot.proto` (package `agent`) และ `backend/protos/retriever.proto` (package `retriever`) ทั้งคู่เป็น `proto3` และไม่ใช้คีย์เวิร์ด `optional`

### 8.1 `agent.AgentService` — implement โดย `agent` เรียกโดย `api-gateway`

```protobuf
service AgentService {
  rpc Chat       (ChatRequest) returns (ChatResponse);
  rpc ChatStream (ChatRequest) returns (stream ChatStreamChunk);
}

message ChatRequest {
  string session_id   = 1;
  string user_message = 2;
  string user_role    = 3;   // "admin" | "user" | "" (ไม่ล็อกอิน)
  int32  staff_id     = 4;   // 0 == ไม่มี
  string username     = 5;   // ใช้เพื่อ log เท่านั้น
}

message ChatResponse {
  string          session_id = 1;
  string          ai_message = 2;
  repeated Source sources    = 3;
  double          cost       = 4;
}

message Source {
  string title   = 1;
  string theme   = 2;
  string content = 3;
}

message ChatStreamChunk {
  string session_id = 1;
  oneof payload {
    string       token          = 2;
    ChatResponse final_response = 3;
    string       error          = 4;
  }
}
```

> ### 🔐 `user_role` และ `staff_id` คือช่องทางกำหนดสิทธิ์
> agent **เชื่อฟิลด์เหล่านี้อย่างสมบูรณ์** เพราะเป็นตัวกำหนดขอบเขตการเข้าถึงคำร้อง client ใดก็ตามที่เข้าถึง `agent:50052` ได้โดยตรง สามารถตั้ง `user_role="admin"` แล้วอ่านคำร้องทุกรายการในฐานข้อมูลได้
>
> **agent ไม่มีระบบยืนยันตัวตนเป็นของตัวเอง** ความปลอดภัยของมันขึ้นอยู่กับการที่เข้าถึงไม่ได้จากภายนอกเครือข่าย Docker `rag_net` ทั้งหมด **ห้ามเปิดพอร์ต 50052 ออกสู่ภายนอกเด็ดขาด**

### 8.2 `retriever.RetrieverService` — implement โดย `retriever`

เรียกโดย **agent** (เฉพาะ `Search`) และ **api-gateway** (`UploadFile`, `ListFiles`, `DeleteFile`)

```protobuf
service RetrieverService {
  rpc Search     (SearchRequest)         returns (SearchResponse);
  rpc ListFiles  (ListFilesRequest)      returns (ListFilesResponse);
  rpc UploadFile (stream UploadFileRequest) returns (UploadFileResponse);
  rpc DeleteFile (DeleteFileRequest)     returns (DeleteFileResponse);
}

enum Theme {
  THEME_UNSPECIFIED = 0;
  REMEDY            = 1;   // ประกาศไว้ แต่ไม่มี handler สำหรับการค้นหา
  DISASTER          = 2;
  MANUAL            = 3;
}

message SearchRequest { string query = 1; Theme theme = 2; int32 limit = 3; }

message SearchResponse {
  message Result {
    string content   = 1;
    string file_name = 2;
    string page      = 3;   // "[start,end]" เป็น STRING ไม่ใช่ int
    float  score     = 4;   // logit ดิบจาก cross-encoder ติดลบได้
  }
  repeated Result results = 1;
}

message ListFilesRequest {}                    // ว่างโดยเจตนา → ดึงทุกหมวด
message FileInfo { string file_id=1; string file_name=2; string theme=3;
                   string created_at=4; int64 size_bytes=5; }
message ListFilesResponse { repeated FileInfo files = 1; }

message UploadFileRequest { oneof data { FileMetadata info = 1; bytes chunk_data = 2; } }
message FileMetadata { string file_name=1; Theme theme=2; string content_type=3; }
message UploadFileResponse { string file_id=1; string message=2; bool success=3; }

message DeleteFileRequest  { string file_id=1; string filename=2; string theme=3; }  // ที่นี่ theme เป็น STRING
message DeleteFileResponse { bool success=1; string message=2; }
```

**สัญญาของ `UploadFile` (client streaming):** ข้อความ **แรก** ต้องตั้งค่า `info` (`FileMetadata`) ส่วนข้อความถัดไปทั้งหมดตั้งค่า `chunk_data` เป็น byte การละเมิดจะ abort ด้วย `INVALID_ARGUMENT` โดย gateway ใช้ frame ขนาด 64 KB

> `UploadFile` **กลืนทุก exception แล้วคืน `success=False`** แทนที่จะโยน gRPC error ให้ตรวจค่า boolean ไม่ใช่แค่ดูรหัสสถานะ

### 8.3 ความไม่สอดคล้องของชนิดข้อมูลที่ต้องระวัง

| แนวคิด | `FileMetadata` | `FileInfo` | `DeleteFileRequest` | HTTP form |
|---|---|---|---|---|
| `theme` | enum `Theme` | `string` (ตัวเลข enum ในรูปข้อความ) | `string` (ชื่อหมวด) | `string` (ชื่อหมวด) |

### 8.4 การสร้าง Stub ใหม่

คำสั่งนี้มีบันทึกไว้ **เฉพาะใน README ที่ root ซึ่งล้าสมัยแล้ว** ไม่มี target ใน Makefile และไม่มีสคริปต์

```bash
cd backend/protos
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chatbot.proto retriever.proto
```

เนื่องจากใช้ `--python_out=.` โมดูลที่สร้างขึ้นจึงเป็น **โมดูลระดับบนสุดแบบแบน** ซึ่งเป็นเหตุผลที่ทุก service เขียน `import retriever_pb2` ไม่ใช่ `from protos import retriever_pb2` **ห้ามแก้ไขไฟล์ `*_pb2.py` / `*_pb2_grpc.py` ที่ถูกสร้างขึ้น**

ไฟล์เหล่านี้ถูกกระจายไปยัง container ในรูป pip package (`protos/setup.py` → `phonphai-protos` 1.0.0) และติดตั้งใน builder stage ของทุก Dockerfile

```dockerfile
COPY protos /protos
RUN uv pip install --no-cache /protos
```

> ### ⚠️ เวอร์ชัน Stub ไม่ตรงกัน — ความเสี่ยงพังตอน import
> - `chatbot_pb2_grpc.py:8` ประกาศ `GRPC_GENERATED_VERSION = '1.80.0'`
> - `retriever_pb2_grpc.py:8` ประกาศ `'1.76.0'`
> - ไฟล์ `_pb2.py` ทั้งสองตรวจ protobuf runtime ที่ **6.31.1**
> - แต่ทุก manifest ระบุเพียง `grpcio>=1.60.0` / `protobuf>=4.25.3`
>
> ไฟล์ที่สร้างขึ้นแต่ละตัวจะโยน `RuntimeError` ตอน import ถ้า runtime ที่ติดตั้งเก่ากว่า หาก resolver เลือก wheel รุ่นเก่า container จะพังตั้งแต่เริ่ม **ควรสร้าง proto ทั้งสองใหม่พร้อมกัน แล้วยกระดับขั้นต่ำ** ในทั้งสาม `requirements.txt` และใน `protos/setup.py`

---

## 9. คู่มือการเชื่อมต่อ (Integration)

### 9.1 เรียกใช้ REST API

เป็นเส้นทางการเชื่อมต่อที่รองรับอย่างเป็นทางการ ทุกอย่างที่ client ภายนอกต้องใช้อยู่ใน [§7](#7-rest-api-reference)

**ขั้นตอน**

1. **ขอบัญชี** — ให้ admin ที่มีอยู่เรียก `POST /api/v1/auth/users` ให้ สำหรับ `role: "user"` ต้องระบุ `staff_id` ซึ่งเป็นตัวกำหนดว่าอ่านคำร้องใดได้บ้าง
2. **เข้าสู่ระบบ** → เก็บ JWT ไว้
3. **แนบ** `Authorization: Bearer <token>` ในทุกคำขอ อายุ 168 ชั่วโมง
4. **สนทนา** ผ่าน `/api/v1/chat/` (แบบง่าย) หรือ `/api/v1/chat/stream` (SSE)
5. **กรอง `sources`** — ตัด `__meta__` และ `__retrieved_chunk__` ออกก่อนแสดงเป็นแหล่งอ้างอิง

> ### ⚠️ Token หมดอายุแบบเงียบ ๆ บนเส้นทางแชท
> `get_optional_user` กลืน `jwt.PyJWTError` แล้วคืน `None` ทำให้ **token ที่หมดอายุหรือผิดรูปถูกปฏิบัติเหมือนไม่มี token เลย** คำขอจะสำเร็จในฐานะผู้ไม่ล็อกอิน และผู้เรียกจะเสียสิทธิ์เข้าถึงคำร้องไปเงียบ ๆ โดยไม่มี 401 และไม่มีคำเตือน
>
> ส่วนเส้นทางที่ต้องยืนยันตัวตน (`/auth/me`, `/files/*`) *จะ* คืน 401 จริง **ให้ตรวจสอบ token ด้วย `GET /api/v1/auth/me`** อย่าอาศัยการตอบกลับของแชทในการตรวจจับการหมดอายุ

**ตัวอย่าง client ภาษา Python ขั้นต่ำ**

```python
import requests

BASE = "http://localhost:8080"

r = requests.post(f"{BASE}/api/v1/auth/login",
                  json={"username": "admin", "password": "a1234567"})
r.raise_for_status()
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

r = requests.post(f"{BASE}/api/v1/chat/",           # ต้องมี / ท้าย
                  json={"session_id": "svc-1", "message": "SKN-2567-0006"},
                  headers=headers)
r.raise_for_status()
data = r.json()

print(data["response"])
citations = [s for s in data["sources"]
             if s["theme"] not in ("__meta__", "__retrieved_chunk__")]
```

**การรับ SSE stream ด้วย Python**

```python
import json, requests

with requests.post(f"{BASE}/api/v1/chat/stream",
                   json={"session_id": "svc-1", "message": "น้ำท่วมทำอย่างไร"},
                   headers=headers, stream=True) as r:
    r.raise_for_status()
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        frame = json.loads(raw[6:])
        if frame["type"] == "token":
            print(frame["content"], end="", flush=True)
        elif frame["type"] == "done":
            print("\ncost:", frame["cost"])
            break                       # ไม่มีสัญญาณ [DONE] — "done" คือจุดจบ
        elif frame["type"] == "error":
            raise RuntimeError(frame["message"])
```

**เช็กลิสต์การเชื่อมต่อจากเบราว์เซอร์**

- [ ] เพิ่ม origin ของคุณลงใน `allow_origins` ที่ `api-gateway/main.py:112` — ดู [§10.12](#1012-เปลี่ยน-cors-origins)
- [ ] ใช้ path ที่มี `/` ท้าย
- [ ] เก็บ JWT (ไม่ใช้ cookie เพราะ `allow_credentials` เป็น `False`)
- [ ] ใช้ `fetch` + `getReader()` สำหรับ streaming **ไม่ใช่** `EventSource` (เพราะต้องใช้ POST + body + auth header)
- [ ] ถอดรหัสด้วย `{ stream: true }` เพื่อให้อักขระไทยแบบ multi-byte ไม่เพี้ยนตอนคร่อม chunk
- [ ] ถือว่า `type: "done"` คือจุดสิ้นสุด
- [ ] ตรวจสอบการหมดอายุด้วยการเรียก `/auth/me`

### 9.2 เรียก `agent` / `retriever` ผ่าน gRPC โดยตรง

มีประโยชน์สำหรับงาน batch, ระบบประเมินผล หรือการเขียน gateway ทดแทน **แต่ข้ามระบบยืนยันตัวตนทั้งหมด** ดูคำเตือนที่ [§8.1](#81-agentagentservice--implement-โดย-agent-เรียกโดย-api-gateway)

**1. เปิดพอร์ต** (สำหรับการพัฒนาเท่านั้น) ใน `backend/docker-compose.yml`

```yaml
  agent:
    ports:
      - "50052:50052"
  retriever:
    ports:
      - "50051:50051"
```

**2. ติดตั้ง stub**

```bash
pip install grpcio protobuf
pip install ./backend/protos
```

**3. เรียก agent**

```python
import grpc, chatbot_pb2, chatbot_pb2_grpc

channel = grpc.insecure_channel("localhost:50052")
stub = chatbot_pb2_grpc.AgentServiceStub(channel)

resp = stub.Chat(chatbot_pb2.ChatRequest(
    session_id="batch-1",
    user_message="SKN-2567-0006",
    user_role="user",        # คุณเป็นผู้ประกาศเอง — agent เชื่อค่านี้
    staff_id=13266,
    username="batch-job",
))
print(resp.ai_message, resp.cost)
```

**4. เรียก retriever โดยตรง** (retrieval ล้วน ไม่มี LLM เหมาะกับการวัดคุณภาพการค้นคืน)

```python
import grpc, retriever_pb2, retriever_pb2_grpc

stub = retriever_pb2_grpc.RetrieverServiceStub(grpc.insecure_channel("localhost:50051"))
resp = stub.Search(retriever_pb2.SearchRequest(
    query="ขั้นตอนการขอชุดบรรเทาทุกข์",
    theme=retriever_pb2.MANUAL,      # ได้เฉพาะ MANUAL หรือ DISASTER — REMEDY จะ abort
    limit=8,
))
for r in resp.results:
    print(f"{r.score:+.3f}  {r.file_name} p.{r.page}\n{r.content[:200]}\n")
```

**ข้อควรระวัง**

- **ไม่มีการตั้ง deadline, retry หรือ keepalive ที่ใดเลย** ให้ตั้ง `timeout=` เองในทุกการเรียก มิฉะนั้นถ้าปลายทางค้าง คำขอจะค้างไปเรื่อย ๆ
- ขนาดข้อความสูงสุดของ gRPC เป็นค่าเริ่มต้น **4 MB** ทั้งสองฝั่ง เพราะไม่มีการส่ง `options=`
- **ไม่มี gRPC reflection** ต้องใช้ stub ที่ compile แล้ว `grpcurl` จะใช้ไม่ได้ถ้าไม่ระบุ `-proto`
- **ไม่มี service `grpc_health.v1`** การตรวจสอบความพร้อมทำด้วยการเชื่อมต่อ TCP ดิบใน compose

### 9.3 เพิ่ม Microservice ใหม่เข้าระบบ

1. นิยาม service ในไฟล์ `.proto` ใหม่ใต้ `backend/protos/` สร้าง stub ใหม่ ([§8.4](#84-การสร้าง-stub-ใหม่)) และเพิ่มโมดูลใหม่ลงใน `py_modules` ของ `protos/setup.py`
2. สร้าง `backend/services/<name>/` พร้อม `main.py`, `config.py` (คลาส `Settings` แบบ `pydantic-settings`), `requirements.txt` และ `Dockerfile` — ใช้ของ agent เป็นต้นแบบ **build context ต้องเป็น `backend/`** ดังนั้นพาธจะเป็น `services/<name>/...`
3. เพิ่มบล็อกใน compose พร้อม `networks: [rag_net]`, healthcheck และ `restart: unless-stopped`
4. หากต้องการเรียกจาก agent ให้เปิด channel ใน `agent/main.py` (ข้าง ๆ channel ของ retriever) เก็บ stub ไว้บน `AgentState` แล้วเปิดเผยเป็น tool ([§10.10](#1010-เพิ่ม-tool-ใหม่ให้-agent))

### 9.4 สร้าง Frontend ของคุณเอง

SPA ที่มาพร้อมระบบเป็นเพียงตัวอย่างอ้างอิง ไม่ใช่สิ่งที่ระบบพึ่งพา หากต้องการเขียนใหม่

- ทุกอย่างที่ต้องใช้อยู่ใน [§7](#7-rest-api-reference)
- อ่าน `Frontend/web/src/services/api.ts` (~165 บรรทัด) — เป็น client ที่สมบูรณ์ในตัวสำหรับทั้ง 8 endpoint
- อย่าลืมอัปเดต `allow_origins` สำหรับ origin ใหม่ ([§10.12](#1012-เปลี่ยน-cors-origins))

**ฟีเจอร์ที่ UI ปัจจุบัน *ยัง*ไม่มี** ซึ่งคุณอาจอยากเพิ่ม

| ช่องว่าง | รายละเอียด |
|---|---|
| **การอ้างอิงแหล่งข้อมูล** | `sources` ถูกรับมาแล้ว**ทิ้ง** ไม่มี UI แสดงแหล่งอ้างอิงเลย |
| **แสดงค่าใช้จ่าย** | API คืน `cost` มาแต่ถูกตัดออกจาก type ฝั่ง Frontend |
| **จัดการ 401** | ไม่มี interceptor ไม่มี refresh ไม่มี redirect token หมดอายุแสดงเป็นฟองข้อความ error ทั่วไป ขณะที่ header ยังแสดงว่าล็อกอินอยู่ |
| **หลายบทสนทนา** | รองรับบทสนทนาเดียว ไม่มีรายการ session ไม่มีตัวสลับ |
| **ยกเลิก stream** | ไม่มี `AbortController` — ช่องพิมพ์ถูกล็อกจนกว่า stream จะจบ |
| **จัดการผู้ใช้** | `POST /api/v1/auth/users` มีอยู่แต่ไม่ได้เชื่อมกับหน้าจอใด |
| **สมัครสมาชิก / รีเซ็ตรหัสผ่าน** | ไม่มีที่ใดเลย |
| **จำภาษาที่เลือก** | ปุ่มสลับ ไทย/อังกฤษ รีเซ็ตทุกครั้งที่โหลดหน้าใหม่ |

---

## 10. ตำราการปรับเปลี่ยนระบบ

### 10.1 เปลี่ยนฐานข้อมูลบัญชีผู้ใช้

api-gateway เก็บบัญชีไว้ใน **backend ที่สลับได้** โดยเลือกตอน deploy ไม่ต้องแก้โค้ดสำหรับ 2 ตัวเลือกที่รองรับ

#### ตัวเลือก A — MongoDB (ค่าเริ่มต้น)

```env
USER_DB_BACKEND=mongo
MONGO_URI=mongodb://mongo:27017
MONGO_DB=rag_db
```

`MongoUserStore.__init__` สร้าง unique index บน `username` ให้เองตอนเริ่มครั้งแรก ไม่ต้องทำอะไรเพิ่ม

#### ตัวเลือก B — PostgreSQL (แนะนำสำหรับการใช้งานจริง)

**1. เตรียมฐานข้อมูล** Postgres **13 ขึ้นไป** (จำเป็นสำหรับ `gen_random_uuid()` จาก `pgcrypto`) ฐานข้อมูลที่เขียนได้ และ role ที่สร้าง extension ได้ — หรือฐานข้อมูลที่ติดตั้ง `pgcrypto` ไว้แล้ว

**2. สร้าง Schema** มี 2 ทางเลือก

*จัดการเอง (ไม่ต้องแตะอะไร):* api-gateway จะรัน DDL ให้ตอนบูต ทุกคำสั่งเป็น `IF NOT EXISTS` จึงทำซ้ำได้ปลอดภัย

*จัดการด้วยมือ (แนะนำสำหรับสภาพแวดล้อมที่จำกัดสิทธิ์):*

```bash
psql "$POSTGRES_USER_DSN" -f backend/services/api-gateway/db/migrations/postgres_users.sql
```

เมื่อตารางมีอยู่แล้ว คำสั่ง `IF NOT EXISTS` ของ gateway จะไม่ทำอะไร

**3. ตั้งค่า**

```env
USER_DB_BACKEND=postgres
POSTGRES_USER_DSN=postgresql://app_user:strongpass@db.internal:5432/auth_db
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=<รหัสผ่านที่แข็งแรง>
```

**4. รีสตาร์ทและตรวจสอบ**

```bash
docker compose up -d --force-recreate api-gateway

curl -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<รหัสผ่านที่แข็งแรง>"}'

psql "$POSTGRES_USER_DSN" -c "SELECT username, role FROM auth_users;"
```

> ⚠️ บล็อก `api-gateway` **ไม่ได้ประกาศ `depends_on: postgres`** การใช้ Postgres ที่อยู่ใน stack เดียวกันจึงเกิด race ตอนเริ่มระบบ ให้เพิ่ม
> ```yaml
>   api-gateway:
>     depends_on:
>       postgres:
>         condition: service_healthy
> ```

#### การสลับไปมาระหว่าง backend

ที่เก็บทั้งสอง **แยกจากกันโดยสิ้นเชิง** — ผู้ใช้ที่อยู่ใน Mongo ไม่มีอยู่ใน Postgres และไม่มีการซิงก์ หากต้องการย้าย ให้ dump จากต้นทาง แปลงข้อมูล แล้ว `INSERT` เข้าปลายทาง **แฮช bcrypt ใช้ข้ามกันได้** ไม่ต้องสร้างใหม่

หากต้องการย้อนกลับ ให้ตั้ง `USER_DB_BACKEND=mongo` แล้ว restart ข้อมูลใน Postgres จะยังอยู่แต่ไม่ถูกใช้

#### ตัวเลือก C — backend ที่ยังไม่รองรับ (MSSQL, MySQL, LDAP, HTTP service ภายใน)

1. implement `AbstractUserStore` (`api-gateway/db/base.py`) — 4 เมธอด: `find_by_username`, `find_by_id`, `admin_exists`, `create_user`
2. คืนค่าเป็น dict `UserRecord` ที่ใช้คีย์ `user_id` เป็น **สตริง** ไม่ใช่ชนิด id ดั้งเดิมของ backend คุณ
3. เพิ่มเงื่อนไขใน `make_user_store` (`api-gateway/db/__init__.py:6-19`)
4. เพิ่มตัวแปรสภาพแวดล้อมใหม่ใน `config.py`
5. เพิ่มตัวแปรเดียวกันในบล็อก `api-gateway` ของ `docker-compose.yml`

ส่วนที่เหลือของ gateway — การล็อกอิน การออก JWT การตรวจบทบาท การสร้างบัญชีเริ่มต้น — ไม่ต้องแก้ เพราะสื่อสารผ่าน `AbstractUserStore` เท่านั้น

> การเลือกค่าที่ไม่รองรับ (เช่น `USER_DB_BACKEND=mysql`) จะ **ล้มเหลวทันทีตอนเริ่มระบบ** พร้อม `ValueError` ที่อ่านเข้าใจได้

### 10.2 เปิดใช้งานประวัติการสนทนา

**ปิดเป็นค่าเริ่มต้น** ต้องตั้งสวิตช์ 2 ตัวที่เป็นอิสระต่อกันบน **2 service ที่ต่างกัน**

**1. api-gateway** (เป็นผู้เขียนประวัติ) — เพิ่มใน `environment:`

```yaml
      - CHAT_HISTORY_ENABLED=true
      - CHAT_HISTORY_BACKEND=mongo        # หรือ postgres
```

**2. agent** (เป็นผู้อ่าน และเป็นตัวผูก tool `load_conversation_history`)

```yaml
      - CHAT_HISTORY_ENABLED=true
      - CHAT_HISTORY_BACKEND=mongo        # ต้องตรงกัน
```

> ### 🔴 agent จะพังตอนเริ่มระบบ
> **`pymongo` ขาดหายไปจาก `backend/services/agent/requirements.txt`** แต่ `db/chat_history.py:26` import มันอยู่ ดังนั้นเมื่อใช้ `CHAT_HISTORY_BACKEND=mongo` ตามค่าเริ่มต้น การเปิดประวัติจะได้
> ```
> ModuleNotFoundError: No module named 'pymongo'
> ```
> **แก้ก่อนเปิดใช้งาน:** เพิ่ม `pymongo>=4.6` ลงใน `backend/services/agent/requirements.txt` แล้ว build image ของ agent ใหม่ (ปัญหานี้ถูกปิดบังอยู่เพราะปัจจุบันประวัติปิดอยู่)

**ข้อสังเกต**

- เทิร์นของผู้ไม่ล็อกอิน **ไม่เคยถูกบันทึก** — gateway เขียนเฉพาะเมื่อมีผู้ใช้ที่ยืนยันตัวตนแล้ว
- ประวัติผูกกับ `session_id` ซึ่งสำหรับผู้ใช้ที่ล็อกอินแล้ว **คือ user id** ดังนั้น 1 ผู้ใช้ = 1 เธรดถาวร
- ประวัติถูกโหลด **เฉพาะเมื่อโมเดลตัดสินใจเรียก tool เท่านั้น** ตามคำแนะนำในหัวข้อ 5 ของ system prompt ไม่ได้ถูกใส่เข้าไปอัตโนมัติ
- จำนวนเทิร์นถูกจำกัดที่ **[1, 20]** ส่วน `CHAT_HISTORY_WINDOW` **ไม่ถูกบังคับใช้** แม้ docstring จะบอกไว้ก็ตาม
- **ไม่มีการสรุปย่อ** — ไม่มี rolling summary ไม่มีการตัดตามจำนวน token ไม่มีการตัดทิ้ง
- การเขียนประวัติจากเส้นทาง SSE ใช้ `asyncio.create_task(...)` แบบ fire-and-forget ในบล็อก `finally` ซึ่งไม่ถูก await และไม่มีการอ้างอิงถือไว้ จึงอาจถูกทิ้งเมื่อ client ตัดการเชื่อมต่อหรือถูก GC **ประวัติจากเส้นทางสตรีมจึงเป็นแบบ best-effort**

### 10.3 ย้ายฐานข้อมูลคำร้องไปที่อื่น

**คงโครงสร้างเดิม แต่ใช้ Postgres ภายนอก**

1. ลบ service `postgres` ออกจาก `docker-compose.yml` และลบ `depends_on: postgres` ออกจากบล็อก `agent`
2. ตั้งค่าบน service `agent`
   ```yaml
         - POSTGRES_HOST=db.internal
         - POSTGRES_PORT=5432
         - POSTGRES_DB=phonphai
         - POSTGRES_USER=app_user
         - POSTGRES_PASSWORD=strongpass
   ```
3. สร้าง schema ด้วยมือ **โดยเปลี่ยน `COPY ... FROM '/path'` ฝั่งเซิร์ฟเวอร์เป็น `\copy` ฝั่ง client** เพราะ instance แบบ managed อ่านไฟล์ในเครื่องคุณไม่ได้
   ```bash
   # รัน DDL ก่อน จากนั้น
   psql "$DSN" -c '\copy issue_logs(code, issue_id, "user", status, process_level, updated_date) FROM ''dump.csv'' WITH (FORMAT csv, HEADER true)'
   ```

**โหลดข้อมูลใหม่ใน container ที่มาพร้อมระบบ**

```bash
docker compose down
Remove-Item -Recurse -Force backend\data\postgres_data
docker compose up --build postgres
```

**เพิ่มตารางใหม่**

1. เพิ่ม `CREATE TABLE IF NOT EXISTS ...` ลงใน `services/sql_data/init.sql`
2. หากต้องมีข้อมูลตั้งต้น ให้เพิ่มไฟล์ CSV ข้าง ๆ `dump.csv` เพิ่มบรรทัด `COPY` ใน `init.sql` **และ** เพิ่มบรรทัด `COPY` ใน Dockerfile เพื่อให้ CSV ไปอยู่ที่ `/docker-entrypoint-initdb.d/` (พาธต้นทางอ้างอิงจาก `backend/`)
3. `docker compose down` → ลบ `backend/data/postgres_data` → `docker compose up --build postgres`
4. เพิ่มเมธอด query ใน `PostgresTicketStore` (`agent/db/postgres.py`) เชื่อม store เข้าที่ `agent/main.py:22-29` แล้วเปิดเผยเป็น tool ([§10.10](#1010-เพิ่ม-tool-ใหม่ให้-agent))

**เปลี่ยนไปใช้ engine อื่นทั้งหมด:** ต้องเขียน `PostgresTicketStore` ใหม่ เพราะ query ใช้ไวยากรณ์เฉพาะของ Postgres ทั้ง `SELECT DISTINCT ON`, `substring(x from 'regex')` และ `NULLS LAST` ซึ่งไม่พกพาข้าม engine

### 10.4 เปลี่ยนโมเดล LLM หรือผู้ให้บริการ

โมเดล **ฝังตายตัว** และชื่อโมเดลปรากฏ **3 จุด** ในไฟล์ `backend/services/agent/core/graph.py`

```python
# core/graph.py:42-50
base_model_config = dict(
    model="google/gemini-2.5-flash",                    # ← บรรทัด 43
    openai_api_base="https://openrouter.ai/api/v1",     # ← บรรทัด 44
    openai_api_key=settings.OPENROUTER_API_KEY,         # ← บรรทัด 45
    temperature=0,                                      # ← บรรทัด 47
)

# core/graph.py:57-62 — metadata สำหรับแสดงผลใน LangSmith
model_with_tools = model.bind_tools(_active_tools).with_config(
    {"metadata": {"ls_provider": "openrouter",
                  "ls_model_name": "google/gemini-2.5-flash"}}   # ← บรรทัด 58
)
streaming_model_with_tools = streaming_model.bind_tools(_active_tools).with_config(
    {"metadata": {"ls_provider": "openrouter",
                  "ls_model_name": "google/gemini-2.5-flash"}}   # ← บรรทัด 61
)
```

**เปลี่ยนไปใช้โมเดลอื่นบน OpenRouter**

1. แก้บรรทัด 43 เป็น slug ใด ๆ ของ OpenRouter เช่น `anthropic/claude-sonnet-4.5`, `openai/gpt-4.1-mini`
2. แก้บรรทัด 58 และ 61 ให้ตรงกัน เพื่อให้ trace ใน LangSmith ถูกต้อง
3. build ใหม่: `docker compose up -d --build agent`

**ย้ายออกจาก OpenRouter ทั้งหมด** (ไป OpenAI โดยตรง, Azure, หรือ vLLM/Ollama ในเครื่อง)

1. แก้ `openai_api_base` (บรรทัด 44) และ `openai_api_key` (บรรทัด 45)
2. **การติดตามค่าใช้จ่ายจะพังโดยไม่มีสัญญาณเตือน** เพราะ `extract_cost` (`core/graph.py:181-200`) และ `extract_usage_metadata` (`:203-236`) อ่านคีย์เฉพาะของ OpenRouter (`cost`, `cost_details.upstream_inference_prompt_cost`) บนผู้ให้บริการอื่นฟังก์ชันเหล่านี้จะคืน `0.0` / `{}` โดยไม่โยน error ให้ยอมรับว่า `cost: 0.0` หรือเขียนฟังก์ชันใหม่
3. ตรวจสอบว่าผู้ให้บริการรองรับ **tool calling** เพราะกลไก routing ทั้งหมดพึ่งพาสิ่งนี้

**ทำให้ตั้งค่าได้ (แนะนำ)** ทุกค่าอื่นใน service นี้ตั้งผ่านตัวแปรสภาพแวดล้อมได้อยู่แล้ว มีแต่โมเดลที่เป็นข้อยกเว้น เพิ่มใน `agent/config.py`

```python
    LLM_MODEL: str = "google/gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
```

แล้วอ้างอิง `settings.LLM_MODEL` ทั้งสามจุด พร้อมเพิ่มตัวแปรลงในบล็อก `agent` ของ compose

**ตัวแปลง PDF ใช้โมเดลแยกต่างหาก** และฝังตายตัวเช่นกัน — `google/gemini-2.5-flash` ที่ `temperature=0.1` ใน `retriever/utils/openrouter_parser.py:86`, `:98` โมเดลนี้ **ต้องรองรับการมองเห็นภาพ (vision)** โมเดลที่รับเฉพาะข้อความจะทำงานล้มเหลวตอนอัปโหลด PDF

**บทบาทอื่น ๆ ของโมเดล** (ทั้งหมดเป็นโมเดลตัวเดียวกันที่ `temperature=0`)

| บทบาท | ตำแหน่ง | หน้าที่ |
|---|---|---|
| ตัวเลือกเส้นทาง / ผู้เขียนคำตอบ | `core/graph.py:268` | เลือก tool และเขียนคำตอบ |
| สำรองเมื่อใช้ tool ครบโควตา | `core/graph.py:287` | บังคับตอบเมื่อครบ `MAX_TOOL_CALL_ROUNDS` |
| ลองใหม่เมื่อคำตอบว่าง | `core/graph.py:326` | เมื่อผู้ให้บริการคืนค่าว่าง |
| ตัวบีบอัดคำตอบภัยพิบัติ | `core/graph.py:166` | ย่อคำตอบเหลือ 1–2 ประโยค |
| ผู้ตัดสินในการประเมิน | `evaluation/eval_runner/settings.py:47-48` | `google/gemini-3-flash-preview` ใช้แบบออฟไลน์เท่านั้น |

### 10.5 เปลี่ยนโมเดล Embedding

**นี่คือการเปลี่ยนแปลงที่เสี่ยงที่สุดในระบบ อ่านหัวข้อนี้ให้จบก่อนลงมือ**

ชื่อโมเดลถูกประกาศไว้ **2 จุดที่ต้องตรงกันเสมอ** คือ build arg (เพื่อให้ weights ถูกฝังใน image) และตัวแปรรันไทม์ (ซึ่งเป็นตัวที่มีผลจริง)

```yaml
# backend/docker-compose.yml
  retriever:
    build:
      args:
        EMBEDDING_MODEL_NAME: intfloat/multilingual-e5-large   # ← บรรทัด 45 (build)
    environment:
      - EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large    # ← บรรทัด 59 (runtime)
```

รวมทั้ง `retriever/config.py:15` (ค่าเริ่มต้นในโค้ด) และ `retriever/Dockerfile:62` (ค่าเริ่มต้นของ `ARG`)

> **ถ้าเปลี่ยนเฉพาะตัวแปรรันไทม์** weights ใหม่จะไม่อยู่ใน HF cache ที่ฝังไว้ และจะถูก **ดาวน์โหลดตอนมีคำขอแรกภายใน container** ซึ่งมีขนาดหลาย GB บล็อกการค้นหาครั้งแรก และ **หายไปทุกครั้งที่ `docker compose down`** เพราะ `/root/.cache/huggingface` ไม่ได้เป็น volume

#### ต้องสร้าง collection ใหม่ไหม

| สถานการณ์ | สิ่งที่ต้องทำ |
|---|---|
| **มิติเท่าเดิม** (e5-large 1024 → `BAAI/bge-m3` 1024) | เก็บ collection เดิมได้ **แต่ต้อง re-embed** เพราะ vector เก่ากับใหม่เทียบกันไม่ได้ |
| **มิติต่างกัน** (→ e5-base 768, → all-MiniLM-L6-v2 384) | **ต้องลบและสร้าง collection ใหม่** เพราะ `_ensure_collection` จะออกจากฟังก์ชันทันทีเมื่อ collection มีอยู่แล้ว จึงคง `size: 1024` ไว้ ทำให้ทุกการ upsert/search ล้มเหลวเรื่องมิติไม่ตรง |

#### 🔴 ไม่มีการสำรองเอกสารต้นฉบับ

**`retriever/db/mongo.py:16-17` ทิ้ง byte ของไฟล์ต้นฉบับโดยเจตนา** Mongo เก็บเพียง `file_name`, `theme`, `content_type`, `size_bytes`, `created_at` **สำเนาเดียวของข้อความที่แปลงแล้วคือ payload `content` ใน Qdrant** การลบ collection คือการทำลายฐานความรู้อย่างถาวร

#### การเปลี่ยนแบบมิติเท่าเดิม (ปลอดภัย)

```bash
# 1. แก้ทั้ง docker-compose.yml:45 และ :59 เป็นโมเดลใหม่
docker compose build retriever
docker compose up -d retriever

# 2. re-embed ทุก point ในที่เดิม โดยใช้ point ID เดิม
docker compose exec retriever python -m scripts.reindex_collection --all

# 3. restart เพื่อสร้าง index BM25 ใหม่จาก collection ที่เปลี่ยนไป
docker compose restart retriever
```

#### การเปลี่ยนแบบมิติต่างกัน (ทำลายข้อมูล)

```bash
# 1. ส่งออกข้อมูลก่อน — ไม่มีสคริปต์สำหรับการนี้ ให้ใช้ REST API ของ Qdrant
curl -X POST "http://localhost:6333/collections/manual/points/scroll" \
  -H 'Content-Type: application/json' \
  -d '{"limit":10000,"with_payload":true,"with_vector":false}' > manual_backup.json
curl -X POST "http://localhost:6333/collections/disaster/points/scroll" \
  -H 'Content-Type: application/json' \
  -d '{"limit":10000,"with_payload":true,"with_vector":false}' > disaster_backup.json

# 2. แก้ทั้ง docker-compose.yml:45 และ :59
# 3. build ใหม่เพื่อฝัง weights ใหม่
docker compose build retriever

# 4. ลบ collection
curl -X DELETE "http://localhost:6333/collections/manual"
curl -X DELETE "http://localhost:6333/collections/disaster"

# 5. restart แล้วอัปโหลด PDF ต้นฉบับทุกไฟล์ใหม่ผ่านหน้า admin หรือ API
docker compose up -d retriever
```

#### โค้ดที่บางโมเดลบังคับให้ต้องแก้

| file:line | เมื่อไหร่ต้องแก้ |
|---|---|
| `db/qdrant.py:27` — `self.uses_e5_prefixes = "e5" in model_name.lower()` | เมื่อโมเดลใหม่ต้องใช้ prefix แต่ชื่อไม่มีคำว่า `"e5"` เช่น `BAAI/bge-m3` ไม่ต้องใช้ prefix (จึงไม่มีปัญหา) แต่ `nomic-embed-text-v1.5` ต้องใช้ `search_query:` / `search_document:` ซึ่ง **ต้องเขียนโค้ดเพิ่ม** ส่วน `intfloat/e5-mistral-7b-instruct` ต้องใช้ instruction template ที่เงื่อนไขนี้สร้างไม่ได้ |
| `db/qdrant.py:40` — `model_kwargs={"device": "cpu"}` | เมื่อต้องการให้ embedding ใช้ GPU หรือต้องเพิ่ม `trust_remote_code=True` (จำเป็นสำหรับโมเดลตระกูล Nomic / Jina) |

> **Embedding ทำงานบน CPU เสมอ** แม้ container จะจอง NVIDIA GPU ไว้ก็ตาม มีเพียง *reranker* ที่ใช้ GPU และไม่มีตัวแปรสภาพแวดล้อมให้ตั้ง ต้องแก้ `db/qdrant.py:40` เป็น `{"device": "cuda"}` เอง อนึ่งทุกการเรียก embed ยังถูกจัดคิวด้วย `threading.Lock` ดังนั้น embedding เป็นแบบเธรดเดียวเสมอ ไม่ว่าจะมี gRPC worker 10 ตัวก็ตาม

### 10.6 เปลี่ยน Reranker / รันโดยไม่ใช้ GPU

**เปลี่ยน reranker** — ประกาศ 2 จุดเช่นเดียวกับ embedder

```yaml
  retriever:
    build:
      args:
        RERANK_MODEL_NAME: BAAI/bge-reranker-v2-m3      # ← บรรทัด 46
    environment:
      - RERANK_MODEL_NAME=BAAI/bge-reranker-v2-m3       # ← บรรทัด 60
```

build ใหม่ด้วย `docker compose build retriever` ต่างจาก embedder ตรงที่ **การเปลี่ยน reranker ไม่ต้อง re-index** เพราะมันให้คะแนนคู่ query/document ตอน query และไม่แตะ vector ที่เก็บไว้เลย

> reranker แต่ละตัวมีสเกลคะแนนต่างกัน `RERANK_SCORE_THRESHOLD=0.0` ถูกปรับมาสำหรับ logit ดิบของ BGE หลังเปลี่ยนโมเดลควรปรับค่านี้ใหม่ (หรือตั้ง `-10` เพื่อปิดการกรอง)

#### รันโดยไม่ใช้ GPU

**1.** ลบบล็อก `deploy.resources` ออกจาก service `retriever` (`docker-compose.yml:47-53`)

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**2.** บังคับให้ rerank บน CPU

```yaml
    environment:
      - RERANK_DEVICE=cpu
```

ถ้าไม่ตั้ง `base.py:71-80` จะแปลง `auto` เป็น `"cuda" if torch.cuda.is_available() else "cpu"` ซึ่งก็ถอยกลับมาถูกอยู่แล้ว แต่การตั้งให้ชัดเจนช่วยลดความประหลาดใจ

**3.** (ไม่บังคับ) build ใหม่บน base image ที่เล็กลง `retriever/Dockerfile:2` และ `:38` ใช้ `nvidia/cuda:12.4.1-runtime-ubuntu22.04` และติดตั้ง torch แบบ CUDA (`--extra-index-url https://download.pytorch.org/whl/cu124`) สำหรับ CPU ล้วนสามารถเปลี่ยนเป็น `python:3.11-slim` และตัด extra index ออก ได้ image ที่เล็กกว่ามาก

**คาดหวังว่า latency จะสูงขึ้นอย่างมีนัยสำคัญ** เพราะ cross-encoder ต้องให้คะแนนผู้เข้าชิงทั้ง 25 รายการต่อ query บน CPU ควรลด `RETRIEVAL_K` ลงเพื่อชดเชย

### 10.7 ปรับคุณภาพการค้นคืน

ทั้งหมดอยู่บน service **retriever** ยกเว้นที่ระบุไว้

| อาการ | ตัวปรับ | ลองปรับเป็น |
|---|---|---|
| ค้นไม่เจอเอกสารที่เกี่ยวข้อง | `RETRIEVAL_K` | 25 → 40 (ช้าลง เพราะเป็นขนาด batch ของ rerank ด้วย) |
| คำตอบมีข้อมูลรบกวนเยอะ | `RERANK_SCORE_THRESHOLD` | 0.0 → 1.0 หรือ 2.0 |
| ไม่เคยได้ผลที่ใช้ได้เลย | `RERANK_SCORE_THRESHOLD` | 0.0 → -10 (ปิดการกรองโดยปริยาย) |
| คำถามแบบระบุคำเป๊ะ ๆ ค้นไม่เจอ | `HYBRID_BM25_WEIGHT` ↑ / `HYBRID_SEMANTIC_WEIGHT` ↓ | 0.4/0.6 → 0.5/0.5 |
| คำถามที่ถอดความใหม่ค้นไม่เจอ | `HYBRID_SEMANTIC_WEIGHT` ↑ | 0.6 → 0.75 |
| คำตอบสั้นเกินไป ขาดรายละเอียด | **agent:** `RETRIEVER_SEARCH_LIMIT` | 8 → 12 |
| คำตอบภัยพิบัติสั้นเกินไป | **agent:** `DISASTER_RETRIEVER_SEARCH_LIMIT`, `DISASTER_EXCERPT_MAX_CHARS` | 4 → 6, 900 → 1400 |
| คำตอบภัยพิบัติยาวเกินไป | **agent:** `DISASTER_CONCISE_REWRITE_ENABLED` | เป็น `true` อยู่แล้ว ตั้ง `false` เพื่อปิดการบีบอัด |

> **อย่าลืม: `RERANK_TOP_K` ไม่มีผลในการใช้งานจริง** ให้แก้ตัวแปร `*_SEARCH_LIMIT` ของ agent แทน

น้ำหนักทั้งสอง **ไม่ถูก normalize เทียบกันอัตโนมัติ** เป็นเพียงตัวคูณดิบบนค่า RRF ไม่จำเป็นต้องรวมกันได้ 1 แต่การทำให้รวมกันได้ 1 ช่วยให้เข้าใจสัดส่วนง่ายขึ้น

**อัตราส่วน 0.6 / 0.4 ได้มาจากการทดลองจริง** ด้วยชุดเครื่องมือ tuning ใน `backend/evaluation/` หากต้องการหาใหม่หลังเปลี่ยนคลังเอกสาร

```bash
cd backend/evaluation
make retrieval-tuning         # กวาดค่า semantic weight x k แล้วออก recall curve + กราฟ SVG
make retrieval-rerank-tuning  # ตรึง alpha แล้วกวาดค่า rerank k
```

ผลลัพธ์อยู่ที่ `outputs/retrieval_tuning/` ได้แก่ `per_query_results.csv`, `recall_curve_summary.csv` และ `plots/<theme>_<question_type>_recall.svg`

### 10.8 เปลี่ยนการแบ่ง Chunk

```yaml
  retriever:
    environment:
      - CHUNK_SIZE=550        # หน่วยเป็นตัวอักษร ไม่ใช่ token
      - CHUNK_OVERLAP=90
```

ค่าเหล่านี้มีผล **ตอนนำเข้าเท่านั้น** การเปลี่ยนไม่ส่งผลต่อ chunk ที่เก็บไว้แล้ว

> ### ✅ ไม่ต้องอัปโหลดใหม่และไม่ต้องจ่ายค่าแปลง PDF ซ้ำ
> markdown ที่ Gemini แปลงไว้ถูกเก็บใน payload `content` ของ Qdrant จึงสามารถแบ่ง chunk ใหม่จากข้อความที่เก็บไว้ได้เลย
>
> ```bash
> docker compose exec retriever python -m scripts.rechunk_collection \
>   --collection manual --chunk-size 400 --chunk-overlap 60
> docker compose restart retriever      # จำเป็น — สคริปต์ไม่รีเฟรช BM25
> ```
>
> นี่คือวงจรการปรับจูนขนาด chunk ที่ประหยัดที่สุด

`rechunk_collection.py` ยังเป็นที่เดียวที่ใช้ **ตัวแบ่งแบบเข้าใจ markdown**

```python
["\n\n", "\n# ", "\n## ", "\n* ", "\n- ", "\n", " ", ""]
```

ขณะที่การแบ่งตอนนำเข้าใช้ค่าเริ่มต้นธรรมดา (`["\n\n", "\n", " ", ""]`) การ re-chunk จึงมักได้ขอบเขตที่ *ดีกว่า* การนำเข้าครั้งแรก มีข้อจำกัด `chunk_size >= 100` และ `0 <= overlap <= chunk_size // 2`

> ⚠️ **อย่าสับสนระหว่างตัวแปร `CHUNK_SIZE` สองตัว** ของ api-gateway (65536) คือ **ขนาด frame ของ gRPC ตอนอัปโหลด หน่วยเป็น byte** ส่วนของ retriever (550) คือ **ขนาดที่ text splitter ใช้ หน่วยเป็นตัวอักษร** ชื่อเดียวกันแต่ความหมายไม่เกี่ยวข้องกันเลย

### 10.9 แก้ไข Prompt

| สิ่งที่ต้องการแก้ | ตำแหน่ง | หมายเหตุ |
|---|---|---|
| **System prompt หลัก** | `agent/prompts/prompt.py:1-62` | เป็นค่าคงที่แบบคงที่ ไม่มี templating ไม่มี `.format()` ไม่มีตัวแปร แก้ได้อย่างอิสระ |
| **กฎการเลือกฐานความรู้** | `prompt.py:3-12` (หัวข้อ 1) | กำหนดว่าคำถามแบบใดใช้ tool ใด |
| **สไตล์และความกระชับของคำตอบ** | `prompt.py:14-27` (หัวข้อ 2) | กฎพฤติกรรม 10 ข้อ ปรับจูนมาจากการประเมินผล |
| **การจำแนกประเภทคำตอบหมวดคู่มือ** | `prompt.py:29-44` (หัวข้อ 3) | `exact_value`, `count_list`, `steps`, `capability`, `comparison`, `other` |
| **รูปแบบผลลัพธ์** | `prompt.py:52-61` | ห้ามใช้ markdown fence ห้ามอ้างอิงในบรรทัด ห้ามแสดง chunk ID |
| **Prompt บีบอัดคำตอบภัยพิบัติ** | `agent/core/graph.py:151-163` | สตริงในโค้ด ส่งเป็น `HumanMessage` เปล่า ๆ ไม่มี system prompt |
| **ข้อความเมื่อใช้ tool ครบโควตา** | `agent/core/graph.py:280-284` | |
| **ข้อความเมื่อคำตอบว่าง** | `agent/core/graph.py:319-323` | |
| **Prompt แปลง PDF** | `retriever/utils/prompt.py:1-12` | สั่งให้ถอดความเป็น markdown พร้อม placeholder `[IMAGE: <ชื่อ>]` |
| **คำอธิบาย tool** | docstring ของ tool, `agent/tools/retriever_tool.py:289-310` | ⚠️ **มีผลต่อการเลือกเส้นทางมากกว่า system prompt** |

Prompt ทั้งหมดถูกอ่านตอน **import** จึงต้อง restart container

```bash
docker compose restart agent      # เมื่อแก้ prompt.py / graph.py
docker compose restart retriever  # เมื่อแก้ prompt แปลง PDF
```

**ไม่มีการแยก prompt ออกเป็นไฟล์ต่างหาก** (ไม่มี `.txt`/`.yaml`/`.jinja`) ไม่มีระบบเวอร์ชันของ prompt และไม่มีการดึงจาก LangSmith Hub

### 10.10 เพิ่ม Tool ใหม่ให้ Agent

**1. นิยาม tool** ใน `backend/services/agent/tools/retriever_tool.py`

```python
@tool(response_format="content_and_artifact")
async def search_policy_documents(query: str) -> tuple[str, list]:
    """Use this to look up HR policies, leave rules, and staff benefit entitlements.
    Do NOT use this for disaster protocols or application how-to questions."""
    return await _execute_search(query, "Policy", retriever_pb2.POLICY)
```

**docstring คือคำอธิบาย tool ที่ถูกส่งให้โมเดล** จึงเป็นส่วนหนึ่งของ prompt กำหนดเส้นทางโดยตรง ให้เขียนเป็นคำสั่ง และระบุชัดเจนว่าไม่ควรใช้กับอะไร ส่วนนี้สำคัญกว่า system prompt

**2. ลงทะเบียน**

```python
# tools/retriever_tool.py:314-319
TOOLS_LIST = [
    search_remedy_tickets,
    list_my_remedy_tickets,
    search_disaster_protocols,
    search_user_manuals,
    search_policy_documents,        # ← ใหม่
]
```

`core/graph.py:52-55` จะหยิบ `TOOLS_LIST` ไปผูกกับโมเดลทั้งสองรูปแบบให้เองอัตโนมัติ

**3. เพิ่มคำอธิบายในหัวข้อกำหนดเส้นทาง** ของ `prompts/prompt.py:3-12` เพื่อให้โมเดลรู้ว่าควรเลือกเมื่อไหร่

**4. คืนค่าเป็น `tuple[str, list]`** โดยสตริงส่งให้โมเดล ส่วน list กลายเป็น `ToolMessage.artifact` ซึ่ง **ไม่ถูกแสดงให้ LLM เห็น** ใช้ artifact สำหรับข้อมูลอ่อนไหวหรือข้อมูลที่มีโครงสร้าง — นี่คือวิธีที่ข้อมูลคำร้องไม่หลุดเข้า prompt

**5. บังคับสิทธิ์ภายใน tool** หากแตะข้อมูลที่ผูกกับผู้ใช้ ให้ทำตามรูปแบบเดิม

```python
from core.auth_context import get_current_auth

auth = get_current_auth()
if auth.is_anonymous:
    return ("Access denied: the user is not logged in.", [])
staff_filter = None if auth.is_admin else auth.staff_id
```

**6. หาก tool ต้องการจัดการผลลัพธ์เป็นพิเศษ** ให้เพิ่มเงื่อนไขใน `format_final_answer` (`core/graph.py:363-381`) เพื่อจัดเส้นทาง artifact และใน `_build_sources` (`agent/server.py:61-117`) เพื่อส่งออกไปทาง wire

**7.** พิจารณาเพิ่ม `MAX_TOOL_CALL_ROUNDS` (ค่าเริ่มต้น 3) หาก tool ใหม่ทำให้ห่วงโซ่การเรียกยาวขึ้น

**8.** `docker compose up -d --build agent`

### 10.11 เพิ่มหมวดฐานความรู้ใหม่

หมวด (theme) เป็นค่า enum ใน proto การเพิ่มจึงกระทบหลายไฟล์

**1. เพิ่มค่า enum** ใน `backend/protos/retriever.proto:14-19`

```protobuf
enum Theme {
  THEME_UNSPECIFIED = 0;
  REMEDY            = 1;
  DISASTER          = 2;
  MANUAL            = 3;
  POLICY            = 4;   // ← ใหม่
}
```

**2. สร้าง stub ใหม่** ([§8.4](#84-การสร้าง-stub-ใหม่))

**3. สร้างคลาส theme** — `backend/services/retriever/themes/policy.py`

```python
from themes.base import BaseTheme

class PolicyTheme(BaseTheme):
    def __init__(self):
        super().__init__("policy")      # → ชื่อ collection ใน Qdrant คือ "policy"
```

**4. ลงทะเบียน** ใน `retriever/server.py:16-19`

```python
self.themes = {
    retriever_pb2.DISASTER: DisasterTheme(),
    retriever_pb2.MANUAL: ManualTheme(),
    retriever_pb2.POLICY: PolicyTheme(),      # ← ใหม่
}
```

**5. เพิ่มการ map สตริง→enum** ในเส้นทางการลบ (`retriever/server.py:136-140`)

**6. เพิ่มการ map ตอนอัปโหลด** ใน `api-gateway/routers/files.py:45-49`

```python
theme_map = {
    "remedy": retriever_pb2.REMEDY,
    "disaster": retriever_pb2.DISASTER,
    "manual": retriever_pb2.MANUAL,
    "policy": retriever_pb2.POLICY,       # ← ใหม่
}
```

**7. เพิ่มตัวเลือกใน Frontend** ที่ `Frontend/web/src/services/api.ts:113`

```ts
export type FileTheme = 'remedy' | 'disaster' | 'manual' | 'policy'
```

และตัวเลือกใน `<select>` ที่ `src/pages/AdminFilesPage.tsx:16-20`

**8. เพิ่ม tool ของ agent** สำหรับหมวดนี้ ([§10.10](#1010-เพิ่ม-tool-ใหม่ให้-agent))

**9.** build ใหม่ทั้งหมด: `docker compose up -d --build`

collection ใน Qdrant จะถูกสร้างแบบ lazy ตอนอัปโหลดครั้งแรก โดยใช้มิติ vector ปัจจุบัน

### 10.12 เปลี่ยน CORS Origins

ฝังตายตัวและ **ไม่มีตัวแปรสภาพแวดล้อม** ต้องแก้ `backend/services/api-gateway/main.py:110-115`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://chatbot.redcross.or.th",     # ← เพิ่มของคุณ
    ],
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**ทางที่ดีกว่า — ทำให้ตั้งค่าได้** เพิ่มใน `api-gateway/config.py`

```python
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
```

แล้วใน `main.py`

```python
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
```

พร้อมเพิ่ม `CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:5173,http://localhost:3000}` ลงในบล็อก compose

อย่าลืมเพิ่ม `PUT`/`PATCH` ใน `allow_methods` หากคุณเพิ่ม endpoint แบบนั้น และเพิ่ม header ที่กำหนดเองใน `allow_headers` เพราะทั้งสองรายการเป็น allowlist แบบครบถ้วน

### 10.13 เปลี่ยน URL ของ Backend ที่ Frontend เรียก

`VITE_API_URL` ถูก **แทนที่ลงในบันเดิลแบบสถิตตอน build** การตั้งค่าบน container nginx ที่กำลังรัน **ไม่มีผลใด ๆ** เพราะไม่มี `env.js` ไม่มีการแทนค่าตอน entrypoint และไม่มี `window.__ENV__`

**สำหรับการพัฒนา** — สร้าง `Frontend/web/.env`

```env
VITE_API_URL=http://localhost:8080
```

**สำหรับ Docker** — ส่งเป็น build arg

```bash
cd Frontend/web
VITE_API_URL=http://api.internal:8080 docker compose up --build
```

**ผลที่ตามมา: 1 image ต่อ 1 backend URL** ไม่สามารถเลื่อน artifact เดียวกันจาก staging ไป production ได้ ต้อง build ใหม่ หากเรื่องนี้สำคัญ ให้เพิ่มกลไก config ตอนรันไทม์ เช่น เสิร์ฟไฟล์ `/config.js` เล็ก ๆ ที่ตั้งค่า `window.__ENV__` แล้วอ่านใน `api.ts` โดยใช้ `VITE_API_URL` เป็นค่าสำรอง

**Reverse proxy โดเมนเดียวกัน** — หาก nginx เสิร์ฟทั้ง SPA และ `/api/*` ให้ตั้ง `VITE_API_URL=""` จะได้พาธสัมพัทธ์และเลี่ยงปัญหา CORS ไปเลย แต่ทำได้เพราะ `??` ไม่ดักสตริงว่างเท่านั้น **อย่าใช้ `"/"`** เพราะจะได้ slash ซ้อนกัน

### 10.14 เปลี่ยนการตั้งค่า JWT

```yaml
  api-gateway:
    environment:
      - JWT_SECRET=<สตริงสุ่มยาว ๆ>
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRES_HOURS=168
```

สร้าง secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> ### 🔴 ค่าเริ่มต้นทั้งสองไม่ปลอดภัย
> `"change-me-in-production"` ในโค้ด และ `"please-change-me"` ใน compose **ไม่มีการตรวจสอบตอนเริ่มระบบ** ใครที่รู้ค่าเริ่มต้นสามารถปลอม token ระดับ admin กับระบบที่ใช้ค่าเริ่มต้นได้ทันที
>
> **ไม่มี refresh token และไม่มีรายการเพิกถอน** token ใช้ได้เต็ม 168 ชั่วโมง `find_by_id` มีอยู่ในทั้งสอง store แต่ **ไม่เคยถูกเรียก** ดังนั้น token ของผู้ใช้ที่ถูกลบไปแล้วยังใช้ได้ต่อ และการเปลี่ยนบทบาทต้องล็อกอินใหม่ การเปลี่ยน `JWT_SECRET` จะทำให้ token ทั้งหมดใช้ไม่ได้ ซึ่งเป็นกลไกเพิกถอนเพียงอย่างเดียวที่มี

สำหรับการเซ็นแบบอสมมาตร (RS256) ต้องแก้ `auth/jwt_utils.py` เพราะโค้ดปัจจุบันส่ง secret เป็นสตริงเดียวให้ทั้ง `jwt.encode` และ `jwt.decode`

### 10.15 เปลี่ยนบัญชีเริ่มต้น

```yaml
  api-gateway:
    environment:
      - INITIAL_ADMIN_USERNAME=admin
      - INITIAL_ADMIN_PASSWORD=<รหัสผ่านที่แข็งแรง>
      - INITIAL_USER_USERNAME=user
      - INITIAL_USER_PASSWORD=<รหัสผ่านที่แข็งแรง>
      - INITIAL_USER_STAFF_ID=13266
```

กฎเกณฑ์
- การสร้าง admin ทำงาน **เฉพาะเมื่อยังไม่มี admin เลย** และจะข้ามพร้อมคำเตือนหากข้อมูลรับรองว่าง หรือมีชื่อผู้ใช้นั้นอยู่แล้วในบทบาทอื่น
- **`INITIAL_USER_STAFF_ID` ต้องมากกว่า 0** ไม่เช่นนั้นการสร้างผู้ใช้จะถูกข้ามไปเงียบ ๆ
- การเปลี่ยนรหัสผ่านของบัญชีที่มีอยู่ต้องแก้ที่ store โดยตรง เพราะ **ไม่มี endpoint สำหรับเปลี่ยนรหัสผ่าน**

### 10.16 แก้ป้ายชื่อ Service ใน Log

`logger.py:26` ของ **ทั้ง** retriever และ agent เขียนไว้ว่า

```python
log = configure_logging("api-gateway")
```

ทำให้ทุกบรรทัด log จากสอง service นี้ถูกติดป้ายว่า `api-gateway` ในคอลัมน์ `{extra[service]}` ซึ่งทำให้การรวบรวมหรือกรอง log ตาม service ใช้ไม่ได้ แก้เพียงคำเดียวในแต่ละไฟล์

```python
log = configure_logging("retriever")   # backend/services/retriever/logger.py:26
log = configure_logging("agent")       # backend/services/agent/logger.py:26
```

---

## 11. การจัดการฐานความรู้ (Knowledge Base)

### 11.1 นำเข้าเอกสาร

**ไม่มี CLI สำหรับนำเข้าจำนวนมาก และไม่มีโฟลเดอร์เอกสารต้นฉบับใน repo** เอกสารเข้าสู่ระบบผ่าน gRPC stream `UploadFile` **เท่านั้น** โดยมี HTTP endpoint ของ admin เป็นหน้าด่าน

**ผ่านหน้าเว็บ:** ล็อกอินเป็น admin → `/admin/files` → เลือกไฟล์และหมวด → อัปโหลด

**ผ่าน API**

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"a1234567"}' | jq -r .token)

curl -X POST http://localhost:8080/api/v1/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./User Manual.pdf" \
  -F "theme=manual"
```

**สิ่งที่เกิดขึ้น:** gateway อ่านไฟล์เข้าหน่วยความจำ → ส่งต่อไป retriever เป็น gRPC frame ขนาด 64 KB → PDF ถูกส่งไป Gemini เพื่อถอดความเป็น markdown (ไฟล์ข้อความจะตกไปเส้นทาง UTF-8 decode) → `RecursiveCharacterTextSplitter(550, 90)` → สร้าง embedding ด้วย e5-large → upsert เข้า Qdrant ด้วย UUID5 ที่กำหนดได้แน่นอน → สร้าง index BM25 ใหม่ → บันทึก metadata (ไม่ใช่ byte) ลง Mongo

**รูปแบบไฟล์ที่รองรับ: PDF และไฟล์ข้อความ (`.txt`, `.md`) เท่านั้น** ส่วน `.csv`, `.docx`, `.xlsx` จะตกไปเส้นทาง plain-text และถูก decode เป็น UTF-8 จาก byte ดิบ ทำให้ได้ chunk ที่เป็นขยะ ตัวเลือกไฟล์ในหน้าเว็บไม่มีตัวกรอง `accept` จึงไม่มีอะไรกันไว้ ให้แปลงเป็น PDF ก่อน

**การอัปโหลดชื่อไฟล์เดิมซ้ำจะเขียนทับ** เพราะ point ID คือ `uuid5(NS, "{collection}:{filename}_chunk_{i}")` chunk ที่เหมือนกันจึงได้ ID เดียวกัน **ไม่เกิดข้อมูลซ้ำ** แต่ก็ **ไม่ได้ลบ** chunk ส่วนเกินหากเวอร์ชันใหม่สั้นกว่าเดิม

### 11.2 สคริปต์บำรุงรักษา

ทั้งหมดรันจาก `/app` ภายใน container

```bash
# สร้าง embedding ใหม่ให้ทุก point ในที่เดิม ด้วยค่าตั้งปัจจุบัน (เฉพาะกรณีมิติเท่าเดิม)
docker compose exec retriever python -m scripts.reindex_collection --all
docker compose exec retriever python -m scripts.reindex_collection --collection manual --batch-size 32

# แบ่ง chunk ใหม่จากข้อความที่เก็บไว้ โดยไม่ต้องแปลง PDF ใหม่ (ใช้ตัวแบ่งแบบเข้าใจ markdown)
docker compose exec retriever python -m scripts.rechunk_collection \
  --collection manual --chunk-size 550 --chunk-overlap 90
docker compose exec retriever python -m scripts.rechunk_collection \
  --collection manual --source "User Manual.pdf"

# หา chunk ที่ซ้ำกัน — เป็นโหมดทดลอง (dry run) เป็นค่าเริ่มต้น
docker compose exec retriever python -m scripts.dedupe_collection --collection manual
docker compose exec retriever python -m scripts.dedupe_collection --collection manual --apply

# ดูจำนวน chunk ต่อชื่อไฟล์ต้นฉบับ
docker compose exec retriever python -m scripts.list_sources --collection manual
docker compose exec retriever python -m scripts.list_sources --collection manual --contains "flood"
```

> ### ⚠️ ต้อง restart ทุกครั้งหลังรันสคริปต์
> ```bash
> docker compose restart retriever
> ```
> index BM25 สร้างครั้งเดียวตอนเริ่มระบบ และรีเฟรชเฉพาะผ่าน `add_knowledge` / `delete_knowledge` สคริปต์เหล่านี้แก้ไข Qdrant **นอกช่องทางปกติ** จึงทิ้งให้ index ฝั่ง sparse ของ server ที่กำลังรันล้าสมัย

รายละเอียด `dedupe_collection`: ทำ normalize เนื้อหา (แปลงเป็นตัวพิมพ์เล็ก ตัดช่องว่างและอักขระที่ไม่ใช่คำ โดยคงช่วงอักขระไทยไว้) แบ่งกลุ่มด้วย SHA-256 และภายในแต่ละกลุ่มเก็บรายการที่ source ตรงกับ `--preferred-source` มากที่สุด (ค่าเริ่มต้นคือ `"User Manual"`) ถอยไปหา source ที่มีคำว่า `"user manual"` แล้วจึงเลือกชื่อที่สั้นที่สุด มี `--min-chars 220` เพื่อข้าม chunk สั้น ๆ และแสดง log ไม่เกิน 25 กลุ่ม

### 11.3 ตรวจสอบ Qdrant โดยตรง

```bash
# หน้า Dashboard
open http://localhost:6333/dashboard

# ข้อมูล collection (มิติ ระยะทาง จำนวน point)
curl http://localhost:6333/collections/manual | jq

# ไล่ดู point
curl -X POST "http://localhost:6333/collections/manual/points/scroll" \
  -H 'Content-Type: application/json' \
  -d '{"limit":5,"with_payload":true,"with_vector":false}' | jq
```

### 11.4 สำรองและกู้คืนข้อมูล

> ### 🔴 payload ใน Qdrant คือสำเนาเดียวของเอกสารทั้งหมด
> byte ของไฟล์ที่อัปโหลด **ไม่เคยถูกเก็บไว้** `retriever/db/mongo.py:16-17` ระบุว่า *"Saves file metadata without storing raw bytes in MongoDB."* การสูญเสีย `backend/data/qdrant_data/` เท่ากับสูญเสียฐานความรู้ทั้งหมด และไม่สามารถสร้างขึ้นใหม่จาก Mongo ได้

**แนะนำ: เก็บไฟล์ PDF ต้นฉบับไว้นอก repo** ในที่ที่คุณควบคุมและสำรองข้อมูลแยกต่างหาก

**สำรองแบบปิดระบบ** (ต้องหยุดก่อน เพราะเป็นไฟล์ฐานข้อมูลที่กำลังทำงาน)

```bash
docker compose down
Compress-Archive -Path backend\data\qdrant_data   -DestinationPath backups\qdrant_$(Get-Date -f yyyyMMdd).zip
Compress-Archive -Path backend\data\mongo_data    -DestinationPath backups\mongo_$(Get-Date -f yyyyMMdd).zip
Compress-Archive -Path backend\data\postgres_data -DestinationPath backups\postgres_$(Get-Date -f yyyyMMdd).zip
docker compose up -d
```

**สำรองแบบตรรกะขณะระบบทำงาน**

```bash
# Snapshot ของ Qdrant
curl -X POST "http://localhost:6333/collections/manual/snapshots"
curl -X POST "http://localhost:6333/collections/disaster/snapshots"

# Postgres
docker compose exec postgres pg_dump -U phonphai phonphai > backup.sql

# Mongo
docker compose exec mongo mongodump --db rag_db --archive > mongo.archive
```

**รีเซ็ตที่เก็บข้อมูล:** หยุดระบบ ลบไดเรกทอรีใต้ `backend/data/` แล้วเริ่มใหม่ อนึ่งการลบ `postgres_data` เป็น**วิธีเดียว**ที่จะทำให้ `init.sql` ทำงานอีกครั้ง

---

## 12. ระบบประเมินผล (Evaluation)

`backend/evaluation/` มีชุดเครื่องมือ 2 ชุดที่แยกจากกัน

### 12.1 การประเมิน QA แบบครบวงจร

เป็นแบบ black-box: ส่งคำถามทดสอบแต่ละข้อไปยัง API gateway ที่ **กำลังทำงานอยู่** แล้วให้คะแนนคำตอบ

```bash
cd backend
uv sync --project evaluation
uv run --project evaluation python evaluation/run_eval.py --input testcases.csv

# พร้อมตัวเลือก
uv run --project evaluation python evaluation/run_eval.py \
  --input evaluation/testcase/manual_csv.csv \
  --output-dir outputs/run_01 \
  --chat-endpoint http://localhost:8080/api/v1/chat/ \
  --judge-model google/gemini-2.5-flash \
  --limit 10
```

หรือผ่าน `backend/evaluation/Makefile`: `make eval EVAL_INPUT=testcase/manual_csv.csv`

**`OPENROUTER_API_KEY` จำเป็นต้องมี** ตัวรันจะโยน `ValueError` ถ้าไม่มี

**คอลัมน์ในไฟล์นำเข้า** (CSV / JSON / JSONL / XLSX)

| คอลัมน์ | จำเป็น | หมายเหตุ |
|---|---|---|
| `Question` | ต้องมีหัวคอลัมน์ | คำถามที่ LLM เรียบเรียง |
| `Human_question` | ต้องมีหัวคอลัมน์ | คำถามที่มนุษย์เรียบเรียง **ต้องมีอย่างน้อย 1 ใน 2 คอลัมน์ที่ไม่ว่างในแต่ละแถว** |
| `Ground_truth` | ✅ | ต้องไม่ว่าง |
| `Evidence` | ✅ | ข้อความอ้างอิงสำหรับคำนวณ precision/recall เชิงคำศัพท์ |
| `Source` | ✅ | ถูกแปลงจากรูปแบบ `"<ชื่อไฟล์> - หน้า N"` / `"- page N"` / `"- pages N-M"` |
| `format_based` | ✅ **โดยพฤตินัย** | ต้องเป็น `text` หรือ `image` เท่านั้น **README ของ evaluation ไม่ได้ระบุไว้** แต่ไฟล์ที่ขาดคอลัมน์นี้จะล้มเหลวทันที |
| `testcase_id` / `id` | — | ถ้าไม่มีจะใช้ลำดับแถวเริ่มจาก 1 |
| `Tags` | — | มีอยู่ในทุก CSV ที่ให้มา แต่ **ไม่เคยถูกอ่าน** |

**หมวด (theme) ไม่ใช่คอลัมน์** — ระบบอนุมานจาก **ชื่อไฟล์** ซึ่งต้องมีคำว่า `manual`, `disaster` หรือ `remedy`

การเข้ารหัส CSV ถูกตรวจจับอัตโนมัติจาก `utf-8-sig, utf-8, utf-16, cp874, tis-620, cp1252, latin-1` พร้อมกลไกตรวจจับ mojibake

**ไฟล์ทดสอบที่ให้มา** (`backend/evaluation/testcase/`): `disaster_csv.csv` (40 แถว), `manual_csv.csv` (40), `manual_csv_improve.csv` (40), `manual_test_1.csv` (1), `manual_test_3.csv` (3 — ค่าเริ่มต้นของ Makefile)

**เกณฑ์การให้คะแนน — CHIE+C** เป็นค่า boolean 5 ข้อพร้อมเหตุผลประกอบ

| ด้าน | ทิศทาง |
|---|---|
| **C**orrectness — ความถูกต้อง | ยิ่งสูงยิ่งดี |
| **H**elpfulness — ข้อมูลเสริมที่เกี่ยวข้อง | ยิ่งสูงยิ่งดี |
| **I**rrelevancy — ข้อมูลไม่เกี่ยวข้องจาก context | **ยิ่งต่ำยิ่งดี** |
| **E**xtraneousness — ข้อมูลที่ไม่มีใน context | **ยิ่งต่ำยิ่งดี** |
| **C**onciseness — ความกระชับ ไม่ซ้ำซ้อน | ยิ่งสูงยิ่งดี |

ที่มา: CHIE (Phatthiyaphaibun และคณะ, 2024, GenBench Workshop) — https://aclanthology.org/2024.genbench-1.10/ ส่วนด้าน `+C` (Conciseness) เป็นสิ่งที่โครงการนี้เพิ่มเข้ามาเอง

**โมเดลผู้ตัดสิน:** `google/gemini-3-flash-preview` (`eval_runner/settings.py:47-48`) ที่ temperature 0.0 เรียกผ่าน `urllib.request` ตรงไปยัง OpenRouter พร้อม JSON schema แบบเข้มงวดและ timeout 180 วินาที

> ⚠️ ค่าเริ่มต้นปรากฏใน **3 ที่ ด้วยค่า 2 แบบ** — `settings.py:47` (`gemini-3-flash-preview` ค่าที่มีผลจริง), `models.py:33` (`gemini-2.5-flash` ไม่ถูกใช้) และป้าย trace ของ LangSmith ที่ **ฝังตายตัว** ที่ `judge.py:112` (`gemini-2.5-flash`) ทำให้ trace ติดป้ายผิดทุกครั้งที่โมเดลจริงต่างออกไป

**สิ่งที่วัดเพิ่มเติม:** ความถูกต้องของการเลือก tool (`manual→search_user_manuals` เป็นต้น) และ precision/recall/F1 เชิงคำศัพท์ของ context ที่ค้นมาได้เทียบกับ `Evidence` (ข้อความภาษาไทยใช้ trigram อักขระ)

**ผลลัพธ์** — 4 ไฟล์ เขียนลง `--output-dir` **โดยอ้างอิงจาก CWD**

```
eval_rows.csv     eval_rows.json      # 1 แถวต่อ (testcase x question_type)
eval_summary.csv  eval_summary.json   # สรุปตาม (theme, question_type, format_based) + ภาพรวม
```

ไฟล์ CSV เป็น UTF-8 **พร้อม BOM** เพื่อให้เปิดใน Excel และแสดงภาษาไทยได้ถูกต้อง

ผลการรันย้อนหลังถูก commit ไว้ที่ `backend/outputs/` ได้แก่ `1`, `2`, `3NewChunk`, `4CleanDupData`, `5NewTest`, `6Disaster_1`, `7Disaster_2_bestConciseness`, `8Disaster_3_errorversion`, `Final/Disaster`, `Final/Manual`, `ิbest`

> **หมวด Remedy ประเมินแบบครบวงจรไม่ได้** เพราะ eval client **ไม่ส่ง auth header** คำถามที่มีรูปแบบรหัสคำร้องจึงไปชนด่าน 401 ของ gateway และ client แปลง HTTP error เป็น `RuntimeError` ที่ทำให้การรันทั้งชุดล้มเหลว สอดคล้องกับการที่ไม่มีไฟล์ testcase หมวด remedy เลย หากต้องการแก้ ให้เพิ่มการรองรับ JWT ใน `eval_runner/client.py`

> มีเมตริกความแม่นยำของการค้นคืน 6 ตัว (`file_precision`, `file_recall`, `file_f1_score`, `page_precision`, `page_recall`, `page_f1_score`) ที่ **ถูกคำนวณแล้วทิ้ง** ไม่ไปปรากฏในไฟล์ผลลัพธ์ใด ๆ

### 12.2 การปรับจูนการค้นคืน

เป็นแบบ white-box: import คลาส theme ของ retriever มาโดยตรง แล้วเรียก `_dense_retrieval` / `_sparse_retrieval` / `_fuse_rankings` / `reranker.predict` เอง

```bash
cd backend/evaluation
make retrieval-tuning          # กวาดค่า semantic weight x k
make retrieval-hybrid-tuning   # เฉพาะ hybrid ไม่มี rerank
make retrieval-rerank-tuning   # ตรึง alpha แล้วกวาดค่า rerank k
```

ตัวแปรใน Makefile: `RETRIEVAL_MAX_K` (30), `QDRANT_HOST` (localhost), `RERANK_DEVICE` (cuda), `HYBRID_WORKERS` (10), `RERANK_WORKERS` (1), `SEMANTIC_WEIGHT` (0.6)

ผลลัพธ์ประกอบด้วย `per_query_results.csv`, `recall_curve_summary.csv`, `recall_curve_points.csv`, `best_config_summary.csv`, `rerank_config_grid.csv` และกราฟ recall แบบ SVG ขนาด 1200×720 ที่สร้างขึ้นเอง

> ตัวรันที่รองรับ rerank ทั้งสองตัวจะบังคับ `--workers 1` เมื่อใช้ CUDA เพื่อเลี่ยง access violation ของ PyTorch/CrossEncoder บน Windows และตั้ง `RETRIEVER_RERANKER_SCOPE=thread` เมื่อ worker > 1

> ⚠️ `evaluation/pyproject.toml` ต้องการ `numpy>=2.0.0` ขณะที่ retriever ต้องการ `numpy<2.0.0` เนื่องจากสคริปต์ tuning import โค้ดของ retriever **มาในโปรเซสเดียวกัน** ความขัดแย้งนี้จึงเป็นเรื่องจริง นอกจากนี้โปรเจกต์ eval ยังตรึง torch แบบ CUDA **12.1** ขณะที่ image ของ retriever build ด้วย **12.4**

---

## 13. ความปลอดภัยและปัญหาที่ทราบแล้ว

### 13.1 สิ่งที่ต้องทำก่อนนำขึ้นใช้งานจริง

| ระดับ | รายการ |
|---|---|
| 🔴 | **เปลี่ยน API key** ที่แสดงไว้ใน [§6.0](#60-secret--backendenv) หากเอกสารนี้ถูก commit |
| 🔴 | **ตั้งค่า `JWT_SECRET`** — ค่าเริ่มต้นทั้งสองเป็นที่รู้กันทั่วไปและไม่มีการตรวจสอบ |
| 🔴 | **เปลี่ยน `POSTGRES_PASSWORD`** — ปัจจุบันเป็น `phonphai` แบบข้อความธรรมดา |
| 🔴 | **เปลี่ยนรหัสผ่านบัญชีเริ่มต้น** — ปัจจุบันเป็น `a1234567` ทั้ง `admin` และ `user` |
| 🔴 | **ห้ามเปิดพอร์ต 50051 / 50052 สู่ภายนอกเด็ดขาด** agent เชื่อค่า `user_role` และ `staff_id` ที่ส่งมาโดยไม่มีการยืนยันตัวตนของตัวเอง |
| 🟠 | เพิ่ม **rate limiting** — `POST /auth/login` ไม่ต้องยืนยันตัวตน ไม่มีการจำกัดอัตรา และรัน bcrypt **บน event loop** (เป็นทั้งเป้าหมายการเดารหัสผ่านและช่องทางทำให้ CPU หมด) |
| 🟠 | เพิ่ม **ขีดจำกัดขนาด request body** ที่ reverse proxy — `/files/upload` เก็บไฟล์ทั้งไฟล์ไว้ใน RAM โดยไม่จำกัด |
| 🟠 | วาง **TLS** ไว้หน้า gateway — gRPC ภายในเป็น plaintext โดยการออกแบบ แต่ช่องทางสาธารณะต้องไม่เป็นเช่นนั้น |
| 🟠 | เพิ่ม **timeout** — ไม่มีการตั้ง timeout บนการเรียก gRPC, LLM หรือการเชื่อมต่อฐานข้อมูลเลย ถ้าปลายทางค้าง คำขอจะค้างไปเรื่อย ๆ |
| 🟡 | แก้ `CORS` ให้ตรงกับ origin จริง ([§10.12](#1012-เปลี่ยน-cors-origins)) |
| 🟡 | พิจารณาปิด `/docs` และ `/openapi.json` เมื่อ deploy สู่สาธารณะ |
| 🟡 | Container **รันด้วยสิทธิ์ root** — ไม่มีคำสั่ง `USER` ใน Dockerfile ใดเลย |
| 🟡 | ระบบ log **ข้อความเต็มของผู้ใช้** พร้อม session id ชื่อผู้ใช้ และบทบาท ที่ระดับ INFO ซึ่งเป็นประเด็นด้าน PII |

### 13.2 บั๊กที่ยืนยันแล้ว

| ระดับ | ตำแหน่ง | ปัญหา |
|---|---|---|
| 🔴 | `agent/requirements.txt` | **`pymongo` ขาดหายไป** แต่ถูก import ที่ `db/chat_history.py:26` การตั้ง `CHAT_HISTORY_ENABLED=true` กับ backend mongo ตามค่าเริ่มต้นจะทำให้ **agent พังตอนเริ่มระบบ** ปัจจุบันถูกปิดบังไว้เพราะประวัติปิดอยู่ |
| 🔴 | `agent/core/bad_word.py:12-16` | `requests.get` ไปยัง GitHub แบบบล็อกและ **ไม่มี timeout ตอน import โมดูล** การเริ่ม container ขึ้นกับเครือข่ายภายนอก และการเชื่อมต่อที่ค้างจะทำให้เริ่มระบบไม่ได้ หากล้มเหลว การกรองคำหยาบภาษาอังกฤษจะหยุดทำงานเงียบ ๆ (ภาษาไทยยังทำงาน) |
| 🟠 | `api-gateway/routers/files.py` | ไม่มีคำสั่ง `except HTTPException: raise` ทำให้ **ข้อผิดพลาด 4xx ที่ตั้งใจทุกตัวกลายเป็น 500** พร้อมคำนำหน้า `"400: "` |
| 🟠 | `api-gateway/routers/files.py:89` | `HTTPException(status_code=502, detail=...)` ส่งค่า `Ellipsis` ของ Python ตรง ๆ ซึ่ง **แปลงเป็น JSON ไม่ได้** เมื่อ RPC ไป retriever ล้มเหลว จะเกิด error ตอน render แทนที่จะได้ 502 ที่สะอาด |
| 🟠 | `protos/*_pb2_grpc.py` | **เวอร์ชันไม่ตรงกัน** — stub หนึ่งต้องการ grpcio ≥ 1.80.0 อีกตัวต้องการ ≥ 1.76.0 และ `_pb2.py` ทั้งคู่ตรึง protobuf 6.31.1 ขณะที่ manifest ระบุเพียง `>=1.60.0` / `>=4.25.3` เสี่ยงเกิด `RuntimeError` ตอน import |
| 🟡 | `retriever/logger.py:26`, `agent/logger.py:26` | ทั้งคู่ติดป้าย service ตัวเองว่า **`"api-gateway"`** ทำให้การกรอง log เสียหาย |
| 🟡 | `retriever/db/mongo.py:11` | **ข้าม `Settings` ทั้งหมด** โดยใช้ `os.getenv("MONGO_URI", "mongodb://localhost:27017")` ซึ่งมีค่าเริ่มต้น*คนละค่า*กับ `config.py` การรันในเครื่องโดยไม่ตั้งตัวแปรจะชี้ไป localhost เงียบ ๆ |
| 🟡 | `agent/config.py:30` | `CHAT_HISTORY_WINDOW` ถูกประกาศและ log ไว้ แต่ **ไม่เคยถูกบังคับใช้** ค่าจริงที่ใช้คือ `min(max(turns,1),20)` |
| 🟡 | `retriever` `RERANK_TOP_K` | ไม่มีผลในการใช้งานจริง และค่าเริ่มต้นในโค้ด (5) ไม่ตรงกับค่าใน compose (10) |
| 🟡 | `api-gateway/routers/auth.py:86-100` | ตรวจก่อนแล้วค่อย insert โดยไม่ดัก `DuplicateKeyError` การสร้างพร้อมกันจึงออกมาเป็น 500 |
| 🟡 | `api-gateway/routers/chat.py:156-163` | การเขียนประวัติจาก SSE เป็น task แบบ fire-and-forget ที่ไม่ถูก await และไม่มีการอ้างอิงถือไว้ อาจถูกทิ้งเมื่อตัดการเชื่อมต่อหรือถูก GC |
| 🟡 | `evaluation/eval_runner/judge.py:112` | `ls_model_name` ฝังตายตัว ทำให้ trace ติดป้ายผิดเมื่อโมเดลผู้ตัดสินต่างออกไป |

### 13.3 ช่องว่างของ Frontend

| รายการ | รายละเอียด |
|---|---|
| **ไม่แสดงแหล่งอ้างอิงเลย** | frame `done` ส่งแหล่งอ้างอิงมาด้วย แต่ `onDone` ใน `useChatManager` ทิ้งทั้งหมด ไม่มี UI แสดงแหล่งอ้างอิงใด ๆ |
| **`cost` ถูกทิ้ง** | API คืนมาแต่ถูกตัดออกจาก type ฝั่ง Frontend |
| **ไม่จัดการ 401** | ไม่มี interceptor ไม่มี refresh ไม่มี redirect token หมดอายุแสดงเป็นฟอง error ทั่วไป ขณะที่ header ยังบอกว่าล็อกอินอยู่ |
| **โค้ดที่ไม่ถูกใช้** | `fetchMe()` และ `sendMessage()` แบบไม่สตรีม ถูก export แต่ไม่เคยถูก import |
| **การตรวจสิทธิ์ admin เชื่อฝั่ง client** | การแก้ `phonphai_user` ใน localStorage ทำให้หน้า admin แสดงผลได้ แต่ API ยังคืน 403 อยู่ดี จึงเป็นการข้ามในระดับหน้าตาเท่านั้น |
| **ไม่มี `.env.example`** | README อ้างถึงแต่ไม่มีไฟล์ใน repo |
| **คีย์ใน README ล้าสมัย** | ระบุว่าเป็น `phonphai_messages` แต่จริง ๆ คือ `phonphai_messages:<user_id\|anonymous>` |
| **คีย์ storage ซ้ำซ้อน** | `'phonphai_token'` เป็นสตริงเขียนซ้ำในทั้ง `AuthContext.tsx:5` และ `api.ts:5` โดยไม่มีค่าคงที่ร่วม การแก้ที่เดียวจะทำให้ระบบยืนยันตัวตนพังเงียบ ๆ |
| **regex รหัสคำร้อง 2 ชุดที่ไม่ตรงกัน** | `utils/skn.ts` (`[A-Z]{3}` ตัวคั่นไม่บังคับ ไม่สนตัวพิมพ์ สะท้อนฝั่ง backend) เทียบกับ `ChatMessage.tsx:12` (`[A-Z]{2,5}` บังคับขีดกลาง สนตัวพิมพ์ ใช้เพื่อแสดงผล) |
| **Admin เข้าไม่ได้จากมือถือ** | ลิงก์ `/admin/files` มีเฉพาะในแถบข้างของเดสก์ท็อป |
| **ไม่มี catch-all route** | URL ที่ไม่รู้จักแสดงหน้าว่าง |
| **หน้ากระพริบตอนโหลด** | `useMediaQuery` เริ่มต้นเป็น `false` ทำให้มือถือแสดงเลย์เอาต์เดสก์ท็อป 1 เฟรม |
| **ยกเลิก stream ไม่ได้** | ไม่มี `AbortController` ช่องพิมพ์ถูกล็อกจนกว่า stream จะจบ |
| **ไม่มี test, ไม่มี `.dockerignore`, ไม่มี CI** | |

### 13.4 เอกสารที่ไม่ตรงกับโค้ด

| ไฟล์ | ปัญหา |
|---|---|
| `README.md` ที่ root | อธิบาย **ChromaDB, `GEMINI_API_KEY`, `all-MiniLM-L6-v2`, `CHROMA_HOST`** ซึ่งถูกแทนที่ไปหมดแล้ว ไม่ได้กล่าวถึง service `postgres` และข้อความเรื่อง handler `@router.get("/")` ซ้ำใน `files.py` ก็ **ไม่เป็นความจริงอีกต่อไป** |
| `backend/README.md` | อ้างถึง `.env.example` ซึ่งไม่มีอยู่จริง |
| `Frontend/web/README.md` | อ้างถึง `.env.example` (ไม่มี) และระบุชื่อคีย์ localStorage ที่ล้าสมัย |
| `evaluation/README.md` | ไม่ได้ระบุ `format_based` ในรายการคอลัมน์ที่จำเป็น ทั้งที่จำเป็นจริง |
| `backend/data/chroma_data/` | ข้อมูลตกค้าง ไม่มีโค้ดอ้างอิง |

---

## 14. การแก้ปัญหาเบื้องต้น

**`docker compose up` ล้มเหลวที่ retriever พร้อม error เรื่อง GPU**
ไม่มี NVIDIA runtime ให้ใช้ ให้ลบบล็อก `deploy.resources` ([§10.6](#106-เปลี่ยน-reranker--รันโดยไม่ใช้-gpu)) และตั้ง `RERANK_DEVICE=cpu`

**Agent ปิดตัวทันทีพร้อม `ValidationError` ของ pydantic**
ไม่มี `OPENROUTER_API_KEY` ซึ่งไม่มีค่าเริ่มต้นและจำเป็นตั้งแต่ตอน import ตรวจว่ามี `backend/.env` และ compose แทนค่า `${OPENROUTER_API_KEY}` ได้จริง

**Agent พังพร้อม `ModuleNotFoundError: No module named 'pymongo'`**
คุณเปิด `CHAT_HISTORY_ENABLED=true` ให้เพิ่ม `pymongo>=4.6` ลงใน `backend/services/agent/requirements.txt` แล้ว build ใหม่ ([§10.2](#102-เปิดใช้งานประวัติการสนทนา))

**Container ค้างนานตอนเริ่ม แล้วมีคำเตือนเรื่องรายการคำหยาบ**
`core/bad_word.py` ดึงรายการคำจาก GitHub ตอน import โดย **ไม่มี timeout** เมื่อออฟไลน์หรืออยู่หลัง proxy จะทำให้ค้าง ให้เก็บรายการคำไว้ในเครื่องเอง หรือเพิ่ม `timeout=5`

**คำขอจากเบราว์เซอร์ล้มเหลวด้วย CORS error**
origin ของคุณไม่อยู่ใน allowlist ที่ฝังตายตัว ดู [§10.12](#1012-เปลี่ยน-cors-origins)

**ทุกคำขอตอบกลับเป็น 307**
คุณลืมใส่ `/` ท้าย `/api/v1/chat/` หรือ `/api/v1/files/`

**แชททำงานได้ แต่ค้นคำร้องแล้วบอกว่ายังไม่ได้ล็อกอินตลอด**
อาจเป็นเพราะไม่ได้ล็อกอินจริง หรือ token หมดอายุแล้วถูก **ลดสิทธิ์เป็นผู้ไม่ล็อกอินอย่างเงียบ ๆ** (เส้นทางแชทไม่คืน 401 เมื่อ token เสีย) ให้ตรวจด้วย `GET /api/v1/auth/me`

**ค้นคำร้องที่รู้ว่ามีอยู่ แต่ระบบบอกว่าไม่พบ**
คุณเป็นผู้ใช้ทั่วไปที่ `staff_id` ไม่ได้เป็นเจ้าของคำร้องนั้น ตรวจด้วย `SELECT DISTINCT "user" FROM issue_logs WHERE code = '...'` เทียบกับ `staff_id` ของบัญชีคุณ

**ผลการค้นหาไม่เกี่ยวข้องเลยหลังเปลี่ยนโมเดล embedding**
คุณเปลี่ยนตัวแปรรันไทม์แต่ไม่ได้เปลี่ยน build arg หรือไม่ได้ re-index ดู [§10.5](#105-เปลี่ยนโมเดล-embedding)

**ผลการค้นหาไม่สะท้อนการเปลี่ยนแปลงจากสคริปต์บำรุงรักษา**
index BM25 ล้าสมัย ให้ `docker compose restart retriever`

**`DELETE /api/v1/chat/history` คืน 404**
`CHAT_HISTORY_ENABLED` ไม่ได้ตั้งไว้ ซึ่งปิดเป็นค่าเริ่มต้นใน compose ([§10.2](#102-เปิดใช้งานประวัติการสนทนา))

**แก้ `init.sql` แล้วไม่มีอะไรเปลี่ยน**
`/docker-entrypoint-initdb.d/*` ทำงานเฉพาะเมื่อ data directory ว่าง ให้ `docker compose down` → ลบ `backend/data/postgres_data` → `docker compose up --build postgres`

**อัปโหลดไฟล์แล้วได้ 500 พร้อม `"detail": "400: Invalid theme..."`**
นั่น*คือ* error 400 เพียงแต่ `files.py` เขียนใหม่เป็น 500 ให้อ่านคำนำหน้า `"NNN: "` ที่อยู่ใน `detail`

**อัปโหลด PDF ไม่สำเร็จ**
`OPENROUTER_API_KEY` ว่างบน service **retriever** (มันโยน `ValueError` เฉพาะเส้นทาง PDF การค้นหายังทำงานได้โดยไม่มี key) หรือไฟล์เป็น `.docx`/`.xlsx` ซึ่งระบบไม่รองรับ

**ความรู้สึกว่าสตรีม "รอนานแล้วเทออกมาทีเดียว"**
เป็นไปตามการออกแบบ streaming เป็นการจำลอง — 2 ตัวอักษร / 25 ms **หลัง**สร้างคำตอบเสร็จแล้ว ([§3.3](#33-ข้อเท็จจริงสำคัญเชิงสถาปัตยกรรม))

**Frontend ยังชี้ไป backend เดิมหลังเปลี่ยน `VITE_API_URL`**
`VITE_API_URL` ถูกฝังตอน build ให้ build ใหม่: `docker compose up --build`

**Log จาก retriever และ agent ถูกติดป้ายว่า `api-gateway`**
เป็นบั๊กที่ทราบแล้ว ดู [§10.16](#1016-แก้ป้ายชื่อ-service-ใน-log)

---

## 15. แผนผังไฟล์

```
PhonphaiChatbot/
├── ARCHITECTURE.md              ← ฉบับภาษาอังกฤษ
├── ARCHITECTURE_TH.md           ← เอกสารฉบับนี้
├── README.md                    ⚠️ ล้าสมัย — อธิบายสถาปัตยกรรมก่อนย้ายมา Qdrant
│
├── backend/
│   ├── .env                     🔑 OPENROUTER_API_KEY, LANGCHAIN_API_KEY (gitignore ไว้)
│   ├── docker-compose.yml       ★ แหล่งอ้างอิงหลักของการ deploy
│   ├── Makefile                 up / down / restart / logs / ps / lint / format / lint-fix
│   ├── pyproject.toml           มีแค่ config ของ ruff ไม่มี dependency ไม่มี build system
│   ├── AUTH_BACKEND.md          คู่มือ auth store แบบสลับได้ (ขยายความไว้ที่ §10.1 ของเอกสารนี้)
│   │
│   ├── protos/
│   │   ├── chatbot.proto        agent.AgentService
│   │   ├── retriever.proto      retriever.RetrieverService
│   │   ├── *_pb2*.py            ⚠️ ไฟล์ที่ถูกสร้างขึ้น — ห้ามแก้ไข
│   │   └── setup.py             แพ็กเป็น phonphai-protos 1.0.0
│   │
│   ├── services/
│   │   ├── api-gateway/
│   │   │   ├── main.py          ★ app, lifespan, CORS (:110-115), การสร้างบัญชีเริ่มต้น
│   │   │   ├── config.py        ★ การตั้งค่าทั้งหมด — ไม่มี os.getenv ที่ใดเลย
│   │   │   ├── state.py         ตัวแปร global gRPCState
│   │   │   ├── auth/            jwt_utils, passwords (bcrypt), dependencies
│   │   │   ├── db/              base (AbstractUserStore) / mongo / postgres / __init__ (factory)
│   │   │   │   └── migrations/postgres_users.sql
│   │   │   └── routers/         auth.py, chat.py (SSE), files.py ⚠️ บั๊กรหัสข้อผิดพลาด
│   │   │
│   │   ├── agent/
│   │   │   ├── main.py          เริ่มระบบ: channel ไป retriever, ping Postgres, history store
│   │   │   ├── server.py        ★ Chat / ChatStream, streaming จำลอง (:175-184)
│   │   │   ├── config.py        ★ ตัวแปรสภาพแวดล้อมทั้งหมด
│   │   │   ├── core/
│   │   │   │   ├── graph.py     ★★ LangGraph, โมเดลฝังตายตัว (:43,:58,:61), safety override
│   │   │   │   ├── bad_word.py  ⚠️ ดึงข้อมูลจาก GitHub แบบบล็อกตอน import
│   │   │   │   ├── auth_context.py, session_context.py    ContextVar
│   │   │   ├── db/              postgres.py (คำร้อง), chat_history.py
│   │   │   ├── prompts/prompt.py ★★ SYSTEM_PROMPT — กฎการเลือกเส้นทางและสไตล์
│   │   │   └── tools/           ★ retriever_tool.py (4 tools), chat_history_tool.py
│   │   │
│   │   ├── retriever/
│   │   │   ├── main.py, server.py    ★ ทะเบียน theme (:16-19)
│   │   │   ├── config.py             ★ ค่าปรับการค้นคืนทั้งหมด
│   │   │   ├── db/qdrant.py          ★ embedding (ล็อกไว้ที่ CPU :40), collection, point ID
│   │   │   ├── db/mongo.py           ⚠️ ข้าม Settings และไม่เก็บ byte ต้นฉบับ
│   │   │   ├── themes/base.py        ★★ ขั้นตอน hybrid retrieval + RRF + rerank
│   │   │   ├── themes/disaster.py, manual.py
│   │   │   ├── utils/openrouter_parser.py   ★ Gemini แปลง PDF → markdown
│   │   │   ├── utils/prompt.py       prompt สำหรับแปลง PDF
│   │   │   └── scripts/              reindex / rechunk / dedupe / list_sources
│   │   │
│   │   └── sql_data/            Dockerfile + init.sql + dump.csv (39 แถว, 12 คำร้อง)
│   │
│   ├── evaluation/              eval_runner/ + สคริปต์ tuning 3 ตัว + testcase/ + Makefile
│   ├── outputs/                 ผลการประเมินย้อนหลังที่ commit ไว้ (10 การทดลอง)
│   └── data/
│       ├── postgres_data/       ⚠️ มีข้อมูลแล้ว — init.sql จะไม่ทำงานซ้ำ
│       ├── mongo_data/
│       ├── qdrant_data/         🔴 สำเนาเดียวของเอกสารทั้งหมด
│       └── chroma_data/         ⚠️ ไม่ได้ใช้แล้ว — ไม่มีโค้ดอ้างอิง ลบได้
│
└── Frontend/web/
    ├── Dockerfile               node:20-alpine → nginx:alpine, เขียน config SPA fallback ในตัว
    ├── docker-compose.yml       host 3000 → container 80, VITE_API_URL เป็น BUILD ARG
    ├── vite.config.ts           เรียบง่าย — ไม่มี proxy ไม่ตรึงพอร์ต
    └── src/
        ├── services/api.ts      ★★ ชั้นเชื่อมต่อ backend ทั้งหมด — ครบทั้ง 8 การเรียก ~165 บรรทัด
        ├── contexts/            AuthContext (localStorage + ซิงก์ข้ามแท็บ), LanguageContext
        ├── hooks/useChatManager.ts  ★ สถานะแชท + ประกอบ stream + บันทึกแยกตามผู้ใช้
        ├── utils/skn.ts         regex รหัสคำร้องฝั่ง client ที่สะท้อนของ backend
        ├── pages/               LoginPage, AdminFilesPage
        └── components/          DesktopView, MobileView, ChatMessage, ThinkingIndicator, ui/
```

**เริ่มดูที่ไหนเมื่อต้องการ…**

| เป้าหมาย | ไฟล์ |
|---|---|
| เข้าใจการ deploy | `backend/docker-compose.yml` |
| เปลี่ยนพฤติกรรมของ LLM | `agent/prompts/prompt.py`, `agent/core/graph.py` |
| ปรับคุณภาพการค้นคืน | `retriever/themes/base.py`, `retriever/config.py` |
| เพิ่ม endpoint | `api-gateway/routers/` + `main.py:118-120` |
| เชื่อมต่อ client | `Frontend/web/src/services/api.ts` (เป็น client อ้างอิงที่สมบูรณ์) |
| เปลี่ยนฐานข้อมูลบัญชี | `api-gateway/db/` + [§10.1](#101-เปลี่ยนฐานข้อมูลบัญชีผู้ใช้) |
| แก้ SQL ของคำร้อง | `agent/db/postgres.py` |

---

*จัดทำจากการอ่านโค้ดทั้งหมดใน `backend/` และ `Frontend/web/` ตามสภาพ ณ เวลาที่จัดทำ หากเอกสารนี้ขัดแย้งกับ `README.md` ที่ root ให้ยึด **เอกสารนี้ซึ่งสะท้อนโค้ดจริง***
