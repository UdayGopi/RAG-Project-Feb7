# RAG Pipeline: Ingestion, Chunking, Embeddings, Retrieval & Generation – 40 Q&As

End-to-end questions and answers for the CarePolicy RAG Hub pipeline.

---

## INGESTION

**1. How does document ingestion work in this project?**  
Documents are ingested **per tenant**. Each tenant has a folder under `documents/<tenant_id>/`. Files are uploaded via the `/upload` API (multipart form with `tenant_id` and `files`) or URLs via `ingest_url()` (allowed domains: www.cms.gov, esmdguide-fhir.cms.hhs.gov). After upload, a manifest is scanned; if files changed, the vector index for that tenant is rebuilt.

**2. What file types are supported for ingestion?**  
PDF, DOCX, PPTX, HTML, TXT, CSV, XLSX, XLS, and images (PNG, JPG, JPEG, TIFF) when the corresponding LlamaIndex readers are available. PDF and DOCX are always supported via PyPDF/Unstructured; others depend on optional loaders (PyMuPDF, UnstructuredReader, ImageReader, PandasCSVReader, PandasExcelReader).

**3. Where are ingested documents stored?**  
Locally under `documents/<tenant_id>/`. Optionally, files can also be uploaded to S3 when `STORAGE_BACKEND=s3` and `S3_BUCKET` are set; the app still uses local (or mounted) paths for indexing.

**4. How does URL ingestion work?**  
When `TrafilaturaWebReader` is available, `ingest_url(tenant_id, url)` checks the URL against `ALLOWED_DOMAINS` (e.g. www.cms.gov, esmdguide-fhir.cms.hhs.gov), fetches and extracts main content, saves it as a `.txt` file in the tenant folder, and optionally does an HTML fallback for short extractions. In the ultralight image (no Trafilatura), URL ingestion is disabled.

**5. What happens after new files are uploaded?**  
The app compares the current file list (path, size, mtime, SHA256) with a stored manifest. If there are changes (added/deleted), the tenant’s vector index is removed and rebuilt from all documents in that tenant folder, and the response cache for that tenant is invalidated.

**6. What is the “cleaning” step during ingestion?**  
An optional text-cleaning pass before chunking: Unicode normalization (NFKC), line-ending normalization, de-hyphenation across line breaks, removal of control characters, collapse of excessive blank lines, and removal of repeated short boilerplate lines (e.g. headers/footers). Controlled by `CLEANING_ENABLED` (default true).

**7. How are tables from PDFs used in ingestion?**  
When `TABLE_EXTRACT_ENABLED` is true and Camelot is available, tables are extracted from PDFs (lattice then stream), converted to text rows, saved as sidecar files (e.g. `pdf_path.tables.txt`), and added as extra `Document` objects with metadata (`source_pdf`, `file_path`). This improves recall for tabular data.

**8. What is a “tenant” in ingestion?**  
A tenant is a logical namespace (e.g. HIH, RC). Each tenant has its own folder under `documents/` and its own vector index under `storage/`. Documents are always associated with a tenant via `tenant_id` on upload.

---

## CHUNKING

**9. What chunking strategy is used?**  
LlamaIndex’s default text splitter is used, driven by **global Settings**: `Settings.chunk_size = 1024` and `Settings.chunk_overlap = 100`. So chunks are up to 1024 characters (or tokens, depending on the splitter), with 100-character overlap between consecutive chunks.

**10. Why 1024 and 100 for chunk size and overlap?**  
1024 keeps chunks large enough for coherent context (e.g. paragraphs/sections) while fitting model context limits. Overlap of 100 reduces the risk of splitting important phrases at boundaries and helps retrieval at chunk edges.

**11. Where is chunking applied?**  
Chunking is applied when building the vector index: `VectorStoreIndex.from_documents(documents)`. LlamaIndex uses the configured `Settings.chunk_size` and `Settings.chunk_overlap` (and default text splitter) to turn each document into nodes before embedding and storing.

**12. Can chunk size and overlap be changed?**  
Yes, by changing `Settings.chunk_size` and `Settings.chunk_overlap` in `rag_agent.py` (or via a future env-based config). They are set in `RAGAgent.__init__` before indexes are built.

**13. Is chunking done per document or per tenant?**  
Per document. Each document is split into chunks (nodes); all chunks from all documents in a tenant are stored in that tenant’s single vector index.

---

## EMBEDDINGS

**14. What embedding model is used by default?**  
Default: **HuggingFace** `BAAI/bge-small-en-v1.5` (via `llama-index-embeddings-huggingface`). It runs locally and requires PyTorch, so it is not used in the ultralight Docker image.

