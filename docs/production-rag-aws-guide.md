# Production RAG on AWS: Limitations, Mitigations, Retrieval Choices, and Model Guidance

This document explains how to move the current tenant‑aware agentic RAG system to a production‑ready architecture on AWS. It covers the practical limitations we addressed, recommended AWS services for retrieval, how bi‑encoders (sentence-transformers) and cross‑encoders work in our project, and guidance on embeddings, chunking, and reranking with trade‑offs and examples.

---

## 1) Core limitations and how we mitigate them

- **[Vague/small‑talk queries triggering RAG]**
  - Mitigation: Early intent detection in `rag_agent.py::_detect_intent()` returns small‑talk replies or clarification prompts instead of retrieving. This reduces hallucinations and wasted retrieval.

- **[Tenant routing ambiguity]**
  - Mitigation: Normalized routing text (`_normalize_for_routing()`), explicit tenant alias detection (`_resolve_tenants_in_text()`), and multi‑tenant merge when multiple tenants are mentioned.

- **[Noisy queries hurting retrieval]**
  - Mitigation: Stopword stripping for routing similarity only. Original query is preserved for retrieval + generation.

- **[Poor source clarity]**
  - Mitigation: De‑duplicate sources, strip sidecars, limit to top‑2, and attach original URLs for URL ingests so the UI opens real sources.

- **[URL ingestion misses content]**
  - Mitigation: Robust fallback fetch (save `.source.html`, strip tags) when the first extractor returns too little.

- **[Hallucinations in generation]**
  - Mitigation: Strict grounding and refusal rules in the generation prompt (`_format_rag_response()`), plus re‑ranking to improve context precision.

---

## 2) AWS production architecture options (retrieval layer)

Choose a vector store that integrates well with AWS, scales, and supports filters/metadata.

- **[Amazon OpenSearch Service (Vector)]**
  - Pros: Managed, scalable shards/replicas, k‑NN (Faiss/HNSW), filters on metadata, VPC support.
  - Cons: Cost and cluster tuning complexity.
  - Fit: Great default for multi‑tenant vector retrieval + metadata filters (e.g., `tenant_id`, `doctype`).

- **[Amazon Aurora PostgreSQL with pgvector]**
  - Pros: SQL + vectors, strong consistency, transactional ingestion, easy joins with metadata.
  - Cons: kNN speed vs dedicated vector DB may lag at very large scale; needs careful indexing.
  - Fit: Excellent when you already need relational joins and strong transactional semantics.

- **[Amazon DynamoDB + external ANN (optional)]**
  - Pros: Serverless key/metadata store, predictable scaling. Combine with Lambda + Faiss for custom ANN.
  - Cons: More DIY work; operational complexity.

- **[Amazon Bedrock Knowledge Base]**
  - Pros: Managed ingestion, chunking, embedding, retrieval. Tight integration with Bedrock models.
  - Cons: Less control over pipeline internals; tenant partitioning needs careful design.
  - Fit: If you want managed RAG and can align to its conventions.

Recommended default: **OpenSearch** for vector search + **S3** for raw artifacts, with **Lambda** ingestion pipeline and **Step Functions** for batch jobs. Use **Aurora** if you need relational joins/transactions with vectors.

---

## 3) Ingestion pipeline on AWS (proposed)

```mermaid
flowchart LR
S3[S3: raw docs & snapshots] --> L1[Lambda: extract & chunk]
L1 --> E1[Embeddings (SageMaker/BYO HF)]
E1 --> OS[OpenSearch: vector + metadata]
L1 --> M[Aurora/DynamoDB: metadata, manifests]
CF[CloudFront] --> API[API Gateway]
API --> A1[ECS/Fargate or Lambda: RAG API]
A1 --> OS
A1 --> M
A1 --> S3
CW[CloudWatch/ X-Ray] -->|logs/metrics| A1
```

- **Documents**: Store originals and snapshots in `S3://<bucket>/tenants/<tenant>/`.
- **Extraction**: Lambda or ECS task fetches, cleans, normalizes, and chunks.
- **Embeddings**: Use a managed endpoint (SageMaker) or local in ECS (CPU/GPU) for batch embedding.
- **Indexing**: Upsert vectors and metadata into OpenSearch; write manifests to Aurora/DynamoDB.
- **Observability**: Emit chunk counts, token counts, error rates, and latency to CloudWatch, log slow queries.

---

## 4) Chunking and overlap: how and why

