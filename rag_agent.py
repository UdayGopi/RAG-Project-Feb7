import os
import re
import unicodedata
import logging
import json
import shutil
from urllib.parse import urlparse
import requests
import html as html_lib
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage, Document
from llama_index.core import download_loader
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.base.response.schema import Response
from llama_index.core.postprocessor import SentenceTransformerRerank
from math import sqrt
import time
import tiktoken  # For accurate token counting

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
            # Build retrieval keywords and retrieval_query for routing/retrieval (not for generation)
            def _extract_keywords(q: str, k_max: int = 8):
                try:
                    text = (q or '').lower()
                    text = re.sub(r"[^a-z0-9\s]", " ", text)
                    tokens = [t for t in text.split() if len(t) >= 3]
                    stop = set(["the","and","for","with","that","this","from","your","about","have","what","which","when","where","will","there","into","those","been","being","were","are","how","make","made","like","such","use","uses","used","using","can","you","please","tell","more","info","info.","step","steps","process","guide","guidance","policy","policies","onboarding","onboard","form","forms","rc","rcs"])  # basic stoplist
                    freq = {}
                    for t in tokens:
                        if t in stop:
                            continue
                        freq[t] = freq.get(t, 0) + 1
                    domain_terms = [t for t in ["esmd","fhir","cms","hhs","extension","extensions","implementation","guide"] if t in tokens]
                    key = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
                    kws = [w for w, _ in key][:k_max]
                    out = []
                    for w in domain_terms + kws:
                        if w not in out:
                            out.append(w)
                    return out[:k_max]
                except Exception:
                    return []

            query_keywords = _extract_keywords(query)
            keywords_str = " ".join(query_keywords)
            retrieval_query = (f"keywords: {keywords_str}\nquestion: {query}" if query_keywords else query)
            trace["keywords"] = query_keywords
            trace["retrieval_query"] = retrieval_query
            # Trace object for logs/response (optional)
            trace = {
                "query": query,
                "keywords": query_keywords,
                "retrieval_query": retrieval_query,
                "mentioned_tenants": [],
                "tenant_scores": [],
                "selected_tenant": None,
                "selected_score": None,
                "decision_path": None
            }
            logging.info(f"Routing: keywords={query_keywords}")
            self.cleaning_enabled = str(os.getenv("CLEANING_ENABLED", "true")).strip().lower() not in ("0","false","no")
        except Exception:
            self.cleaning_enabled = True
        # Table extraction toggle (enable by default)
        try:
            self.table_extract_enabled = str(os.getenv("TABLE_EXTRACT_ENABLED", "true")).strip().lower() not in ("0","false","no")
        except Exception:
            self.table_extract_enabled = True
        # Response cache toggle (enable by default)
        try:
            self.cache_enabled = str(os.getenv("CACHE_ENABLED", "true")).strip().lower() not in ("0","false","no")
        except Exception:
            self.cache_enabled = True
        try:
            self.TENANT_HIGH_CONF_THRESH = float(os.getenv("TENANT_HIGH_CONF_THRESH", "0.75"))
        except ValueError:
            self.TENANT_HIGH_CONF_THRESH = 0.75
        try:
            self.TENANT_MIN_CONF_THRESH = float(os.getenv("TENANT_MIN_CONF_THRESH", "0.5"))
        except ValueError:
            self.TENANT_MIN_CONF_THRESH = 0.5
        # Clarify intent thresholds (tunable)
        try:
            self.CLARIFY_NONTRIVIAL_MAX = int(os.getenv("CLARIFY_NONTRIVIAL_MAX", "1"))
        except ValueError:
            self.CLARIFY_NONTRIVIAL_MAX = 1
        try:
            self.CLARIFY_MIN_TOTAL_TOKENS = int(os.getenv("CLARIFY_MIN_TOTAL_TOKENS", "2"))
        except ValueError:
            self.CLARIFY_MIN_TOTAL_TOKENS = 2
        # Tenant alias mapping (JSON env or sensible defaults)
        try:
            aliases_env = os.getenv("TENANT_ALIASES", "")
            if aliases_env.strip():
                self.alias_to_tenant = {k.lower(): v for k, v in json.loads(aliases_env).items()}
            else:
                self.alias_to_tenant = {
                    "hih": "HIH",
                    "health information handler": "HIH",
                    "handler": "HIH",
                    "rc": "RC",
                    "review contractor": "RC",
                    "review contractors": "RC",
                }
        except Exception:
            self.alias_to_tenant = {}
        self.cache_file = os.path.join(os.getcwd(), "cache_store.json")
        self._rebuild_router_engine()

    # -------------------- Intent detection --------------------
    def _detect_intent(self, query: str) -> str:
        """Very lightweight intent classifier.
        Returns one of: 'small_talk' | 'clarify' | 'download' | 'question' | 'unknown'.
        """
        try:
            raw = (query or "").strip()
            q = raw.lower()
            q_stripped = re.sub(r"[^a-z0-9\s]", "", q)  # strip punctuation/emojis for heuristic
            if not q:
                return 'unknown'
            # If user mentions a tenant explicitly or via alias, this is not small talk
            mentioned = self._resolve_tenants_in_text(q)
            if mentioned:
                return 'question'
            # Greetings (use word boundaries to avoid matching 'hi' inside 'hih')
            if (
                re.search(r"\b(hi|hello|hey|hiya|yo|sup)\b", q_stripped) or
                re.search(r"\b(good\s+(morning|afternoon|evening))\b", q_stripped) or
                'how are you' in q_stripped or 'what is up' in q_stripped or 'whats up' in q_stripped
            ) and len(q_stripped.split()) <= 6:
                return 'small_talk'
            # Clarification-needed: extremely vague or placeholder queries (no meaningful tokens)
            words = [w for w in q_stripped.split() if len(w) > 1]
            low_info_terms = {"what", "is", "the", "a", "an", "of", "in"}
            nontrivial = [w for w in words if w not in low_info_terms]
            if len(nontrivial) == 0:
                return 'clarify'
            if any(k in q_stripped for k in ['download', 'form', 'get', 'obtain', 'document']):
                return 'download'
            if any(ch in (raw or '') for ch in ['?', ':']) or len(q_stripped.split()) >= 4:
                return 'question'
            return 'unknown'
        except Exception:
            return 'unknown'

    # -------------------- URL enrichment for cached responses --------------------
    def _enrich_sources_with_url(self, resp: dict):
        try:
            if not isinstance(resp, dict):
                return resp
            sources = resp.get('sources') or []
            if not sources:
                return resp
            sel = resp.get('selected_tenant') or ''
            tenants_in_scope = [t.strip() for t in str(sel).split(',') if t.strip()] if sel else []
            url_maps = {}
            for t in tenants_in_scope:
                try:
                    url_map_path = os.path.join(self.documents_dir, t, 'url_map.json')
                    if os.path.exists(url_map_path):
                        with open(url_map_path, 'r', encoding='utf-8') as fh:
                            m = json.load(fh) or {}
                            for k, v in m.items():
                                try:
                                    url_maps[os.path.normpath(k)] = v
                                    url_maps[os.path.basename(os.path.normpath(k))] = v
                                except Exception:
                                    url_maps[k] = v
                except Exception:
                    continue
            changed = False
            for s in sources:
                try:
                    if s.get('url'):
                        continue
                    fname = str(s.get('filename') or '')
                    if not fname:
                        continue
                    key1 = os.path.normpath(fname)
                    url_val = url_maps.get(key1) or url_maps.get(os.path.basename(key1))
                    if url_val:
                        s['url'] = url_val
                        changed = True
                except Exception:
                    continue
            if changed:
                resp['sources'] = sources
            return resp
        except Exception:
            return resp

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

            # Use reranker to filter only the most relevant results (top 3 for focused responses)
            reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=3)

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
                    # Optional: extract tables from PDFs and append as additional Documents
                    if self.table_extract_enabled:
                        try:
                            import os as _os
                            pdf_paths = []
                            for root, _, fs in _os.walk(tenant_doc_dir):
                                for f in fs:
                                    if f.lower().endswith('.pdf'):
                                        pdf_paths.append(_os.path.join(root, f))
                            if pdf_paths:
                                try:
                                    import camelot  # type: ignore
                                except Exception:
                                    camelot = None
                                for pdf_path in pdf_paths:
                                    lines = []
                                    tables = None
                                    if camelot is not None:
                                        try:
                                            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
                                        except Exception:
                                            try:
                                                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
                                            except Exception:
                                                tables = None
                                    if not tables or getattr(tables, 'n', 0) == 0:
                                        continue
                                    for t in tables:
                                        try:
                                            df = t.df
                                            for row in df.values.tolist():
                                                row_text = " | ".join([str(x).strip() for x in row if str(x).strip()])
                                                if any(c.isdigit() for c in row_text):
                                                    lines.append(row_text)
                                        except Exception:
                                            continue
                                    if lines:
                                        text = "\n".join(lines)
                                        try:
                                            sidecar = pdf_path + '.tables.txt'
                                            with open(sidecar, 'w', encoding='utf-8') as fh:
                                                fh.write(text)
                                        except Exception:
                                            pass
                                        # Append as a lightweight document to improve recall
                                        documents.append(
                                            Document(
                                                text=text,
                                                metadata={
                                                    'file_path': sidecar if 'sidecar' in locals() else (pdf_path + '::tables'),
                                                    'source_pdf': pdf_path,
                                                }
                                            )
                                        )
                        except Exception as _te:
                            logging.warning(f"Table extraction skipped due to error: {_te}")

                    index = VectorStoreIndex.from_documents(documents)
                    index.storage_context.persist(persist_dir=tenant_storage_dir)
                
                query_engine = index.as_query_engine(
                    similarity_top_k=10,  # Retrieve focused set of candidates (reduced from 15)
                    node_postprocessors=[reranker],
                    similarity_cutoff=0.5  # Filter out low-relevance results
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

    def _resolve_tenants_in_text(self, text: str):
        """Return list of tenant IDs explicitly mentioned in text via exact tenant IDs or aliases.
        Deduplicated, preserves order of first appearance.
        """
        found = []
        seen = set()
        ql = (text or "").lower()
        # direct tenant ID matches
        for t in self.tenants:
            if t and t.lower() in ql:
                if t not in seen:
                    seen.add(t)
                    found.append(t)
        # aliases
        for alias, tenant in (self.alias_to_tenant or {}).items():
            if alias in ql:
                tid = tenant
                if tid in self.tenants and tid not in seen:
                    seen.add(tid)
                    found.append(tid)
        return found

    # -------------------- Routing normalization --------------------
    def _normalize_for_routing(self, text: str) -> str:
        """Normalize user query for routing/tenant selection only.
        - Lowercase, NFKC normalize
        - Remove punctuation
        - Remove common stopwords and filler phrases
        We still send the ORIGINAL query to the LLM and retrieval engine.
        """
        try:
            sw = {
                'a','an','the','and','or','but','if','then','else','for','to','of','in','on','at','by','with','from','as','about','is','are','was','were','be','being','been','it','this','that','these','those','do','does','did','doing','have','has','had','having','you','your','yours','me','my','we','our','ours','they','their','them','i','he','she','his','her','him','what','which','who','whom','whose','when','where','why','how','can','could','should','would','will','shall','may','might','also','please','kindly','hi','hello','hey','thanks','thank','regards'
            }
            t = unicodedata.normalize('NFKC', text or '')
            t = t.lower()
            t = re.sub(r"[^a-z0-9\s]", " ", t)
            tokens = [w for w in t.split() if w not in sw and len(w) > 1]
            return " ".join(tokens).strip()
        except Exception:
            return (text or '').strip()

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
        stop = {"a","an","the","and","or","to","from","for","why","it","is","are","was","were","be","being","been","use","used","of","in","on","at","by","with","what","which","who","whom","how","when","where","hello","hi","hey","please"}
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

    def _smart_truncate_context(self, source_nodes, max_tokens=3500):
        """
        Intelligently truncate context to fit within token limits while preserving
        the most relevant information. Already reranked nodes are prioritized.
        
        Args:
            source_nodes: List of source nodes (already reranked by relevance)
            max_tokens: Maximum tokens allowed (default 3500 to leave room for prompt + response)
        
        Returns:
            Truncated context string with most relevant information
        """
        try:
            # Initialize tokenizer (cl100k_base is used by most modern models)
            encoding = tiktoken.get_encoding("cl100k_base")
            
            # Nodes are already reranked, so we take them in order of relevance
            selected_chunks = []
            total_tokens = 0
            
            for node in source_nodes:
                content = node.get_content()
                # Count tokens in this chunk
                chunk_tokens = len(encoding.encode(content))
                
                # If adding this chunk stays within limit, include it
                if total_tokens + chunk_tokens <= max_tokens:
                    selected_chunks.append(content)
                    total_tokens += chunk_tokens
                else:
                    # If we can't fit the whole chunk, try to fit part of it
                    remaining_tokens = max_tokens - total_tokens
                    if remaining_tokens > 100:  # Only add if we have meaningful space
                        # Truncate the chunk to fit remaining space
                        tokens = encoding.encode(content)[:remaining_tokens]
                        truncated_content = encoding.decode(tokens) + "... [truncated]"
                        selected_chunks.append(truncated_content)
                    break
            
            context = "\n\n".join(selected_chunks)
            
            # Log the truncation
            if len(selected_chunks) < len(source_nodes):
                logging.info(f"Context truncated: Used {len(selected_chunks)}/{len(source_nodes)} chunks (~{total_tokens} tokens)")
            
            return context
            
        except Exception as e:
            logging.warning(f"Token counting failed, using fallback truncation: {e}")
            # Fallback: simple character-based truncation
            fallback_context = "\n\n".join([r.get_content() for r in source_nodes])
            max_chars = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars
            if len(fallback_context) > max_chars:
                fallback_context = fallback_context[:max_chars] + "\n\n... [context truncated to fit token limit]"
            return fallback_context

    def _format_rag_response(self, query, rag_response, selected_tenant):
        # Use smart truncation to ensure context fits within token limits
        # Keep most relevant information from reranked nodes
        # Max tokens: 3500 for context + ~1000 for prompt/instructions + ~1500 for response = ~6000 total (under Groq limit)
        context_str = self._smart_truncate_context(rag_response.source_nodes, max_tokens=3500)
        
        prompt = f"""
        You are a professional AI assistant providing concise, accurate information to company employees. Your purpose is to deliver ONLY the most relevant information based STRICTLY on the provided context.

        CRITICAL RULES:
        1.  **NO HALLUCINATIONS:** If the answer is not in the `CONTEXT` below, you MUST state that you could not find the information in the available documents. Do not use any outside knowledge.
        2.  **STRICTLY USE CONTEXT:** Base your entire response on the `CONTEXT` provided. Extract ONLY information that directly answers the user's question.
        3.  **PROFESSIONAL & CONCISE:** Provide clear, professional responses. Be direct and avoid unnecessary elaboration. Each sentence must add value.
        4.  **RELEVANCE FIRST:** Include ONLY information that directly addresses the user's specific question. Omit tangential or background information unless explicitly asked.
        5.  **CODE SNIPPETS:** If the context contains any code blocks (e.g., XML, JSON, Python), extract them exactly as they are.
        6.  **DOWNLOAD INTENT:** If the user query contains keywords like "download", "form", "get", "obtain", or "document", identify the most relevant filename(s) from the context and include them in the `downloadable_files` list.
        7.  **CONSISTENT FORMATTING:** In `detailed_response`, write concise, parallel bullets or short paragraphs. Keep structure consistent and on-topic.
        8.  **PRECISION OVER VOLUME:** Answer precisely what was asked. If multiple tenants are involved, integrate only the relevant evidence and clearly note any key differences.

        CONTEXT FROM TENANT '{selected_tenant}':
        ---
        {context_str if context_str.strip() else "No relevant context found."}
        ---

        USER QUERY: "{query}"

        Based on the rules and context, provide a structured response in a single JSON object.

        RESPONSE FORMAT (JSON object only):
        {{
            "summary": "Concise 1-2 sentence summary with ONLY the most relevant information from context. If no context, say that clearly.",
            "detailed_response": "Focused, professional answer with ONLY information directly relevant to the question. Use clear bullet points or short paragraphs. Avoid filler content. If no context, state that the information is not in the documents.",
            "key_points": ["List of 2-4 key takeaways that DIRECTLY answer the question. Include only essential information. If none, return empty list."],
            "suggestions": ["List of 1-2 practical next steps based ONLY on relevant context. Omit generic advice. If none, return empty list."],
            "follow_up_questions": ["List of 1-2 highly relevant follow-up questions that can be answered from the context. If none, return empty list."],
            "code_snippets": [],
        }}

        IMPORTANT OUTPUT RULES:
        - Output MUST be a single valid JSON object and NOTHING else. Do not add headings or lists after the JSON.
        - Escape all newlines within string values as \n. Do not include raw line breaks inside JSON strings.
        - Be concise and professional. Every piece of information must be directly relevant to the user's question.
        - Quality over quantity: Provide focused, useful information rather than comprehensive overviews.
        """
        ql = (query or '').lower()
        wants_only_codes = any(k in ql for k in ['only code', 'only codes', 'just code', 'just codes', 'codes only'])
        code_candidates = self._extract_code_like_tokens(context_str)
        response_str = None  # Initialize to avoid UnboundLocalError
        
        # Validate total prompt size before sending to API
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            prompt_tokens = len(encoding.encode(prompt))
            if prompt_tokens > 5500:  # Leave room for response (6000 - 500 buffer)
                logging.warning(f"Prompt size ({prompt_tokens} tokens) approaching limit. Consider reducing context further.")
        except Exception:
            pass  # If token counting fails, proceed anyway
        
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
            # Check if error is due to API payload size limit or token issues
            error_msg = str(e)
            if "413" in error_msg or "Payload Too Large" in error_msg or "rate_limit_exceeded" in error_msg or "token" in error_msg.lower():
                logging.error(f"API payload/token limit exceeded for query: {query[:100]}... Error: {error_msg[:200]}")
                return {
                    "summary": "Query Retrieved Too Much Data",
                    "detailed_response": "The system retrieved more information than can be processed in one response. The context has been automatically optimized, but you may get better results by:\n\n1. **Be more specific**: Focus on one aspect at a time\n2. **Narrow the scope**: Ask about specific items or categories\n3. **Use filters**: Specify particular dates, types, or criteria\n4. **Break it down**: Split complex questions into smaller queries\n\nNote: The system now automatically keeps only the most relevant information to fit within limits.",
                    "key_points": [
                        "Your query is valid but retrieved extensive context",
                        "System automatically prioritizes most relevant information",
                        "More specific queries yield better results"
                    ],
                    "suggestions": [
                        "Rephrase with more specific criteria",
                        "Focus on one aspect of your question at a time"
                    ],
                    "follow_up_questions": [],
                    "code_snippets": [],
                    "codes": []
                }
            
            # Log the error with response if available
            if response_str:
                logging.error(f"Failed to parse LLM response into JSON: {e}. Response: {response_str[:500]}...")
            else:
                logging.error(f"LLM API call failed: {e}")
            
            # Return fallback response
            return {
                "summary": "Could not format response.",
                "detailed_response": rag_response.response if hasattr(rag_response, 'response') else "An error occurred while processing your request."
            }

    def get_response(self, query):
        if not self.router_query_engine:
            return {
                "is_conversational": True,
                "answer": "The agent is not configured yet. Please upload some documents to begin."
            }

        auto_select = "[AUTO]" in query
        if auto_select:
            query = query.replace("[AUTO]", "").strip()
        
        # Ambiguity detection (more tolerant to misspellings like 'onbording')
        ambiguous_keywords = ["onboard", "onboarding", "onbord", "onbordin", "form"]
        is_ambiguous = any(keyword in query.lower() for keyword in ambiguous_keywords)
        
        if not auto_select and is_ambiguous and not any(tenant.lower() in query.lower() for tenant in self.tenants):
            logging.info("Ambiguous query detected. Asking user for tenant selection.")
            return {
                "needs_tenant_selection": True,
                "tenants": self.tenants,
                "original_query": query
            }

        # Small-talk / greeting bypass to avoid hallucinations without context
        intent = self._detect_intent(query)
        if intent == 'small_talk':
            return {
                "is_conversational": True,
                "answer": "👋 Hi! I'm your policy bot. You can ask about policies, codes, or upload docs first. Use the Upload tab to add content, then ask me anything about it."
            }
        if intent == 'clarify':
            return {
                "is_conversational": True,
                "answer": (
                    "I can help with company or policy-related questions. Please be specific, for example: \n"
                    "- 'What are the esMD onboarding steps for RCs?'\n"
                    "- 'Show HIPAA guidance for NPI submission.'\n"
                    "- 'List CPT codes referenced in Medicare policy XYZ.'"
                )
            }

        try:
            # Initialize routing trace early to avoid NameError on later references
            trace = {
                "query": query,
                "keywords": [],
                "retrieval_query": query,
                "mentioned_tenants": [],
                "tenant_scores": [],
                "selected_tenant": None,
                "selected_score": None,
                "decision_path": None
            }
            # Build retrieval keywords and construct retrieval_query for routing/retrieval
            def _extract_keywords(q: str, k_max: int = 8):
                try:
                    text = (q or '').lower()
                    text = re.sub(r"[^a-z0-9\s]", " ", text)
                    tokens = [t for t in text.split() if len(t) >= 3]
                    stop = set(["the","and","for","with","that","this","from","your","about","have","what","which","when","where","will","there","into","those","been","being","were","are","how","make","made","like","such","use","uses","used","using","can","you","please","tell","more","info","info.","step","steps","process","guide","guidance","policy","policies","onboarding","onboard","form","forms","rc","rcs"])  # basic stoplist
                    freq = {}
                    for t in tokens:
                        if t in stop:
                            continue
                        freq[t] = freq.get(t, 0) + 1
                    domain_terms = [t for t in ["esmd","fhir","cms","hhs","extension","extensions","implementation","guide"] if t in tokens]
                    key = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
                    kws = [w for w, _ in key][:k_max]
                    out = []
                    for w in domain_terms + kws:
                        if w not in out:
                            out.append(w)
                    return out[:k_max]
                except Exception:
                    return []

            query_keywords = _extract_keywords(query)
            keywords_str = " ".join(query_keywords)
            retrieval_query = (f"keywords: {keywords_str}\nquestion: {query}" if query_keywords else query)
            # Try cached response if enabled. We don't know the tenant yet, so scan all tenants for a hit.
            if self.cache_enabled:
                for t in self.tenants:
                    cached = self._get_cached_response(query, t)
                    if cached:
                        logging.info(f"Serving cached response for tenant '{t}'")
                        return self._enrich_sources_with_url(cached)

            # 0) If explicit tenants mentioned in the query, honor them (single or multiple)
            ql_full = query.lower()
            mentioned = self._resolve_tenants_in_text(ql_full)
            trace["mentioned_tenants"] = mentioned
            if len(mentioned) >= 2:
                logging.info(f"Explicit multi-tenant query detected: {mentioned}")
                source_nodes = []
                for t in mentioned:
                    engine = self.tenant_tool_map.get(t)
                    if not engine:
                        continue
                    try:
                        r = engine.query(retrieval_query)
                        source_nodes.extend(list(getattr(r, 'source_nodes', []) or []))
                    except Exception:
                        continue
                if not source_nodes:
                    return {
                        "is_conversational": True,
                        "answer": "I couldn't find relevant information across the tenants you mentioned. Please refine your question or upload documents."
                    }
                class _R:
                    def __init__(self, nodes):
                        self.source_nodes = nodes
                        self.response = ''
                adapted = _R(source_nodes)
                selected_tenant = ",".join(mentioned)
                # continue to scoring/aggregation/formatting using combined nodes
            # 1) Embed query (biased by keywords) and pick best-scoring tenant via cosine similarity
            best_tenant = None
            best_score = -1.0
            try:
                route_q = self._normalize_for_routing(retrieval_query)
                q_emb = self.embed_model.get_text_embedding(route_q or query)
                # Prefer explicit tenant mention in the query
                ql = query.lower()
                explicit = None
                if len(mentioned) == 1:
                    explicit = mentioned[0]
                else:
                    # fallback single explicit from text or alias
                    exp = self._resolve_tenants_in_text(ql)
                    if len(exp) == 1:
                        explicit = exp[0]

                if explicit:
                    best_tenant = explicit
                    best_score = 1.0
                # Blend cosine similarity with tenant keyword overlap
                alpha = float(os.getenv('ROUTING_COSINE_WEIGHT', '0.7'))  # cosine weight
                for tenant_id, t_emb in self.tenant_embeddings.items():
                    cos = float(self._cosine(q_emb, t_emb))
                    # compute keyword overlap score
                    prof = self._load_tenant_profile(tenant_id)
                    kw_map = prof.get('keywords', {}) or {}
                    overlap = 0.0
                    if query_keywords and kw_map:
                        hits = sum(1 for kw in query_keywords if kw in kw_map)
                        overlap = hits / max(len(query_keywords), 1)
                    score = alpha * cos + (1.0 - alpha) * overlap
                    trace["tenant_scores"].append({"tenant": tenant_id, "cosine": cos, "overlap": overlap, "blended": float(score)})
                    if score > best_score:
                        best_score = score
                        best_tenant = tenant_id
                logging.info(f"Best tenant preselection: {best_tenant} (score={best_score:.3f})")
                trace["selected_tenant"] = best_tenant
                trace["selected_score"] = float(best_score)
            except Exception as e:
                logging.warning(f"Query embedding or tenant similarity failed, falling back to router: {e}")
                best_tenant = None

            # 2) Decision: if confident OR user requested auto-select, route directly
            if 'selected_tenant' in locals() and len(mentioned) >= 2:
                response = adapted  # already assembled combined nodes
                trace["decision_path"] = "explicit_multi_tenant"
            elif best_tenant and (best_score >= self.TENANT_MIN_CONF_THRESH or auto_select or explicit):
                selected_tenant = best_tenant
                tenant_engine = self.tenant_tool_map.get(selected_tenant)
                if tenant_engine is None:
                    logging.warning(f"No engine found for selected tenant '{selected_tenant}', falling back to router.")
                    response = self.router_query_engine.query(retrieval_query)
                    trace["decision_path"] = "router_fallback_no_engine"
                else:
                    response = tenant_engine.query(retrieval_query)
                    trace["decision_path"] = "tenant_engine"
            else:
                # Low confidence: if auto-select was requested, fall back to router silently; otherwise ask user
                if auto_select:
                    logging.info("Low-confidence routing with [AUTO]. Falling back to router engine.")
                    response = self.router_query_engine.query(retrieval_query)
                    trace["decision_path"] = "router_low_conf_with_auto"
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

            # Guardrail: if we have sources but none contain the retrieval keywords, avoid hallucinated answers
            try:
                if query_keywords:
                    kw_hits = 0
                    for n in source_nodes[:10]:  # check top-k
                        tl = (n.get_content() or '').lower()
                        if any(kw in tl for kw in query_keywords):
                            kw_hits += 1
                    if kw_hits == 0:
                        logging.warning("Retrieved content lacks query keywords; returning no-relevant-info message.")
                        trace["decision_path"] = (trace.get("decision_path") or "") + ":guard_no_keyword_hits"
                        return {
                            "is_conversational": True,
                            "answer": "I couldn't find relevant information in the documents for your question. Please provide more specifics or ingest related content.",
                            "trace": trace if str(os.getenv("SHOW_TRACE", "false")).lower() in ("1","true","yes") else None
                        }
            except Exception:
                pass

            # Aggregate by canonical source key: prefer original PDF over sidecar and collect all matched pages
            agg = {}
            for node in source_nodes:
                meta = getattr(node, 'metadata', {}) or {}
                file_path = meta.get('file_path')
                source_pdf = meta.get('source_pdf')
                key_raw = source_pdf or file_path or ""
                try:
                    key_norm = os.path.normpath(str(key_raw)).lower()
                except Exception:
                    key_norm = str(key_raw)
                if not key_norm:
                    continue
                display_name = source_pdf or file_path
                score_val = float(getattr(node, 'score', 0.0) or 0.0)
                page = meta.get('page', meta.get('page_label'))
                # init bucket
                bucket = agg.get(key_norm)
                if bucket is None:
                    bucket = {"filename": display_name, "relevance": score_val, "_pages": set()}
                    agg[key_norm] = bucket
                else:
                    # keep the best display name (prefer PDF) and highest relevance
                    if score_val > bucket.get("relevance", 0.0):
                        bucket["relevance"] = score_val
                        bucket["filename"] = display_name
                # collect page
                if page is not None:
                    try:
                        bucket["_pages"].add(int(page))
                    except Exception:
                        try:
                            # Normalize like "12" -> 12 when possible, else keep string
                            p_int = int(str(page).strip())
                            bucket["_pages"].add(p_int)
                        except Exception:
                            bucket["_pages"].add(str(page))

            # Materialize unique sources list with sorted pages
            # Load URL maps for tenants in scope (selected_tenant may be ","-joined)
            url_maps = {}
            try:
                tenants_in_scope = []
                try:
                    tenants_in_scope = [t.strip() for t in str(selected_tenant).split(',') if t.strip()]
                except Exception:
                    tenants_in_scope = [selected_tenant] if selected_tenant else []
                for t in tenants_in_scope or []:
                    url_map_path = os.path.join(self.documents_dir, t, 'url_map.json')
                    if os.path.exists(url_map_path):
                        with open(url_map_path, 'r', encoding='utf-8') as fh:
                            m = json.load(fh) or {}
                            for k, v in m.items():
                                try:
                                    url_maps[os.path.normpath(k)] = v
                                    url_maps[os.path.basename(os.path.normpath(k))] = v
                                except Exception:
                                    url_maps[k] = v
            except Exception:
                url_maps = {}

            unique_sources = []
            for _, bucket in agg.items():
                pages = list(bucket.get("_pages", set()))
                try:
                    pages = sorted(pages)
                except Exception:
                    pass
                # Prefer original source path; strip sidecar suffixes
                fn = bucket.get("filename")
                try:
                    if isinstance(fn, str):
                        if fn.endswith('.tables.txt'):
                            fn = fn[:-11]
                        if fn.endswith('::tables'):
                            fn = fn[:-8]
                except Exception:
                    pass
                # Attach original URL if this came from a URL-ingested .txt
                url_value = None
                try:
                    raw_fn = str(bucket.get("filename") or "")
                    key_norm = os.path.normpath(raw_fn)
                    base = os.path.basename(key_norm)
                    url_value = url_maps.get(key_norm) or url_maps.get(base)
                    if not url_value:
                        # Try documents/<tenant>/<basename> variants
                        for t in (tenants_in_scope or []):
                            alt = os.path.normpath(os.path.join(self.documents_dir, t, base))
                            url_value = url_maps.get(alt)
                            if url_value:
                                break
                    if not url_value:
                        logging.debug(f"URL map miss for source filename='{raw_fn}', base='{base}', tenants={tenants_in_scope}")
                except Exception:
                    url_value = None
                # relative_path: path under tenant dir for view/download (actual document, not chunk file)
                try:
                    rel_path = os.path.basename(str(fn).strip()) if fn else None
                except Exception:
                    rel_path = None
                src = {"filename": fn, "relevance": float(bucket.get("relevance", 0.0))}
                if rel_path:
                    src["relative_path"] = rel_path
                if url_value:
                    src["url"] = url_value
                if pages:
                    src["pages"] = pages
                    src["page"] = pages[0]  # first page for #page= fragment
                unique_sources.append(src)

            # De-duplicate defensively by normalized filename and keep top 2 by relevance
            dedup = {}
            for s in unique_sources:
                name = str(s.get("filename") or "").strip().lower()
                if name not in dedup or float(s.get("relevance", 0.0)) > float(dedup[name].get("relevance", 0.0)):
                    dedup[name] = s
            unique_sources = sorted(dedup.values(), key=lambda x: float(x.get("relevance", 0.0)), reverse=True)[:10]

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
            if str(os.getenv("SHOW_TRACE", "false")).lower() in ("1","true","yes"):
                structured_response["trace"] = trace
            # Ensure no leaked keys like 'downloadable_files' are returned
            if "downloadable_files" in structured_response:
                try:
                    del structured_response["downloadable_files"]
                except Exception:
                    pass
            # Write-through cache
            try:
                if self.cache_enabled:
                    self.cache_response(query, structured_response)
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
                    # keyword profiling from file content (best-effort for .txt/.source.html)
                    try:
                        text_sample = ""
                        fname_lower = (file.filename or "").lower()
                        if fname_lower.endswith('.txt') or fname_lower.endswith('.html') or fname_lower.endswith('.source.html'):
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as rf:
                                text_sample = rf.read()
                        elif fname_lower.endswith('.pdf'):
                            try:
                                import pypdf
                                reader = pypdf.PdfReader(filepath)
                                for i, pg in enumerate(reader.pages[:3]):
                                    try:
                                        text_sample += (pg.extract_text() or "") + "\n"
                                    except Exception:
                                        continue
                            except Exception:
                                pass
                        kws = self._extract_keywords_from_text(text_sample, k_max=200) if text_sample else []
                        if kws:
                            self._update_tenant_profile(tenant_id, kws)
                    except Exception:
                        pass
                    # record metadata
                    try:
                        size = os.path.getsize(filepath)
                        mtime = os.path.getmtime(filepath)
                        sha = self._hash_file(filepath)
                        self._append_metadata_entry(tenant_dir, {
                            "filename": file.filename,
                            "path": filepath,
                            "tenant": tenant_id,
                            "source_type": "file_upload",
                            "size_bytes": size,
                            "mtime": mtime,
                            "sha256": sha,
                            "created_at": time.time()
                        })
                    except Exception:
                        pass
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

    def _write_manifest(self, manifest_path: str, current_list):
        try:
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            with open(manifest_path, 'w', encoding='utf-8') as fh:
                json.dump({"files": current_list, "updated_at": time.time()}, fh, indent=2)
        except Exception:
            pass

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

    def _diff_manifest(self, prev_list, current_list):
        try:
            prev_set = set(prev_list or [])
            curr_set = set(current_list or [])
            added = list(curr_set - prev_set)
            deleted = list(prev_set - curr_set)
            # We use simple set difference; any 'changed' is handled by rebuild elsewhere
            changed = []
            return changed, deleted, added
        except Exception:
            return [], [], []

    # -------------------- Tenant keyword profiling --------------------
    def _extract_keywords_from_text(self, text: str, k_max: int = 200):
        try:
            t = (text or '').lower()
            t = re.sub(r"[^a-z0-9\s]", " ", t)
            tokens = [tok for tok in t.split() if len(tok) >= 3]
            stop = set([
                "the","and","for","with","that","this","from","your","about","have","what","which","when","where","will","there","into","those","been","being","were","are","how","make","made","like","such","use","uses","used","using","can","you","please","tell","more","info","info","step","steps","process","guide","guidance","policy","policies","form","forms","table","tables","section","sections"
            ])
            # Keep important domain terms
            domain_keep = set(["esmd","fhir","cms","hhs","extension","extensions","implementation","guide","onboarding","onboard","rc","rcs"])
            freq = {}
            for tok in tokens:
                if tok in stop and tok not in domain_keep:
                    continue
                freq[tok] = freq.get(tok, 0) + 1
            ranks = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
            return [w for w, _ in ranks[:k_max]]
        except Exception:
            return []

    def _tenant_profile_path(self, tenant_id: str):
        return os.path.join(self.documents_dir, tenant_id, 'tenant_profile.json')

    def _load_tenant_profile(self, tenant_id: str):
        try:
            path = self._tenant_profile_path(tenant_id)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    obj = json.load(fh) or {}
                    if isinstance(obj, dict):
                        return obj
            return {"keywords": {}}
        except Exception:
            return {"keywords": {}}

    def _update_tenant_profile(self, tenant_id: str, keywords: list):
        try:
            profile = self._load_tenant_profile(tenant_id)
            kw_map = profile.get('keywords', {}) or {}
            for kw in (keywords or []):
                try:
                    kw_map[kw] = int(kw_map.get(kw, 0)) + 1
                except Exception:
                    continue
            profile['keywords'] = kw_map
            path = self._tenant_profile_path(tenant_id)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(profile, fh, indent=2)
        except Exception:
            pass

    # -------------------- URL map helpers --------------------
    def _url_map_path(self, tenant_id: str):
        return os.path.join(self.documents_dir, tenant_id, 'url_map.json')

    def _load_url_map(self, tenant_id: str):
        try:
            p = self._url_map_path(tenant_id)
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as fh:
                    m = json.load(fh) or {}
                    if isinstance(m, dict):
                        return m
            return {}
        except Exception:
            return {}

    def _update_url_map(self, tenant_id: str, key_path: str, src_url: str):
        try:
            if not key_path or not src_url:
                return
            m = self._load_url_map(tenant_id)
            m[os.path.normpath(key_path)] = src_url
            # Also store basename as convenience
            try:
                base = os.path.basename(os.path.normpath(key_path))
                m[base] = src_url
            except Exception:
                pass
            p = self._url_map_path(tenant_id)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as fh:
                json.dump(m, fh, indent=2)
        except Exception:
            pass

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

            # Write initial extract from reader
            extracted = ''
            try:
                extracted = "\n\n".join([(doc.text or '') for doc in documents])
            except Exception:
                extracted = ''
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(extracted)

            # If extract seems too small, perform robust fallback: fetch full HTML, save snapshot, strip tags
            try:
                min_chars = int(os.getenv('URL_MIN_CHARS_FOR_FALLBACK', '2000'))
            except Exception:
                min_chars = 2000
            if len((extracted or '').strip()) < min_chars:
                try:
                    headers = {'User-Agent': os.getenv('URL_USER_AGENT', 'Mozilla/5.0 (RAG Ingest)')}
                    timeout = int(os.getenv('URL_TIMEOUT', '20'))
                    r = requests.get(url, headers=headers, timeout=timeout)
                    r.raise_for_status()
                    html_raw = r.text or ''
                    # Save snapshot for audit
                    snapshot_path = os.path.join(tenant_dir, sanitized_filename.replace('.txt', '.source.html'))
                    try:
                        with open(snapshot_path, 'w', encoding='utf-8') as sf:
                            sf.write(html_raw)
                    except Exception:
                        pass
                    # Strip scripts/styles and tags
                    no_scripts = re.sub(r'<script[\s\S]*?</script>', ' ', html_raw, flags=re.IGNORECASE)
                    no_styles = re.sub(r'<style[\s\S]*?</style>', ' ', no_scripts, flags=re.IGNORECASE)
                    text_only = re.sub(r'<[^>]+>', ' ', no_styles)
                    text_only = html_lib.unescape(text_only)
                    text_only = re.sub(r'\s+', ' ', text_only)
                    text_only = re.sub(r'\n{2,}', '\n', text_only)
                    # Overwrite .txt with fuller text
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(text_only.strip())
                except Exception as _:
                    pass

            # Update tenant keyword profile from extracted text and snapshot (if present)
            try:
                prof_text = ""
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as rf:
                        prof_text += rf.read()
                except Exception:
                    pass
                snapshot_path = os.path.join(tenant_dir, sanitized_filename.replace('.txt', '.source.html'))
                if os.path.exists(snapshot_path):
                    try:
                        with open(snapshot_path, 'r', encoding='utf-8', errors='ignore') as sf:
                            prof_text += "\n" + sf.read()
                    except Exception:
                        pass
                kws = self._extract_keywords_from_text(prof_text, k_max=200) if prof_text else []
                if kws:
                    self._update_tenant_profile(tenant_id, kws)
            except Exception:
                pass

            # Record URL mapping so sources can reference original page URL
            try:
                self._update_url_map(tenant_id, filepath, url)
            except Exception:
                pass

            # record metadata for .txt and snapshot if present
            try:
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                sha = self._hash_file(filepath)
                self._append_metadata_entry(tenant_dir, {
                    "filename": sanitized_filename,
                    "path": filepath,
                    "tenant": tenant_id,
                    "source_type": "url",
                    "url": url,
                    "size_bytes": size,
                    "mtime": mtime,
                    "sha256": sha,
                    "created_at": time.time()
                })
            except Exception:
                pass
            try:
                snapshot_path = os.path.join(tenant_dir, sanitized_filename.replace('.txt', '.source.html'))
                if os.path.exists(snapshot_path):
                    size = os.path.getsize(snapshot_path)
                    mtime = os.path.getmtime(snapshot_path)
                    sha = self._hash_file(snapshot_path)
                    self._append_metadata_entry(tenant_dir, {
                        "filename": os.path.basename(snapshot_path),
                        "path": snapshot_path,
                        "tenant": tenant_id,
                        "source_type": "url_snapshot",
                        "url": url,
                        "size_bytes": size,
                        "mtime": mtime,
                        "sha256": sha,
                        "created_at": time.time()
                    })
            except Exception:
                pass
            
            tenant_storage_dir = os.path.join(self.storage_dir, tenant_id)
            manifest_path = os.path.join(tenant_storage_dir, "manifest.json")
            # Persist URL mapping so later responses can attach original URLs in sources
            try:
                url_map_path = os.path.join(tenant_dir, 'url_map.json')
                url_map = {}
                if os.path.exists(url_map_path):
                    with open(url_map_path, 'r', encoding='utf-8') as fh:
                        url_map = json.load(fh) or {}
                # map by full normalized path and by basename
                url_map[os.path.normpath(filepath)] = url
                url_map[os.path.basename(os.path.normpath(filepath))] = url
                with open(url_map_path, 'w', encoding='utf-8') as fh:
                    json.dump(url_map, fh, indent=2)
            except Exception:
                pass
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