**15. What embedding option is used in the ultralight image?**  
When `EMBEDDING_PROVIDER=openai` and `OPENAI_API_KEY` is set, the app uses **OpenAI** `text-embedding-3-small` (API-based). No local model or PyTorch is needed.

**16. How is the embedding model selected?**  
In `rag_agent.py`, `_get_embed_model()` reads `EMBEDDING_PROVIDER`. If it is `openai`, it returns `OpenAIEmbedding(model="text-embedding-3-small")`; otherwise it returns `HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")`.

**17. Where are embeddings used?**  
(1) When building the index: every chunk is embedded and stored in the vector store. (2) At query time: the user query (or a routing-normalized version) is embedded for tenant preselection (cosine similarity with tenant descriptors). (3) For retrieval: the query is embedded and compared to chunk embeddings for similarity search.

**18. What is the “tenant descriptor” embedding?**  
For each tenant, a short text is built (e.g. “Tenant: HIH. Files: file1.pdf, file2.docx”) and embedded once. At query time, the query embedding is compared to these tenant embeddings to choose the best tenant(s) before running the full retrieval.

---

## RETRIEVAL

**19. How does retrieval work for a single tenant?**  
For a chosen tenant, the corresponding **query engine** (built from that tenant’s vector index) is used. The query (optionally prefixed with “keywords: … question: …”) is run against the index with `similarity_top_k=10` and `similarity_cutoff=0.5`. Retrieved nodes can then be reranked (if the reranker is available).

**20. What is similarity_top_k and similarity_cutoff?**  
`similarity_top_k=10`: retrieve up to 10 most similar chunks. `similarity_cutoff=0.5`: only keep chunks with similarity score ≥ 0.5. Both are set on the per-tenant query engine in `rag_agent.py`.

**21. Is a reranker used?**  
If available (sentence-transformers installed, not in ultralight), **SentenceTransformerRerank** with model `BAAI/bge-reranker-base` and `top_n=3` is used. It takes the top candidates from vector search and returns the top 3 by relevance. In ultralight, no reranker is used (`node_postprocessors` is empty).

**22. How is the “retrieval query” built?**  
The raw user query is normalized and keyword-extracted (stopwords removed, domain terms like esmd/fhir/cms favored). The retrieval query can be `"keywords: <keywords>\nquestion: <query>"` to bias retrieval toward important terms. This same string is used for vector search and (when applicable) for the router.

**23. How is the tenant chosen for a query?**  
(1) If the user explicitly mentions one or more tenants (by name or alias), those are used. (2) Otherwise, the query (or its normalized form) is embedded and compared via cosine similarity to each tenant’s descriptor embedding; scores are blended with keyword-overlap (configurable via `ROUTING_COSINE_WEIGHT`, default 0.7). (3) If the best score is above `TENANT_MIN_CONF_THRESH` (default 0.5) or the user asked for auto-select, that tenant’s engine is used. (4) Otherwise the app can either use the **RouterQueryEngine** (LLM selects among tenant tools) or ask the user to pick a tenant.

**24. What is the RouterQueryEngine?**  
A LlamaIndex **RouterQueryEngine** with **PydanticSingleSelector** and the LLM (Groq). It has one tool per tenant (each tool is that tenant’s query engine). When routing is needed, the LLM chooses which tenant tool to call for the given query.

**25. What tools are used in retrieval?**  
Each tenant is exposed as a **QueryEngineTool** wrapping that tenant’s vector-store query engine. The router uses these tools; alternatively, the app can bypass the router and call the selected tenant’s engine directly after embedding-based tenant selection.

**26. How are multi-tenant queries handled?**  
If two or more tenants are explicitly mentioned, the app queries each of those tenants’ engines with the same retrieval query, merges the `source_nodes`, and then runs scoring, aggregation, and response formatting over the combined nodes. A single “selected_tenant” can be a comma-separated list (e.g. "HIH,RC").

**27. Is there any keyword or code-aware boosting?**  
Yes. After retrieval, nodes are re-scored: numeric/code-like tokens and quoted phrases from the query get a bonus if they appear in the chunk; domain codes (ICD-10, CPT, HCPCS, DRG/MS-DRG) get higher boost. This favors chunks that contain exact codes or quoted phrases.

**28. What is the “guardrail” for no keyword hits?**  
If the top retrieved chunks do not contain any of the retrieval keywords, the app does not send context to the LLM and returns a “couldn’t find relevant information” style message to reduce hallucination.

---

## GENERATION