- **Current settings**: `chunk_size = 1024` chars, `chunk_overlap = 100` in `rag_agent.py`.
- **Why**: 1024‑char chunks capture definitions + short procedures without diluting semantic focus; 100 overlap preserves context across boundaries.
- **When to adjust**:
  - If answers miss detail: raise to 1200–1600, keep overlap 80–120.
  - If retrieval feels noisy: lower to 800–1000, reduce overlap to 60–100.
- **Tenants/doc types**: Allow per‑tenant overrides via metadata policies (e.g., larger chunks for narrative PDFs, smaller for FAQ glossaries).

---

## 5) Sentence-transformers vs cross-encoders (how they work here)

- **Bi‑encoder (sentence‑transformers)**
  - Example: `BAAI/bge-small-en-v1.5` (384‑d) used in our project for embeddings.
  - How it works: Encode query and chunks independently into vectors. Retrieval uses ANN (kNN) over these vectors.
  - Pros: Very fast at query time; precompute chunk embeddings once. Scales to millions of chunks.
  - Cons: Coarse similarity—can retrieve slightly off‑topic chunks.

- **Cross‑encoder (re‑ranker)**
  - Example: `BAAI/bge-reranker-base` used to re‑rank top K retrieved chunks.
  - How it works: Concatenate query + chunk and score relevance with a transformer jointly (no vector index).
  - Pros: Much higher precision on the top results.
  - Cons: Slower; run only on a small candidate set (e.g., top 20).

- **In our pipeline**
  - Step 1: Use bi‑encoder vectors to retrieve top N (e.g., 20) candidates.
  - Step 2: Cross‑encoder re‑ranks to top 5 for generation context.
  - Outcome: Speed of bi‑encoder + precision of cross‑encoder.

---

## 6) Choosing embeddings and reranking models

- **Embeddings (bi‑encoder)**
  - `BAAI/bge-small-en-v1.5` (384‑d, fast, good quality). Great default for CPU.
  - `BAAI/bge-base-en-v1.5` (768‑d, better accuracy, ~2x vector size). Use if recall is lacking.
  - `intfloat/e5-base-v2` (768‑d) or `gte-base` variants: strong alternatives.
  - Limitations: Larger dimension → bigger index RAM and slower ANN. Domain adaptation may require fine‑tuning.

- **Reranker (cross‑encoder)**
  - `BAAI/bge-reranker-base` (strong general reranker). Consider `bge-reranker-large` if you can afford latency.
  - Limitations: Latency grows linearly with candidate count; keep candidates small (10–30).

- **Generation LLM**
  - Current: Groq `llama-3.1-8b-instant` (low latency, good adherence).
  - AWS option: Bedrock models (e.g., Claude, Llama via Bedrock) for VPC/private routing.
  - Limitations: Larger models increase cost and latency; guardrails still required.

---

## 7) Example retrieval configurations

- **Balanced (current‑like)**
  - Chunk: 1024 / 100 overlap
  - Retrieve top_k: 20 → Rerank to 5
  - Embeddings: `bge-small-en-v1.5`
  - Reranker: `bge-reranker-base`

- **Precision‑biased**
  - Chunk: 900 / 80 overlap
  - Retrieve top_k: 12 → Rerank to 5
  - Embeddings: `bge-base-en-v1.5`
  - Reranker: `bge-reranker-base`

- **Recall‑biased**
  - Chunk: 1400 / 120 overlap
  - Retrieve top_k: 30 → Rerank to 7
  - Embeddings: `bge-base-en-v1.5`
  - Reranker: `bge-reranker-large` (if latency budget allows)

---

## 8) Metadata and filters (multi‑tenant)

- Index metadata: `tenant_id`, `doctype` (pdf, url, docx, csv), `path`, `title`, `created_at`, `effective_date`, tags.
- Use filters to restrict retrieval by tenant(s) detected from the query (or user selection) to avoid cross‑tenant leakage.
- For OpenSearch, store metadata in the same document as the vector field; query with vector + filter.

---

## 9) Latency, scaling, and costs

- **Hot path (per query)**
  - Embed query (bi‑encoder) → ANN search → re‑rank top‑K → LLM answer.
- **Budgeting**
  - ANN (OpenSearch): 10–50 ms typical with tuned HNSW and cache.
  - Rerank (5–20 items): 30–120 ms on CPU; faster on small GPU.
  - LLM: 200–1000+ ms depending on model and token count.
