# CarePolicy Hub – Technical Overview

## 1. Tech Stack
- **Backend**: Flask (`app.py`)
- **RAG**: LlamaIndex (`rag_agent.py`)
- **LLM**: Groq `llama-3.1-8b-instant`
- **Embeddings**: HuggingFace `BAAI/bge-small-en-v1.5`
- **Re-ranking**: `BAAI/bge-reranker-base` via `SentenceTransformerRerank`
- **Frontend**: Single-page HTML/CSS/JS (`static/care-policy-hub.html`, TailwindCDN)
- **Auth**: Email/Password (SQLite+JWT), OAuth (Google/Microsoft via Authlib), UI: `static/auth.html`
- **Readers/Parsing**: PyMuPDF, Unstructured, Pandas CSV/Excel, Image OCR (best-effort)

## 2. Key Files & Directories
- `rag_agent.py`: Routing, retrieval, evidence filtering, response formatting, caching helpers
- `app.py`: Flask routes (chat, upload, feedback, history, analytics, view/download, auth & OAuth)
- `static/care-policy-hub.html`: Chat UI, Sources section, tenant selection, exact-page "Open"
- `static/auth.html`: Sign in/up with OAuth buttons and avatar preview
- `documents/`: Per-tenant document storage (e.g., `documents/RC/...`)
- `storage/`: Per-tenant vector store persistence (e.g., `storage/RC/...`)

## 3. Data Ingestion Flow
1. **Upload** (`POST /upload`)
   - Files saved to `documents/<tenant>/`
   - Rebuild tenant index (persist to `storage/<tenant>/`)
   - Invalidate response cache for that tenant
2. **URL** (`rag_agent.py:RAGAgent.ingest_url()`)
   - Fetches content, writes `*.txt` under tenant folder
   - Attempts incremental update; falls back to rebuild if needed
3. **Readers** (`SimpleDirectoryReader` w/ `file_extractor`)
   - PDFs: PyMuPDF or Unstructured
   - DOCX/PPTX/HTML: Unstructured
   - Images: ImageReader (OCR)
   - CSV/Excel: Pandas readers

## 4. Routing & Retrieval Flow
- **Tenant preselection**
  - Each tenant has an embedded descriptor (file list summary)
  - Query embedding uses stopword-removed text (`clean_for_route`)
  - Explicit tenant mention (e.g., "RC") overrides embeddings
  - If low-confidence and user clicks Skip (Auto-Select), route across all tenants via `RouterQueryEngine`
- **Retrieval**
  - Index retrieval `similarity_top_k=10`
  - Rerank to ~top 4 via `BAAI/bge-reranker-base`
- **Evidence-aware filtering**
  - Extract numeric/quoted tokens from the query
  - Prefer nodes containing these tokens; if none remain, abstain with a clear "not found in documents"

## 5. Response Formatting
- **Function**: `rag_agent.py:RAGAgent._format_rag_response()`
- **Prompt rules**
  - Summaries 1–2 sentences, concise
  - Detailed response: short, structured (bullets/numbers), no hallucinations, context-only
  - Keys allowlisted: `summary`, `detailed_response`, `key_points`, `suggestions`, `follow_up_questions`, `code_snippets`
  - JSON sanitized/extracted to avoid payload issues

## 6. UI Behavior & Sources
- **Greetings** (e.g., "hi", "hello"): `RAGAgent._detect_intent()` returns a short conversational reply. No routing/sources.
- **Sources** (built in `RAGAgent.get_response()` and rendered in `static/care-policy-hub.html`)
  - Each source includes: `filename`, `relative_path`, `relevance`, `page`
  - "Open" uses `/view/<tenant>/<relative_path>#page=<n>` (inline exact page for PDFs)
  - "Download" shown only when backend flags `is_download_intent=true`
- **Relevance display**: Normalized relative to top source; raw score shown in tooltip

