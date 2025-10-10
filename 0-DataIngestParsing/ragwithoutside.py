import os
import re
import logging
import json
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage, download_loader
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import RouterQueryEngine, BaseQueryEngine
from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.base.response.schema import Response
from llama_index.core.schema import QueryBundle
from typing import Dict, Any, List, Optional
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.llms import ChatMessage, MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ConversationalQueryEngine(BaseQueryEngine):
    """A custom query engine that signals a conversational query."""

    def __init__(
        self,
        callback_manager: Optional[CallbackManager] = None,
    ) -> None:
        super().__init__(callback_manager=callback_manager or CallbackManager())

    def _query(self, query_bundle: QueryBundle) -> Response:
        return Response(response="CONVERSATIONAL_MARKER")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self) -> Dict[str, Any]:
        return {}


class RAGAgent:
    def __init__(self, documents_dir="documents", storage_dir="storage"):
        self.documents_dir = documents_dir
        self.storage_dir = storage_dir
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")

        self.llm = Groq(model="llama-3.1-8b-instant", api_key=groq_api_key)
        self.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        logging.info("Groq LLM and HuggingFace Embedding Model initialized.")

        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.chunk_size = 1024
        Settings.chunk_overlap = 100
        logging.info("LlamaIndex settings configured.")

        self.web_reader = download_loader("TrafilaturaWebReader")()
        self.query_engine = None
        self._rebuild_index_and_engine()

    def _rebuild_index_and_engine(self):
        try:
            if os.path.exists(self.storage_dir) and os.listdir(self.storage_dir):
                logging.info(f"Loading existing index from '{self.storage_dir}'...")
                storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
                self.index = load_index_from_storage(storage_context)
            else:
                logging.info(f"Building new index from documents in '{self.documents_dir}'...")
                documents = SimpleDirectoryReader(self.documents_dir, recursive=True).load_data() if os.path.exists(self.documents_dir) and os.listdir(self.documents_dir) else []
                self.index = VectorStoreIndex.from_documents(documents)
                self.index.storage_context.persist(persist_dir=self.storage_dir)
                logging.info(f"New index built and persisted to '{self.storage_dir}'.")
            
            rag_query_engine = self.index.as_query_engine(
                similarity_top_k=5,
                node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)]
            )
            rag_tool = QueryEngineTool.from_defaults(
                query_engine=rag_query_engine,
                name="policy_document_retriever",
                description="Use for any questions that require looking up specific information in the company's policy documents.",
            )

            conversational_tool = QueryEngineTool(
                query_engine=ConversationalQueryEngine(),
                metadata=ToolMetadata(
                    name="conversational_chat",
                    description="Use for general conversation, greetings, or questions that do not require accessing internal documents.",
                )
            )

            self.query_engine = RouterQueryEngine(
                selector=PydanticSingleSelector.from_defaults(llm=self.llm),
                query_engine_tools=[conversational_tool, rag_tool],
                verbose=True
            )
            logging.info("Router Query Engine initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to create vector store index or agent: {e}", exc_info=True)
            self.query_engine = None

    def _format_rag_response(self, query, rag_response):
        context_str = "\n\n".join([r.get_content() for r in rag_response.source_nodes])
        
        prompt = f"""
        You are a professional AI assistant for company employees. Your purpose is to provide accurate information based SOLELY on the provided context.

        RULES:
        1.  **NO HALLUCINATIONS:** If the answer is not in the `CONTEXT` below, you MUST state that you could not find the information in the available documents. Do not use any outside knowledge.
        2.  **STRICTLY USE CONTEXT:** Base your entire response on the `CONTEXT` provided.
        3.  **PROFESSIONAL TONE:** Frame your answers in a clear, professional, and helpful manner.

        CONTEXT:
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
            "follow_up_questions": ["List of 2-3 relevant follow-up questions that can be answered from the context. If none, return an empty list."]
        }}
        """
        try:
            response_str = self.llm.complete(prompt).text
            response_str = re.sub(r'^```json\s*|\s*```$', '', response_str, flags=re.MULTILINE)
            return json.loads(response_str)
        except Exception as e:
            logging.error(f"Failed to parse LLM response into JSON: {e}. Response: {response_str}")
            return {"summary": "Could not format response.", "detailed_response": rag_response.response}

    def get_response(self, query):
        if not self.query_engine:
            return {"summary": "Error", "detailed_response": "Agent not available."}
        try:
            response = self.query_engine.query(query)
            
            if response.response == "CONVERSATIONAL_MARKER":
                logging.info("Handling as a conversational query.")
                chat_response = self.llm.chat([ChatMessage(role=MessageRole.USER, content=query)])
                return {
                    "is_conversational": True,
                    "answer": chat_response.message.content,
                }
            
            if not response.source_nodes:
                logging.warning(f"No relevant documents found for query: '{query}'.")
                # PERMANENT FIX: Return a direct "not found" message instead of rephrasing.
                return {
                    "is_conversational": True,
                    "answer": "I'm sorry, but I couldn't find any relevant information in the documents for your query. Please try asking in a different way."
                }

            logging.info("Handling as a RAG query. Formatting response...")
            sources = [{"filename": node.metadata.get('file_path', 'N/A'), "relevance": node.score} for node in response.source_nodes] if hasattr(response, 'source_nodes') else []
            structured_response = self._format_rag_response(query, response)
            structured_response["sources"] = sources
            return structured_response
        except Exception as e:
            logging.error(f"Error getting response from agent for query '{query}': {e}", exc_info=True)
            return {"summary": "Error", "detailed_response": "I encountered an error processing your request."}

    def rephrase_query(self, query):
        prompt = f'Rephrase the following user query in 3 different ways to improve search results. Return ONLY a single JSON object with a "suggestions" key containing a list of strings.\n\nORIGINAL QUERY: "{query}"'
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
            try:
                filepath = os.path.join(tenant_dir, file.filename)
                file.save(filepath)
                saved_files.append(file.filename)
            except Exception as e:
                errors.append(f"Error saving {file.filename}: {e}")
        
        if saved_files:
            logging.info("New content added. Triggering full index rebuild.")
            if os.path.exists(self.storage_dir):
                import shutil
                shutil.rmtree(self.storage_dir)
            self._rebuild_index_and_engine()
        return saved_files, errors

    def ingest_url(self, tenant_id, url):
        try:
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
            
            logging.info(f"New content added from URL. Triggering rebuild.")
            if os.path.exists(self.storage_dir):
                import shutil
                shutil.rmtree(self.storage_dir)
            self._rebuild_index_and_engine()
            return [sanitized_filename], []
        except Exception as e:
            logging.error(f"Error ingesting URL '{url}': {e}", exc_info=True)
            return [], [f"Failed to ingest URL {url}: {e}"]