- **Scaling**
  - OpenSearch: Scale shards/replicas; enable UltraWarm/ISM for cold tiers; set HNSW params (M, efSearch) per index.
  - ECS/Fargate for stateless RAG API; autoscale on CPU/QPS.
  - SageMaker endpoint for embeddings/reranker if needed; or run them on ECS with CPU/GPU.

---

## 10) Observability and quality

- Track: retrieval hit rate, RAG groundedness, top‑K overlap, reranker lifts, latency breakdown, error rates.
- Add feedback API (thumbs up/down) + sample storage to S3.
- Periodically evaluate with a small set of labeled Q/A to regress quality.

---

## 11) Security & governance

- VPC‑only access for OpenSearch/Aurora.
- S3 bucket policies scoped by tenant prefix.
- KMS encryption at rest for S3, OpenSearch, and Aurora.
- Audit/logging in CloudWatch + retention policies.
- PII/PHI detection (Macie/Comprehend Medical) before indexing if needed.

---

## 12) Worked example: retrieval + reranking

- Query: "What are the esMD onboarding steps for RCs?"
- Candidates (ANN): Top 20 chunks from `tenant_id=RC`.
- Reranker scores each `concat([query] + [chunk])` → select top 5.
- Generation prompt only sees those 5. Sources limited to top‑2 deduped doc names/URLs.

```json
{
  "query": "What are the esMD onboarding steps for RCs?",
  "retrieval": {
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "k": 20,
    "filters": {"tenant_id": "RC"}
  },
  "reranking": {
    "model": "BAAI/bge-reranker-base",
    "top_n": 5
  },
  "generation": {
    "model": "llama-3.1-8b-instant",
    "guardrails": ["no external knowledge", "cite sources"]
  }
}
```

---

## 13) Trade‑offs summary

- **[Embeddings]**
  - Small models: fast, cheap, lower recall.
  - Base/large models: better recall/semantic capture, higher cost and latency.
- **[Chunks]**
  - Large: fewer documents to fetch, but more noise per chunk.
  - Small: precise and composable, but may fragment context and raise k.
- **[Reranker]**
  - Base: good precision with modest latency.
  - Large: best precision, highest latency—cap top‑K accordingly.

---

## 14) Checklist to go live on AWS

- **[Data]** S3 bucket per environment; lifecycle rules; tenant prefixes.
- **[Index]** OpenSearch domain sized for vectors; HNSW tuned; index template with vector + metadata mappings.
- **[Ingest]** Lambda/ECS job; retries; backoff; DLQ.
- **[API]** ECS/Fargate service or Lambda; VPC; private subnets; autoscaling.
- **[Models]** Embeddings/reranker on SageMaker or ECS; health checks; autoscaling.
- **[Secrets]** AWS Secrets Manager for keys.
- **[Observability]** CloudWatch dashboards; alarms on p95 latency, error rate; quality eval jobs.
- **[Security]** VPC, SGs, KMS, IAM least privilege, audit logs.

---

## 15) Appendix: suggested OpenSearch mappings

```json
{
  "mappings": {
    "properties": {
      "tenant_id": {"type": "keyword"},
      "doctype": {"type": "keyword"},
      "path": {"type": "keyword"},
      "title": {"type": "text"},
      "created_at": {"type": "date"},
      "tags": {"type": "keyword"},
      "content": {"type": "text"},
      "vector": {
        "type": "dense_vector",
        "dims": 384,
        "index": true,
        "similarity": "cosine",
        "method": {"name": "hnsw", "engine": "nmslib", "parameters": {"ef_construction": 128, "m": 16}}
      }
    }
  }
}
```

---

## 16) TL;DR recommendations

- **OpenSearch** for vector search + **S3** for source storage.
- **bge-small-en-v1.5** for embeddings → upgrade to **bge-base** if recall lacks.
- **bge-reranker-base** for top‑K precision.
- Chunk 1000±200 with 80–120 overlap; evaluate and tune per tenant.
- Strong intent gating, explicit tenant aliases, top‑2 deduped sources.
- CloudWatch observability + feedback loop for continuous quality.

---

## 17) AWS services to use in production (cost‑effective, secure, low‑latency, robust)

- **[Amazon OpenSearch Serverless (Vector)]**
  - Managed vector search with HNSW, scales seamlessly; VPC endpoints supported.
  - Use data access policies per tenant and index‑level field security for `tenant_id`.
  - Keep vectors in a "hot" collection; move raw artifacts to S3.