## 7. Authentication
- **Email/Password** (`/auth/signup`, `/auth/signin`, `/auth/signout`, `/me`)
  - SQLite `users.db` with `email`, `name`, `password_hash`, `avatar_url`
  - Session cookie `auth_token` (JWT) set as HttpOnly
  - Avatar: DiceBear (no API key), seeded by email
- **OAuth via Authlib** (`/auth/login/<google|microsoft>`, `/auth/callback/<provider>`)
  - Upserts user, sets session cookie, redirects to `/`
- **Frontend enforcement**: `care-policy-hub.html` calls `/me` (with `credentials: 'include'`) and redirects to `/auth.html` on 401

## 8. Caching & History
- **History**: `history.json` maintained by `app.py` for chat history and analytics
- **Response cache**: Helpers in `rag_agent.py` (per-tenant invalidation on ingest)

## 9. Chunking Parameters
- **In `rag_agent.py`**
  - `Settings.chunk_size = 1024`
  - `Settings.chunk_overlap = 100`
- **Rationale**
  - 1024 captures sufficient policy/table context without too much drift
  - 100 overlap mitigates boundary loss while keeping index size/cost contained

## 10. Models & Cost/Performance
- **LLM**: Groq `llama-3.1-8b-instant` – fast, cost-effective, good JSON compliance
- **Embedding**: `BAAI/bge-small-en-v1.5` – light and quick for routing/retrieval
- **Re-ranker**: `BAAI/bge-reranker-base` – significantly boosts precision of top candidates at reasonable cost

## 11. Advantages / Disadvantages
- **Advantages**
  - Multi-tenant routing with explicit override and stopword-cleaned embeddings
  - Reranking for precision; numeric evidence filtering to avoid hallucinations
  - Exact-page source opening and nested path support
  - Conditional Download button driven by intent detection
  - Email/OAuth auth; portable avatar generation without dependencies
- **Disadvantages / Trade-offs**
  - Full rebuild on some uploads (simpler but costlier than fully granular incremental)
  - Numeric-only evidence filter can abstain when synonyms present without exact numbers
  - Small embedding model prioritizes speed over peak accuracy

## 12. Handling New Versions of Data
- Uploads or URL ingests update tenant storage and invalidate cache
- URL ingest attempts incremental update; falls back to rebuild on change risk
- (Planned) Manifest-based hashing to do strict per-file incremental updates across file and URL ingestion

## 13. User Flow
1. User authenticates (email/password or OAuth) → cookie set → redirected to `/`
2. If greeting/wish, return a short reply (no RAG)
3. Else: explicit tenant mention → direct; otherwise stopword-cleaned embedding preselect
4. If user clicked Skip (Auto-Select), route across all tenants
5. Retrieve → rerank → evidence filtering; abstain if no evidence
6. LLM formats concise JSON → UI renders answer, Sources (Open exact page), conditional Download
7. Helpful responses may be cached; cache invalidated on ingest

## 14. Environment Variables (.env)
- `GROQ_API_KEY` (required)
- `SECRET_KEY` (flask + default JWT secret)
- `JWT_SECRET` (optional; fallback to SECRET_KEY)
- `JWT_EXPIRES_MIN` (default 10080 = 7d)
- OAuth (optional):
  - `APP_BASE_URL` (default `http://127.0.0.1:5001`)
  - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
  - `MS_CLIENT_ID`, `MS_CLIENT_SECRET`

## 15. Operations
- **Run**: `python app.py`
- **Auth UI**: `GET /auth.html`
- **App UI**: `GET /` → redirects to `/auth.html` if not authenticated
- **Upload**: Use Upload tab in UI or `POST /upload`
- **Open file**: `/view/<tenant>/<relative_path>#page=<n>`
- **Download file**: `/download/<tenant>/<relative_path>`

## 16. Future Enhancements
- Strict manifest-based incremental ingestion pipeline (file hashing) across all ingest paths
- Hybrid retrieval (BM25 + vector) for exact-token queries and codes
- Per-tenant model/reranker overrides and adaptive chunking per content type
