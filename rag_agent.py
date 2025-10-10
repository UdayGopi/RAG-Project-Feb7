import os
import re
import unicodedata
import logging
import json
import shutil
from urllib.parse import urlparse
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage, download_loader
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.base.response.schema import Response
from llama_index.core.postprocessor import SentenceTransformerRerank
from math import sqrt
import time

class RAGAgent:
    def __init__(self, documents_dir="documents", storage_dir="storage"):
        self.documents_dir = documents_dir
        self.storage_dir = storage_dir
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)
        self.ALLOWED_DOMAINS = ["www.cms.gov", "esmdguide-fhir.cms.hhs.gov"]
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        self.llm = Groq(model="llama-3.1-8b-instant", api_key=groq_api_key)
        self.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.chunk_size = 1024
        Settings.chunk_overlap = 100
        self.web_reader = download_loader("TrafilaturaWebReader")()
        self.router_query_engine = None
        self.tenants = []
        self.tools = []
        self.tenant_embeddings = {}
        self.tenant_tool_map = {}
        # Cleaning toggle (enable by default)
        try:
            self.cleaning_enabled = str(os.getenv("CLEANING_ENABLED", "true")).strip().lower() not in ("0","false","no")
        except Exception:
            self.cleaning_enabled = True
        try:
            self.TENANT_HIGH_CONF_THRESH = float(os.getenv("TENANT_HIGH_CONF_THRESH", "0.75"))
        except ValueError:
            self.TENANT_HIGH_CONF_THRESH = 0.75
        try:
            self.TENANT_MIN_CONF_THRESH = float(os.getenv("TENANT_MIN_CONF_THRESH", "0.5"))
        except ValueError:
            self.TENANT_MIN_CONF_THRESH = 0.5
        self.cache_file = os.path.join(os.getcwd(), "cache_store.json")
        self._rebuild_router_engine()

    def _rebuild_router_engine(self):
        """
        Builds a multi-tenant routing query engine with advanced features like re-ranking.
        The ingestion process now leverages 'unstructured' for better parsing of complex documents.
        """
        try:
            self.tools = []
            self.tenant_embeddings = {}
            self.tenant_tool_map = {}
            
            self.tenants = [d for d in os.listdir(self.documents_dir) if os.path.isdir(os.path.join(self.documents_dir, d))]

            if not self.tenants:
                logging.warning("No tenant directories found.")
                self.router_query_engine = None
                return

            reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=5)

            for tenant_id in self.tenants:
                tenant_doc_dir = os.path.join(self.documents_dir, tenant_id)
                tenant_storage_dir = os.path.join(self.storage_dir, tenant_id)
                
                must_rebuild = True
                if os.path.exists(tenant_storage_dir) and os.listdir(tenant_storage_dir):
                    # Only attempt load if core files exist; otherwise rebuild
                    docstore_path = os.path.join(tenant_storage_dir, "docstore.json")
                    try:
                        if os.path.exists(docstore_path):
                            storage_context = StorageContext.from_defaults(persist_dir=tenant_storage_dir)
                            index = load_index_from_storage(storage_context)
                            must_rebuild = False
                    except Exception:
                        must_rebuild = True
                if must_rebuild:
                    # Use SimpleDirectoryReader with best-effort extractors for diverse formats (PDF tables, images, etc.)
                    file_extractor = {}
                    try:
                        # Prefer PyMuPDF for better layout/table retention when available
                        from llama_index.readers.file import PyMuPDFReader  # type: ignore
                        file_extractor[".pdf"] = PyMuPDFReader()
                    except Exception:
                        pass
                    try:
                        # Fallback high-res unstructured if available
                        from llama_index.readers.file import UnstructuredReader  # type: ignore
                        file_extractor.setdefault(".pdf", UnstructuredReader())
                        file_extractor[".docx"] = UnstructuredReader()
                        file_extractor[".pptx"] = UnstructuredReader()
                        file_extractor[".html"] = UnstructuredReader()
                    except Exception:
                        pass
                    try:
                        # Basic image OCR if available
                        from llama_index.readers.file import ImageReader  # type: ignore
                        file_extractor[".png"] = ImageReader()
                        file_extractor[".jpg"] = ImageReader()
                        file_extractor[".jpeg"] = ImageReader()
                        file_extractor[".tiff"] = ImageReader()
                    except Exception:
                        pass
                    try:
                        from llama_index.readers.file import PandasCSVReader, PandasExcelReader  # type: ignore
                        file_extractor[".csv"] = PandasCSVReader()
                        file_extractor[".xlsx"] = PandasExcelReader()
                        file_extractor[".xls"] = PandasExcelReader()
                    except Exception:
                        pass

                    documents = SimpleDirectoryReader(
                        tenant_doc_dir,
                        recursive=True,
                        file_extractor=file_extractor or None,
                    ).load_data()
                    # Optional cleaning pass before chunking/indexing
                    if self.cleaning_enabled:
                        def _is_code_like(s: str) -> bool:
                            if not s:
                                return False
                            s2 = s.strip()
                            # ICD-10, CPT, HCPCS, DRG/MS-DRG quick checks
                            if re.search(r"\b[A-TV-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?\b", s2, re.IGNORECASE):
                                return True
                            if re.search(r"\b\d{5}\b", s2):
                                return True
                            if re.search(r"\b[A-VJ-KM-PQRS-T][0-9]{4}\b", s2, re.IGNORECASE):
                                return True
                            if re.search(r"\b(?:MS-)?DRG\s*\d{3}\b", s2, re.IGNORECASE):
                                return True
                            return False

                        def _clean_text(txt: str) -> str:
                            if not isinstance(txt, str) or not txt:
                                return txt
                            # Unicode normalize
                            t = unicodedata.normalize("NFKC", txt)
                            # Normalize line endings
                            t = t.replace("\r\n", "\n").replace("\r", "\n")
                            # De-hyphenate across line breaks: word-\nword => wordword (but avoid inside recognized codes)
                            t = re.sub(r"(?<=\w)-(?:\n|\r\n)(?=\w)", "", t)
                            # Remove control chars (except \n and \t)
                            t = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", t)
                            # Collapse excessive blank lines
                            t = re.sub(r"\n{3,}", "\n\n", t)
                            # Header/footer heuristic: drop lines repeated often, short, and non-code
                            lines = t.split("\n")
                            counts = {}
                            for ln in lines:
                                key = ln.strip()
                                if key:
                                    counts[key] = counts.get(key, 0) + 1
                            cleaned_lines = []
                            for ln in lines:
                                key = ln.strip()
                                if not key:
                                    cleaned_lines.append(ln)
                                    continue
                                # Repeated boilerplate and not a code line
                                if counts.get(key, 0) >= 3 and 2 <= len(key) <= 80 and not _is_code_like(key):
                                    continue
                                cleaned_lines.append(ln)
                            t = "\n".join(cleaned_lines)
                            # Collapse horizontal whitespace sequences (not newlines)
                            t = re.sub(r"[ \t]{2,}", " ", t)
                            return t.strip()

                        for d in documents:
                            try:
                                if hasattr(d, 'text') and isinstance(d.text, str):
                                    d.text = _clean_text(d.text)
                            except Exception:
                                pass
                    index = VectorStoreIndex.from_documents(documents)
                    index.storage_context.persist(persist_dir=tenant_storage_dir)
                
                query_engine = index.as_query_engine(
                    similarity_top_k=15,  # Retrieve more candidates for the re-ranker
                    node_postprocessors=[reranker]
                )
                
                tool = QueryEngineTool(
                    query_engine=query_engine,
                    metadata=ToolMetadata(
                        name=tenant_id,
                        description=f"Use this tool for any questions related to the tenant '{tenant_id}'.",
                    ),
                )
                self.tools.append(tool)
                # Map for direct per-tenant routing
                self.tenant_tool_map[tenant_id] = query_engine
                # Build a lightweight descriptor for tenant and embed it for preselection
                descriptor = self._build_tenant_descriptor(tenant_id, tenant_doc_dir)
                try:
                    self.tenant_embeddings[tenant_id] = self.embed_model.get_text_embedding(descriptor)
                except Exception as e:
                    logging.warning(f"Failed to embed descriptor for tenant '{tenant_id}': {e}")

            self.router_query_engine = RouterQueryEngine(
                selector=PydanticSingleSelector.from_defaults(llm=self.llm),
                query_engine_tools=self.tools,
                verbose=True
            )
            logging.info("Multi-tenant Router Query Engine initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to create router engine: {e}", exc_info=True)
            self.router_query_engine = None

    def _build_tenant_descriptor(self, tenant_id: str, tenant_doc_dir: str) -> str:
        """Create a compact textual descriptor for a tenant to enable cheap embedding-based routing."""
        file_names = []
        try:
            for root, _, files in os.walk(tenant_doc_dir):
                for f in files:
                    file_names.append(f)
                if len(file_names) > 30:
                    break
        except Exception:
            pass
        top_files = ", ".join(file_names[:30]) if file_names else ""
        return f"Tenant: {tenant_id}. Files: {top_files}"

    def _cosine(self, a, b) -> float:
        """Cosine similarity between two equal-length vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x*y for x, y in zip(a, b))
        na = sqrt(sum(x*x for x in a))
        nb = sqrt(sum(y*y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # -------------------- Response Cache Helpers --------------------
    def _load_cache(self):
        try:
            if not os.path.exists(self.cache_file):
                return {"entries": []}
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"entries": []}

    def _save_cache(self, cache_obj):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_obj, f, indent=2)
        except Exception as e:
            logging.warning(f"Failed to save cache: {e}")

    def _normalize_query(self, q: str) -> str:
        return (q or "").strip().lower()

    def _file_signatures(self, sources):
        sigs = []
        for s in sources or []:
            fp = s.get("filename") if isinstance(s, dict) else None
            if not fp:
                continue
            try:
                mtime = os.path.getmtime(fp)
                size = os.path.getsize(fp)
                sigs.append({"path": fp, "mtime": mtime, "size": size})
            except Exception:
                continue
        return sigs

    def _hash_file(self, path: str) -> str:
        import hashlib
        h = hashlib.sha256()
        with open(path, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()

    def _is_cache_entry_valid(self, entry) -> bool:
        for sig in entry.get("file_signatures", []):
            try:
                if (abs(os.path.getmtime(sig["path"]) - sig["mtime"]) > 1e-6) or (os.path.getsize(sig["path"]) != sig["size"]):
                    return False
            except Exception:
                return False
        return True

    def _get_cached_response(self, query: str, tenant: str):
        cache_obj = self._load_cache()
        nq = self._normalize_query(query)
        for entry in cache_obj.get("entries", []):
            if entry.get("tenant") == tenant and entry.get("query_norm") == nq:
                if self._is_cache_entry_valid(entry):
                    return entry.get("response")
        return None

    def _extract_query_tokens(self, query: str):
        q = (query or "").strip()
        tokens = set()
        # quoted phrases: "..." or '...'
        for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'', q):
            tok = (m.group(1) or m.group(2) or "").strip()
            if tok:
                tokens.add(tok.lower())
        # numbers and alnum codes (e.g., 625, 18.1_0)
        for m in re.finditer(r'\b\d[\w\-.]*\b', q):
            tokens.add(m.group(0).lower())
        # short keywords (avoid common stopwords)
        words = re.findall(r'[A-Za-z0-9_\-]+', q.lower())
        stop = {"what","is","the","a","an","and","or","to","from","for","why","it","used","use","of","in","on"}
        for w in words:
            if w not in stop and len(w) >= 2:
                tokens.add(w)
        return list(tokens)

    def _extract_code_like_tokens(self, text: str):
        """Heuristic extraction of code-like tokens from text (IDs, error codes).
        - Includes tokens with uppercase letters/digits/_/- of length 2-20
        - Includes pure digit sequences length 2-6
        - De-duplicates while preserving insertion order
        """
        if not text:
            return []
        candidates = []
        seen = set()
        # Alnum codes with hyphen/underscore
        for m in re.finditer(r"\b[A-Z0-9][A-Z0-9_-]{1,19}\b", text):
            tok = m.group(0)
            if any(c.isdigit() for c in tok):
                if tok not in seen:
                    seen.add(tok)
                    candidates.append(tok)
        # Pure digit codes
        for m in re.finditer(r"\b\d{2,6}\b", text):
            tok = m.group(0)
            if tok not in seen:
                seen.add(tok)
                candidates.append(tok)
        return candidates[:200]

    def _extract_medical_codes(self, text: str):
        """Extract domain-specific codes with labels for stronger matching.
        Returns list of dicts: {"type":"ICD10"|"CPT"|"HCPCS"|"DRG"|"MS-DRG", "code": str}
        Patterns (practical approximations):
        - ICD-10-CM: e.g., A00, E11.9, S72.001A (letter+2 digits, optional . and alphanumerics)
        - CPT: 5 digits (00100-99999), allow leading zeros
        - HCPCS Level II: one letter A-V,J,K,L,M,P,Q,R,S,T + 4 digits (e.g., J0123)
        - DRG/MS-DRG: 3 digits (001-999) when prefixed by DRG or MS-DRG in proximity
        """
        results = []
        if not text:
            return results
        tl = text
        # ICD-10 (simple, common subset)
        for m in re.finditer(r"\b([A-TV-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?)\b", tl, flags=re.IGNORECASE):
            results.append({"type": "ICD10", "code": m.group(1).upper()})
        # CPT (5 digits)
        for m in re.finditer(r"\b(\d{5})\b", tl):
            results.append({"type": "CPT", "code": m.group(1)})
        # HCPCS (letter + 4 digits)
        for m in re.finditer(r"\b([A-VJ-KM-PQRS-T][0-9]{4})\b", tl, flags=re.IGNORECASE):
            results.append({"type": "HCPCS", "code": m.group(1).upper()})
        # DRG/MS-DRG (detect when DRG mentioned near 3-digit number)
        for m in re.finditer(r"\b(MS-)?DRG\s*(\d{3})\b", tl, flags=re.IGNORECASE):
            results.append({"type": "MS-DRG" if m.group(1) else "DRG", "code": m.group(2)})
        return results


    def cache_response(self, query: str, response_obj: dict):
        try:
            cache_obj = self._load_cache()
            nq = self._normalize_query(query)
            tenant = response_obj.get("selected_tenant")
            sources = response_obj.get("sources", [])
            entry = {
                "tenant": tenant,
                "query_norm": nq,
                "response": response_obj,
                "file_signatures": self._file_signatures(sources),
                "cached_at": time.time(),
            }
            # Replace existing entry for same key
            cache_obj.setdefault("entries", [])
            cache_obj["entries"] = [e for e in cache_obj["entries"] if not (e.get("tenant") == tenant and e.get("query_norm") == nq)]
            cache_obj["entries"].append(entry)
            self._save_cache(cache_obj)
        except Exception as e:
            logging.warning(f"Failed to cache response: {e}")

    def _invalidate_cache_for_tenant(self, tenant_id: str):
        try:
            cache_obj = self._load_cache()
            cache_obj["entries"] = [e for e in cache_obj.get("entries", []) if e.get("tenant") != tenant_id]
            self._save_cache(cache_obj)
        except Exception as e:
            logging.warning(f"Failed to invalidate cache for tenant {tenant_id}: {e}")

    def _extract_first_json_object(self, text: str) -> str:
        """
        Extract the first top-level JSON object {...} from the text, handling nested braces
        and ignoring braces inside quoted strings. Returns empty string if none found.
        """
        in_string = False
        escape = False
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        return text[start:i+1]
        return ""

    def _escape_control_chars_in_json_strings(self, text: str) -> str:
        """
        Walk through the JSON text and escape raw control characters (\n, \r, \t) only
        inside quoted strings. This helps when LLMs emit literal newlines inside string values.
        """
        out = []
        in_string = False
        escape = False
        for ch in text:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == '\\':
                out.append(ch)
                escape = True
                continue
            if ch == '"':
                out.append(ch)
                in_string = not in_string
                continue
            if in_string:
                if ch == '\n':
                    out.append('\\n')
                elif ch == '\r':
                    out.append('\\r')
                elif ch == '\t':
                    out.append('\\t')
                else:
                    out.append(ch)
            else:
                out.append(ch)
        return ''.join(out)

    def _format_rag_response(self, query, rag_response, selected_tenant):
        context_str = "\n\n".join([r.get_content() for r in rag_response.source_nodes])
        
        prompt = f"""
        You are a professional AI assistant for company employees. Your purpose is to provide accurate information based SOLELY on the provided context.

        RULES:
        1.  **NO HALLUCINATIONS:** If the answer is not in the `CONTEXT` below, you MUST state that you could not find the information in the available documents. Do not use any outside knowledge.
        2.  **STRICTLY USE CONTEXT:** Base your entire response on the `CONTEXT` provided.
        3.  **PROFESSIONAL TONE:** Frame your answers in a clear, professional, and helpful manner.
        4.  **CODE SNIPPETS:** If the context contains any code blocks (e.g., XML, JSON, Python), extract them exactly as they are.
        5.  **DOWNLOAD INTENT:** If the user query contains keywords like "download", "form", "get", "obtain", or "document", identify the most relevant filename(s) from the context and include them in the `downloadable_files` list.

        CONTEXT FROM TENANT '{selected_tenant}':
        ---
        {context_str if context_str.strip() else "No relevant context found."}
        ---

        USER QUERY: "{query}"

        Based on the rules and context, provide a structured response in a single JSON object.

        RESPONSE FORMAT (JSON object only):
        {{
            "summary": "Concise 1-3 sentence summary based ONLY on the context. If no context, say that.",
            "detailed_response": "Detailed, multi-paragraph answer based ONLY on the context. If no context, state that the information is not in the documents.",
            "key_points": ["List of 3-5 key takeaways from the context. If none, return an empty list."],
            "suggestions": ["List of 2-3 practical next steps based on the context. If none, return an empty list."],
            "follow_up_questions": ["List of 2-3 relevant follow-up questions that can be answered from the context. If none, return an empty list."],
            "code_snippets": [],
        }}

        IMPORTANT OUTPUT RULES:
        - Output MUST be a single valid JSON object and NOTHING else. Do not add headings or lists after the JSON.
        - Escape all newlines within string values as \n. Do not include raw line breaks inside JSON strings.
        """
        ql = (query or '').lower()
        wants_only_codes = any(k in ql for k in ['only code', 'only codes', 'just code', 'just codes', 'codes only'])
        code_candidates = self._extract_code_like_tokens(context_str)
        try:
            response_str = self.llm.complete(prompt).text
            # Local helpers to avoid attribute lookup issues in some runtimes
            def _extract_first_json_object(text: str) -> str:
                in_string = False
                escape = False
                depth = 0
                start = -1
                for i, ch in enumerate(text):
                    if escape:
                        escape = False
                        continue
                    if ch == '\\':
                        escape = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == '{':
                        if depth == 0:
                            start = i
                        depth += 1
                    elif ch == '}':
                        if depth > 0:
                            depth -= 1
                            if depth == 0 and start != -1:
                                return text[start:i+1]
                return ""

            def _escape_control_chars_in_json_strings(text: str) -> str:
                out = []
                in_string = False
                escape = False
                for ch in text:
                    if escape:
                        out.append(ch)
                        escape = False
                        continue
                    if ch == '\\':
                        out.append(ch)
                        escape = True
                        continue
                    if ch == '"':
                        out.append(ch)
                        in_string = not in_string
                        continue
                    if in_string:
                        if ch == '\n':
                            out.append('\\n')
                        elif ch == '\r':
                            out.append('\\r')
                        elif ch == '\t':
                            out.append('\\t')
                        else:
                            out.append(ch)
                    else:
                        out.append(ch)
                return ''.join(out)

            # Remove code fences if present
            response_str = re.sub(r'^```json\s*|\s*```$', '', response_str, flags=re.MULTILINE)
            # Extract only the first JSON object to avoid trailing markdown/text
            json_str = _extract_first_json_object(response_str)
            if not json_str:
                raise ValueError("No JSON object found in LLM response")
            # Escape control characters within JSON string values
            safe_json_str = _escape_control_chars_in_json_strings(json_str)
            parsed = json.loads(safe_json_str)
            allowed_keys = {"intent","summary","detailed_response","key_points","suggestions","follow_up_questions","code_snippets","codes","esmd_onboarding"}
            sanitized = {k: parsed.get(k) for k in allowed_keys}
            # Ensure list fields are lists
            for k in ("key_points","suggestions","follow_up_questions","code_snippets","codes"):
                if not isinstance(sanitized.get(k), list):
                    sanitized[k] = []
            if not isinstance(sanitized.get("esmd_onboarding"), dict):
                sanitized["esmd_onboarding"] = {}
            # Fallback for codes-only request if model missed it
            if wants_only_codes and not sanitized.get("codes") and code_candidates:
                sanitized["codes"] = code_candidates
            # Mark download intent for UI toast convenience
            intent = (sanitized.get("intent") or "").lower()
            di = intent == "download" or any(k in ql for k in ['download','form','get','obtain','document'])
            sanitized["is_download_intent"] = bool(di)
            return sanitized
        except Exception as e:
            logging.error(f"Failed to parse LLM response into JSON: {e}. Response: {response_str}")
            return {"summary": "Could not format response.", "detailed_response": rag_response.response}

    def get_response(self, query):
        if not self.router_query_engine:
            return {
                "is_conversational": True,
                "answer": "The agent is not configured yet. Please upload some documents to begin."
            }

        auto_select = "[AUTO]" in query
        if auto_select:
            query = query.replace("[AUTO]", "").strip()
        
        ambiguous_keywords = ["onboard", "onboarding", "form"]
        is_ambiguous = any(keyword in query.lower() for keyword in ambiguous_keywords)
        
        if not auto_select and is_ambiguous and not any(tenant.lower() in query.lower() for tenant in self.tenants):
            logging.info("Ambiguous query detected. Asking user for tenant selection.")
            return {
                "needs_tenant_selection": True,
                "tenants": self.tenants,
                "original_query": query
            }

        try:
            # Try cached response (using auto-selected tenant descriptor if present later; fallback to None)
            # We attempt cache after we know tenant. For now, try all tenants and pick a hit if any.
            for t in self.tenants:
                cached = self._get_cached_response(query, t)
                if cached:
                    logging.info(f"Serving cached response for tenant '{t}'")
                    return cached

            # 1) Embed query and pick best-scoring tenant via cosine similarity
            best_tenant = None
            best_score = -1.0
            try:
                q_emb = self.embed_model.get_text_embedding(query)
                # Prefer explicit tenant mention in the query
                ql = query.lower()
                explicit = None
                for tenant_id in self.tenants:
                    if tenant_id.lower() in ql:
                        explicit = tenant_id
                        break

                if explicit:
                    best_tenant = explicit
                    best_score = 1.0
                for tenant_id, t_emb in self.tenant_embeddings.items():
                    score = self._cosine(q_emb, t_emb)
                    if score > best_score:
                        best_score = score
                        best_tenant = tenant_id
                logging.info(f"Best tenant preselection: {best_tenant} (score={best_score:.3f})")
            except Exception as e:
                logging.warning(f"Query embedding or tenant similarity failed, falling back to router: {e}")
                best_tenant = None

            # 2) Decision: if confident OR user requested auto-select, route directly
            if best_tenant and (best_score >= self.TENANT_MIN_CONF_THRESH or auto_select):
                selected_tenant = best_tenant
                tenant_engine = self.tenant_tool_map.get(selected_tenant)
                if tenant_engine is None:
                    logging.warning(f"No engine found for selected tenant '{selected_tenant}', falling back to router.")
                    response = self.router_query_engine.query(query)
                else:
                    response = tenant_engine.query(query)
            else:
                # Low confidence: if auto-select was requested, fall back to router silently; otherwise ask user
                if auto_select:
                    logging.info("Low-confidence routing with [AUTO]. Falling back to router engine.")
                    response = self.router_query_engine.query(query)
                else:
                    logging.info("Low-confidence routing. Asking user for tenant selection.")
                    return {
                        "needs_tenant_selection": True,
                        "tenants": self.tenants,
                        "original_query": query
                    }
            
            if not response.source_nodes:
                logging.warning(f"No relevant documents found for query: '{query}'.")
                return {
                    "is_conversational": True,
                    "answer": "I'm sorry, but I couldn't find any relevant information in the documents for your query. Please try asking in a different way."
                }

            logging.info("Handling as a RAG query. Formatting response...")
            
            # If we got here via direct-tenant path, selected_tenant is set; otherwise try reading router metadata
            if 'selected_tenant' not in locals():
                selected_tenant = "default"
                if response.metadata and "selector_result" in response.metadata:
                    selections = response.metadata["selector_result"].selections
                    if selections:
                        selected_index = selections[0].index
                        selected_tenant = self.tools[selected_index].metadata.name
            
            # Evidence-aware re-scoring: boost nodes that contain numeric/code tokens (incl. domain codes) and quoted phrases
            tokens = self._extract_query_tokens(query)
            numeric_tokens = [t for t in tokens if any(c.isdigit() for c in t)]
            query_codes = self._extract_medical_codes(query)

            # Build variant patterns for numeric tokens (e.g., 543, (543), error 543, code 543)
            def token_variants(t: str):
                v = {t}
                v.add(f"({t})")
                v.add(f"[{t}]")
                v.add(f"{{{t}}}")
                v.add(f"{t}.")
                v.add(f"error {t}")
                v.add(f"code {t}")
                v.add(f"reason {t}")
                v.add(f"section {t}")
                return list(v)

            numeric_variants = []
            for t in numeric_tokens:
                numeric_variants.extend(token_variants(t))
            # Add domain-code contextual variants
            for c in query_codes:
                code = c.get("code", "").lower()
                if not code:
                    continue
                numeric_variants.extend([
                    code,
                    f"drg {code}", f"ms-drg {code}",
                    f"icd {code}", f"icd-10 {code}", f"icd10 {code}",
                    f"cpt {code}", f"hcpcs {code}",
                ])

            # Quoted phrases get higher weight if present verbatim
            quoted_phrases = []
            for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'', query):
                qp = (m.group(1) or m.group(2) or '').strip()
                if qp:
                    quoted_phrases.append(qp.lower())

            def score_node(n):
                base = float(getattr(n, 'score', 0.0) or 0.0)
                tl = (n.get_content() or '').lower()
                bonus = 0.0
                # numeric/code tokens bonus
                if numeric_variants:
                    for t in numeric_variants:
                        if t and t in tl:
                            bonus += 0.3
                # domain code exact matches get higher boost
                if query_codes:
                    for c in query_codes:
                        code = (c.get("code") or "").lower()
                        if code and code in tl:
                            bonus += 0.5
                # quoted phrase exact-match bonus
                for qp in quoted_phrases:
                    if qp and qp in tl:
                        bonus += 0.4
                # light length cap to avoid over-emphasizing huge chunks
                return base + min(bonus, 2.0)

            source_nodes = sorted(response.source_nodes, key=score_node, reverse=True)

            seen_sources = set()
            unique_sources = []
            for node in source_nodes:
                file_path = node.metadata.get('file_path')
                if file_path not in seen_sources:
                    seen_sources.add(file_path)
                    # PERMANENT FIX: Convert the score to a standard Python float, include page if present
                    page = node.metadata.get('page', node.metadata.get('page_label'))
                    src = {"filename": file_path, "relevance": float(node.score)}
                    if page is not None:
                        try:
                            src["page"] = int(page)
                        except Exception:
                            src["page"] = page
                    unique_sources.append(src)

            # Build final structured response and attach sources/metadata
            # Create a lightweight response adapter with the possibly filtered nodes for formatting
            class _RespAdapter:
                def __init__(self, nodes, original):
                    self.source_nodes = nodes
                    self.response = getattr(original, 'response', '')
            adapted = _RespAdapter(source_nodes, response)
            structured_response = self._format_rag_response(query, adapted, selected_tenant)
            structured_response["sources"] = unique_sources
            structured_response["selected_tenant"] = selected_tenant
            structured_response["tenant_preselect_score"] = round(float(best_score), 3) if best_tenant else None
            # Ensure no leaked keys like 'downloadable_files' are returned
            if "downloadable_files" in structured_response:
                try:
                    del structured_response["downloadable_files"]
                except Exception:
                    pass
            return structured_response
        except Exception as e:
            logging.error(f"Error getting response from agent for query '{query}': {e}", exc_info=True)
            return {"summary": "Error", "detailed_response": "I encountered an error processing your request."}

    def rephrase_query(self, query):
        prompt = f'Rephrase the following user query in 3 different ways to improve search results. Return ONLY a single JSON object with a "suggestions" key containing a list of strings.\n\nORIGINAL QUERY: "{query}"'
        ql = (query or '').lower()
        try:
            response_str = self.llm.complete(prompt).text
            match = re.search(r'{\s*"suggestions"\s*:\s*\[.*\]\s*}', response_str, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                logging.error(f"Could not find a valid JSON object in the rephrase response: {response_str}")
                return {"suggestions": []}
        except Exception as e:
            logging.error(f"Failed to rephrase query: {e}")
            return {"suggestions": []}

    def ingest_files(self, tenant_id, files):
        tenant_dir = os.path.join(self.documents_dir, tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)
        saved_files, errors = [], []
        for file in files:
            if file and file.filename:
                try:
                    filepath = os.path.join(tenant_dir, file.filename)
                    file.save(filepath)
                    saved_files.append(file.filename)
                except Exception as e:
                    errors.append(f"Error saving {file.filename}: {e}")
            else:
                logging.info("Skipping an empty file part in the upload.")

        if saved_files:
            tenant_storage_dir = os.path.join(self.storage_dir, tenant_id)
            manifest_path = os.path.join(tenant_storage_dir, "manifest.json")
            current = self._scan_manifest(tenant_dir)
            prev = self._read_manifest(manifest_path)
            changed, deleted, added = self._diff_manifest(prev, current)
            if changed or deleted or added:
                logging.info("Detected changes for tenant '%s'. Rebuilding index.", tenant_id)
                if os.path.exists(tenant_storage_dir):
                    shutil.rmtree(tenant_storage_dir)
                self._write_manifest(manifest_path, current)
                # Invalidate cache for this tenant then rebuild
                self._invalidate_cache_for_tenant(tenant_id)
                self._rebuild_router_engine()
        return saved_files, errors

    # -------------------- Manifest helpers for incremental updates --------------------
    def _scan_manifest(self, tenant_doc_dir: str):
        """Return a sorted list of file signature strings 'path|size|mtime|sha256' for change detection."""
        sigs = []
        try:
            for root, _, files in os.walk(tenant_doc_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                        mtime = os.path.getmtime(fp)
                        sha = self._hash_file(fp)
                        sigs.append(f"{fp}|{size}|{mtime}|{sha}")
                    except Exception:
                        continue
        except Exception:
            pass
        sigs.sort()
        return sigs

    def _read_manifest(self, manifest_path: str):
        try:
            if not os.path.exists(manifest_path):
                return []
            with open(manifest_path, 'r', encoding='utf-8') as fh:
                obj = json.load(fh)
                if isinstance(obj, list):
                    return obj
                return obj.get('files', [])
        except Exception:
            return []

    def _write_manifest(self, manifest_path: str, current_list):
        try:
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(manifest_path, 'w', encoding='utf-8') as fh:
                json.dump(current_list, fh, indent=2)
        except Exception:
            pass

    def _diff_manifest(self, prev_list, curr_list):
        prev_set = set(prev_list or [])
        curr_set = set(curr_list or [])
        added = list(curr_set - prev_set)
        deleted = list(prev_set - curr_set)
        # We use simple set difference; changed handled by rebuilding if needed elsewhere
        changed = []
        return changed, deleted, added

    def ingest_url(self, tenant_id, url):
        try:
            parsed_url = urlparse(url)
            if parsed_url.netloc not in self.ALLOWED_DOMAINS:
                raise ValueError(f"Domain '{parsed_url.netloc}' is not in the list of allowed domains.")

            documents = self.web_reader.load_data(urls=[url])
            if not documents:
                raise ValueError("Web reader failed to extract any content from the URL.")
            
            tenant_dir = os.path.join(self.documents_dir, tenant_id)
            os.makedirs(tenant_dir, exist_ok=True)
            
            sanitized_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', url) + ".txt"
            filepath = os.path.join(tenant_dir, sanitized_filename)

            with open(filepath, "w", encoding="utf-8") as f:
                for doc in documents:
                    f.write(doc.text + '\n\n')
            
            tenant_storage_dir = os.path.join(self.storage_dir, tenant_id)
            manifest_path = os.path.join(tenant_storage_dir, "manifest.json")
            current = self._scan_manifest(tenant_dir)
            prev = self._read_manifest(manifest_path)
            changed, deleted, added = self._diff_manifest(prev, current)
            if changed or deleted or added:
                logging.info("URL ingest changed tenant '%s'. Rebuilding index.", tenant_id)
                try:
                    if os.path.exists(tenant_storage_dir):
                        shutil.rmtree(tenant_storage_dir)
                except Exception:
                    pass
                self._write_manifest(manifest_path, current)
                self._invalidate_cache_for_tenant(tenant_id)
                self._rebuild_router_engine()
            return [sanitized_filename], []
        except Exception as e:
            logging.error(f"Error ingesting URL '{url}': {e}", exc_info=True)
            return [], [f"Failed to ingest URL {url}: {e}"]



