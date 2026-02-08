## CarePolicy Hub — Recruiter Brief (STAR + Tech Overview)

### Elevator Pitch (30 seconds)
CarePolicy Hub is a Retrieval-Augmented Generation (RAG) assistant for healthcare policy documents. Users ask natural language questions and get fast, accurate, source-linked answers grounded in their own PDFs, DOCX, HTML, CSV, and images. It delivers sub-3s responses, page-level citations, and secure multi-tenant isolation.

### STAR Narrative
- Situation: Teams struggled to find precise guidance in large, frequently updated healthcare policy sets. PDFs and scanned tables made search slow and error-prone; accuracy and traceability were mandatory.
- Task: Build a multi-tenant, reliable, and fast RAG system that returns correct answers with page-level source attribution, supports secure authentication, and handles frequent document updates.
- Action:
  - Implemented LlamaIndex-based retrieval with BGE small embeddings; retrieved top-15, re-ranked with a cross-encoder (BGE reranker) to improve precision.
  - Extracted policy data from PDFs/DOCX/HTML/CSV; added Camelot table sidecars to boost numeric/code recall. Applied cleaning/normalization.
  - Built tenant routing via embedding + keyword overlaps, with explicit override and a router fallback for low-confidence queries.
  - Used Groq Llama-3.1 8B for fast, strictly formatted JSON answers; added evidence-aware filtering to reduce hallucinations.
  - Added per-tenant caching (file-signature validated) and history, with manifest-driven rebuilds on ingestion.
  - Provided Flask API endpoints, OAuth + JWT, and a simple Tailwind-based SPA for chat and document management.
- Result:
  - Average response time: 2–3 seconds; cache hit ratio ≈ 40%.
  - Significantly higher precision of top candidates after re-ranking; reduced hallucination complaints.
  - Smooth multi-tenant isolation and exact page open/download increased user trust.
  - Reliable rebuild + cache invalidation reduced stale-answer risks after ingests.

---

## Architecture & Tech Stack (What / Why / How)

- Backend: Flask
  - Why: Lightweight, ML-friendly, quick to ship. Team experience and ecosystem fit.
  - How: REST endpoints for chat, upload, auth, history; gunicorn in production.

- RAG Orchestration: LlamaIndex
  - Why: Purpose-built for document-heavy RAG; simple loaders, indexes, and query engines.
  - How: VectorStoreIndex per tenant; retrieval top_k=15; postprocessors include cross-encoder reranker.

- LLM: Groq Llama-3.1-8b-instant
  - Why: Fast, cost-effective, and solid JSON compliance for structured UI rendering.
  - How: Single prompt → strict JSON parsing with sanitization and allowlisted keys.

- Embeddings: HuggingFace BAAI/bge-small-en-v1.5
  - Why: Strong performance/size ratio, CPU-friendly, good for routing and recall.
  - How: Global embed model; per-tenant vector indices; used for routing and similarity.

- Re-ranking: BAAI/bge-reranker-base (cross-encoder)
  - Why: Substantial precision lift beyond cosine similarity; improves grounded answers.
  - How: Re-rank top-15 to top ≈ 5 before generation.

- Readers/Parsing: PyMuPDF, Unstructured, Pandas, Image OCR, Camelot (tables)
  - Why: Broad format coverage and better layout/table retention.
  - How: Best-effort extraction; numeric table sidecars appended to improve retrieval.

- Frontend: Single-page HTML/JS + Tailwind CDN
  - Why: Zero-build, fast iteration, minimal complexity.
  - How: Calls /me, /chat, /upload; renders sources with exact page open via /view.

- Auth: Email/Password (SQLite+JWT) + OAuth (Google/Microsoft via Authlib)
  - Why: Low-ops default; enterprise login ready.
  - How: HttpOnly JWT cookie; OAuth callbacks; WAL-mode SQLite for light concurrency.

---

## End-to-End Flows

### Ingestion Flow (Files)
1) Upload to /upload with tenant_id
2) Parse with PyMuPDF/Unstructured/Pandas/Image OCR; Camelot extracts tables
3) Clean/normalize text; build vector index (BGE embeddings) and persist per tenant
4) Invalidate per-tenant response cache based on file signatures

### Ingestion Flow (URL)
1) Submit URL to /upload
2) Trafilatura scrapes; .txt saved; optional full HTML snapshot fallback
3) Clean/normalize; index persists; cache invalidated

### User Query Flow
1) POST /chat with query
2) Intent detection (small talk / clarify / download / question)
3) Tenant routing: explicit mention → direct; else embeddings + keyword overlap → best tenant; router fallback if low confidence
4) Retrieval: similarity top_k=15 → cross-encoder re-rank to ≈ 5
5) Evidence-aware filtering (quoted phrases, numeric tokens, medical codes) and possible abstain
6) LLM (Groq 8B) produces strict JSON (summary, details, key_points, etc.)
7) Sources deduped with pages and URL; helpful responses cached

---

## Key Challenges & Mitigations
- PDF tables hurt recall
  - Mitigation: Camelot sidecar text, cleaning and normalization to enrich signals
- Multi-tenant routing misclassification
  - Mitigation: Blend of embedding cosine + keyword overlap, explicit tenant override, router fallback
- Hallucinations under weak evidence
  - Mitigation: Evidence-aware filtering and abstain; strict JSON formatting and key allowlist
- Stale answers after updates
  - Mitigation: Per-tenant cache invalidation keyed by file signatures; manifest-based rebuilds

---

## Performance & Reliability
- p50 ≈ 2–3s response time; cache hit ≈ 40%
- Reranker adds ~150–300ms but boosts precision notably
- WAL-mode SQLite for auth; indices persisted per tenant; defensive try/except around optional readers

---

## Alternatives Considered (FastAPI)
- Pros: Async I/O, auto validation (Pydantic), OpenAPI docs, WebSockets
- Why not now: Flask satisfied needs with lower complexity and faster time-to-ship
- Migration path: Run `/chat` on FastAPI first behind a reverse proxy; share `RAGAgent` module; incrementally port

---

## Future Enhancements
- Hybrid retrieval (BM25 + Vector) for exact-token/code queries
- Strict, per-file incremental indexing across all ingestion paths
- Per-tenant model/reranker overrides and adaptive chunking

---

## Talking Points & FAQs
- How do you ensure answer correctness? Evidence-aware filtering + re-ranking + page-level citations; abstain on weak evidence.
- How do you handle updates? Manifest-driven rebuilds and per-tenant cache invalidation using file signatures.
- Why this model stack? Groq 8B balances speed/cost/JSON compliance; BGE small + cross-encoder yields strong precision without heavy infra.
- How secure is data? HttpOnly JWT, tenant isolation, optional AV scan, encryption in transit, minimal PII in logs.