**29. What LLM is used for generation?**  
**Groq** with model **llama-3.1-8b-instant** (configurable via code; API key from `GROQ_API_KEY`). Used for final answer formatting and for the router when it selects a tenant.

**30. How is the final answer produced?**  
Retrieved (and optionally reranked) chunks are truncated to a token budget (`_smart_truncate_context`, default 3500 tokens) using tiktoken (`cl100k_base`). A structured prompt is built with rules (no hallucination, use only context, professional tone, JSON output). The prompt is sent to the LLM; the response is parsed as JSON (with handling for control characters and first JSON object extraction).

**31. What is in the generation prompt?**  
The prompt includes: system rules (no hallucinations, use only context, concise, code snippets exact, download intent, JSON format), the truncated context under “CONTEXT FROM TENANT”, the user query, and the required JSON schema: `summary`, `detailed_response`, `key_points`, `suggestions`, `follow_up_questions`, `code_snippets`.

**32. Why is context truncated before generation?**  
To fit within the model’s context window (e.g. Groq limits). The code aims for ~3500 tokens for context so that prompt + response stay under the limit (e.g. 6000 total). Truncation is relevance-order aware (reranked nodes first).

**33. What tokenizer is used for truncation?**  
**tiktoken** with encoding `cl100k_base` (same style as GPT-3.5/4). Used in `_smart_truncate_context` to count and cap tokens; if token counting fails, a character-based fallback is used (~4 chars per token).

**34. How are sources attached to the response?**  
Retrieved nodes are aggregated by canonical source (file path; prefer original PDF over sidecar). For each source, filename, relevance score, and page numbers are collected. Optional `url_map.json` per tenant maps file paths to original URLs. The final response includes a `sources` list (e.g. filename, relevance, pages, optional url, relative_path) and `selected_tenant`.

**35. Is response caching used?**  
Yes, when `CACHE_ENABLED` is true. Cache key is normalized query + tenant. Cache entries store file signatures (path, mtime, size); if any file for that tenant changes, the entry is considered invalid. On cache hit, the stored response is returned without running retrieval or generation again.

**36. What is rephrase_query used for?**  
`rephrase_query(query)` calls the LLM to suggest 3 alternative phrasings of the user query and returns them in a JSON object (`suggestions`). Used to improve search (e.g. suggest different ways to ask the same question).

---

## END-TO-END FLOW

**37. Walk through the flow from user query to answer.**  
(1) Query received; optional cache check. (2) Resolve explicit tenant mentions or aliases. (3) If multiple tenants mentioned, query each tenant engine and merge nodes. (4) Else: embed query, compare to tenant descriptors, select best tenant (or use router). (5) Run retrieval on selected tenant(s): vector search (top_k=10, cutoff=0.5), optional rerank (top_n=3). (6) Evidence re-scoring (codes, quoted phrases). (7) Guardrail: require keyword presence in top chunks. (8) Aggregate sources, truncate context to token limit. (9) Build prompt and call LLM for JSON response. (10) Parse JSON, attach sources and metadata; optionally cache and return.

**38. What frameworks/libraries power the pipeline?**  
**LlamaIndex** (core, vector store, query engines, router, tools, selectors), **Groq** (LLM), **HuggingFace** or **OpenAI** (embeddings), **tiktoken** (token counting), **Camelot** (optional table extraction), **Trafilatura** (optional URL ingestion). Optional: **sentence-transformers** reranker.

**39. How do ingestion, chunking, embedding, retrieval, and generation connect?**  
Ingestion writes files into `documents/<tenant_id>/`. Index build loads those documents (with optional cleaning and table sidecars), chunks them with LlamaIndex (1024/100), embeds chunks with the configured embedding model, and stores them in the tenant’s vector index. At query time, the query is embedded, tenant(s) are selected, retrieval returns top chunks (and optionally reranked), context is truncated, and the LLM generates the final JSON answer from that context.

**40. What env vars control the RAG pipeline?**  
`GROQ_API_KEY` (required), `EMBEDDING_PROVIDER` and `OPENAI_API_KEY` (for OpenAI embeddings), `CLEANING_ENABLED`, `TABLE_EXTRACT_ENABLED`, `CACHE_ENABLED`, `TENANT_HIGH_CONF_THRESH`, `TENANT_MIN_CONF_THRESH`, `ROUTING_COSINE_WEIGHT`, `TENANT_ALIASES`, `SHOW_TRACE`. Chunk size/overlap are in code (Settings); similarity_top_k, similarity_cutoff, and reranker top_n are in code.

---

*Document generated from the CarePolicy RAG Hub codebase (rag_agent.py, app.py).*