- **[Amazon Bedrock Knowledge Bases] (optional)**
  - Managed ingestion + retrieval if you prefer a turnkey pipeline. Evaluate if its chunking/filters meet your multi‑tenant needs.

- **[AWS Lambda + DLQ]**
  - Ingestion workers for URL/PDF processing. Configure **DLQ** (SQS) for failed ingests. Use **EventBridge** schedules for re‑crawls.

- **[Amazon S3]**
  - Store raw docs, HTML snapshots, and manifests under `s3://bucket/tenants/<tenant>/...`.
  - Enable bucket policies/KMS, lifecycle transitions (e.g., to IA/Glacier) and object locks if governance requires.

- **[API layer: Amazon API Gateway + Lambda or ECS/Fargate]**
  - Low‑latency, stateless RAG API. Prefer ECS/Fargate for steady traffic; Lambda for bursty workloads.

- **[Secrets & Security]**
  - AWS Secrets Manager for LLM keys; VPC‑only subnets; KMS encryption (S3/OS/Aurora); IAM least privilege.

- **[Observability]**
  - CloudWatch metrics/dashboards + logs; X‑Ray tracing for hot path (embed → ANN → rerank → LLM).

---

## 18) Generation model placement: AWS vs. external (Groq) vs. self‑host

- **[Amazon Bedrock (Claude, Llama, etc.)]**
  - Pros: VPC/private connectivity, enterprise guardrails, consolidated billing.
  - Cons: Model/menu varies by region; per‑token pricing applies.
  - Use when: Compliance and private networking are primary.

- **[Groq (external)]**
  - Pros: Very low latency; cost‑effective tokens for certain models; great for interactive UX.
  - Cons: External egress; ensure data policy alignment; add retry/backoff.
  - Use when: Latency is king and external routing is acceptable.

- **[Self‑host on ECS/SageMaker]**
  - Pros: Full control; fixed capacity economics; private networking.
  - Cons: Ops overhead; GPU capacity planning; rolling updates.
  - Use when: You need strict residency/control and predictable throughput.

Decision pattern: Start with Bedrock (private) or Groq (latency) → add self‑hosted for steady high‑QPS tenants.

---

## 19) Cost methodology and rough examples

Costs vary by region/traffic. Use this as an approach, not a quote. Keep telemetry to validate real p95s and token counts.

- **Assumptions (example)**
  - 100k queries/month; avg 1.2k tokens generated per answer; 20 candidates re‑ranked per query.
  - Vector index holds 2M chunks (384‑d) across tenants; S3 stores 200 GB raw.

- **Components to model**
  - OpenSearch Serverless: OCU‑hours for compute + GB‑month for storage. Retrieval ops scale mainly with QPS and efSearch.
  - Embeddings/Reranker: per‑request CPU/GPU time (SageMaker or ECS) or external API unit costs.
  - LLM generation: per‑token cost (Bedrock/Groq) or GPU hours (self‑host).
  - S3/transfer: storage GB‑month + egress for snapshots/downloads.
  - API/compute: ECS task hours or Lambda GB‑seconds.

- **Illustrative monthly ballpark (order‑of‑magnitude; plug your prices):**
  - OpenSearch Serverless vectors (hot): low hundreds USD.
  - S3 (200 GB, standard + some GETs): tens of USD.
  - Embedding + reranking (CPU with moderate parallelism): tens to low hundreds USD.
  - LLM tokens (100k × 1.2k = 120M output tokens + input): depends on model/provider; could be mid‑hundreds to low thousands USD.
  - API/runtime (ECS small cluster): tens to low hundreds USD.

To refine, replace with your region’s current prices and measured token/QPS metrics; run a week‑long canary and extrapolate.

---

## 20) Recommended production blueprint

- **[Retrieval]** OpenSearch Serverless (Vector) with `tenant_id` filters and HNSW tuned; S3 for raw.
- **[Embeddings]** `bge-small-en-v1.5` (384‑d) to start; upgrade to `bge-base` if recall lacking.
- **[Reranking]** `bge-reranker-base` over top‑20 → top‑5 context.
- **[Generation]** Start with Bedrock (VPC) or Groq (latency); later add self‑host for steady tenants.
- **[Ingest]** Lambda with DLQ + EventBridge schedules; snapshots to S3; per‑tenant manifests.
- **[Security]** VPC‑only, KMS everywhere, IAM least privilege, Secrets Manager.
- **[Ops]** CloudWatch metrics, dashboards, alarms; cost allocation tags by tenant.
