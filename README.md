# PromptOps Gateway 🛡️

> **An Enterprise-Grade LLM Firewall and Observability Gateway.**  
> Securing generative AI workloads by preventing PII leaks, reducing API costs via semantic caching, and providing full token-level observability.

[![Live Demo](https://img.shields.io/badge/Live_Demo-Coming_Soon-emerald?style=for-the-badge)](#)
[![System Screenshot](https://img.shields.io/badge/View_Screenshot-Click_Here-blue?style=for-the-badge)](#)

---

## 🛑 The Enterprise AI Gap

As organizations rapidly adopt Large Language Models (LLMs), engineering teams face two critical bottlenecks:
1. **Data Security (DLP):** Passing unregulated user prompts to third-party APIs (like OpenAI or Groq) poses a massive risk of leaking Personally Identifiable Information (PII) or protected health data.
2. **Unpredictable Latency & Costs:** Sending duplicate or highly similar queries redundantly wastes tokens and increases response times for end-users.

**PromptOps Gateway** operates as a transparent proxy layer between the client applications and the LLM provider, mitigating these risks natively before the request ever leaves the enterprise network.

---

## ✨ Core Architecture & Features

### 1. PII Security Firewall (DLP)
Engineered an inline Data Loss Prevention (DLP) module utilizing **Microsoft Presidio** and **SpaCy** Named Entity Recognition (NER) models. 
- Automatically detects and scrubs sensitive entities (`PERSON`, `CREDIT_CARD`, `EMAIL_ADDRESS`, etc.) from incoming JSON payloads in real-time.
- Replaces restricted data with generic tokens (e.g., `<PERSON>`) before proxying the request to the upstream LLM.

### 2. Semantic Vector Cache
Implemented an intelligent caching layer using **ChromaDB** and `sentence-transformers`.
- Generates a local vector embedding of the incoming prompt.
- Performs a cosine-similarity search against historical requests. If a semantic match (e.g., "Tell me a feline joke" vs. "Tell me a cat joke") falls below the configured distance threshold, the gateway short-circuits the outbound API call and returns the cached response.
- Substantially reduces $L99$ latency to milliseconds and mitigates redundant token expenditure.

### 3. Asynchronous Observability & Analytics
Built a non-blocking analytics pipeline using **FastAPI BackgroundTasks** and **PostgreSQL (Supabase)**.
- Captures granular telemetry for every request: `latency_ms`, `token_count`, `was_pii_detected`, and `was_cache_hit`.
- Calculations execute strictly post-response, ensuring zero overhead on the critical path.
- Includes a bespoke **React Control Plane** (Dashboard) visualizing cache hit rates, PII interception metrics, and estimated cost savings using **Recharts**.

---

## 🗺️ System Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant G as PromptOps Gateway (FastAPI)
    participant S as PII Firewall (Presidio)
    participant V as Semantic Cache (ChromaDB)
    participant L as Upstream LLM (Groq)
    participant DB as Postgres (Supabase)

    C->>G: POST /v1/chat/completions
    G->>S: Scrub PII (NER Analysis)
    S-->>G: Sanitized Prompt
    G->>V: Generate Embedding & Query Threshold
    
    alt Cache Hit (Distance < 0.1)
        V-->>G: Return Cached Response
        G->>DB: Log Async (0 Tokens Cost)
        G-->>C: Response (Latency: <50ms)
    else Cache Miss
        V-->>G: No Match
        G->>L: Forward Request
        L-->>G: LLM Generation
        G->>V: Async Store Embedding + Response
        G->>DB: Log Async (Token Count & Cost)
        G-->>C: Response
    end
```

---

## 🛠️ Tech Stack

**Backend & Infrastructure**
- **Framework:** FastAPI, Uvicorn, Python 3.11+
- **Database:** PostgreSQL (Supabase), SQLAlchemy ORM
- **HTTP Client:** `httpx` (Asynchronous networking)

**AI / ML Layer**
- **NLP / NER:** Microsoft Presidio, SpaCy (`en_core_web_lg`)
- **Embeddings:** HuggingFace `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Vector Store:** ChromaDB (Local SQLite/Parquet backed)
- **Tokenization:** OpenAI `tiktoken`

**Frontend (Control Plane)**
- **Framework:** React, Vite
- **Styling:** Tailwind CSS (v4), Lucide React
- **Data Vis:** Recharts (High-density analytical charts)

---

## 🚀 Installation & Usage

### 1. Environment Setup
Clone the repository and configure your environment variables:
```bash
git clone https://github.com/yourusername/promptops-gateway.git
cd promptops-gateway

# Create .env file based on the template below
```

**`.env` Configuration:**
```env
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
DATABASE_URL=postgresql://postgres:[password]@db.your-supabase-url.supabase.co:5432/postgres
```

### 2. Backend Initialization
Set up the Python virtual environment and start the FastAPI proxy:
```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate | Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
python main.py
```
*Note: The first launch will synchronously download the 80MB embedding model from HuggingFace.*

### 3. Frontend Dashboard Initialization
In a new terminal tab, start the React telemetry dashboard:
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173` to view the control plane.

---

## 🔬 Engineering Highlights

- **Concurrency & Event Loop Optimization:** The FastAPI router uses standard `async/await` for high-throughput I/O proxying (via `httpx.AsyncClient`). However, heavy CPU-bound NLP tasks (SpaCy/Presidio) and local ChromaDB queries are actively decoupled from the main event loop using `fastapi.concurrency.run_in_threadpool`, preventing thread starvation and ensuring maximum parallel connection handling.
- **Dynamic Token Estimation:** During a semantic cache hit, the gateway bypasses the upstream LLM entirely. To maintain accurate cost analytics without API overhead, the system utilizes OpenAI's `tiktoken` to synthetically calculate the exact token cost saved by combining the `cl100k_base` encodings of the prompt and the cached response.
- **Zero-Latency Telemetry:** The PostgreSQL logging and vector cache writes are offloaded to `starlette.background.BackgroundTasks`. This ensures the critical path of the gateway returns the HTTP 200 response to the client immediately, delegating the IO-bound database `INSERT` operations to background worker threads.
