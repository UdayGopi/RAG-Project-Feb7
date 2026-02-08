"""
Async API for RAG application (FastAPI).
Run with: uvicorn api_async:app --host 0.0.0.0 --port 5002

Use this for non-blocking I/O: multiple chat requests can be in flight
while waiting on Bedrock/OpenSearch. Sync RAG logic runs in a thread pool.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

# Load .env before any app or config imports that need env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Lazy init RAG agent in lifespan so we don't block event loop at import
rag_agent = None

def get_agent():
    global rag_agent
    if rag_agent is None:
        try:
            from agents import get_rag_agent
            rag_agent = get_rag_agent()
        except Exception:
            from rag_agent import RAGAgent
            rag_agent = RAGAgent()
    return rag_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG agent at startup (runs in thread so event loop is not blocked)."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_agent)
    yield


app = FastAPI(title="RAG API (Async)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str
    tenant_id: str | None = None


class ChatResponse(BaseModel):
    summary: str
    detailed_response: str
    sources: list
    confidence: float | None = None
    error: str | None = None


@app.get("/health")
async def health():
    """Health check."""
    agent = get_agent()
    return {
        "status": "healthy",
        "async": True,
        "router_enabled": getattr(agent, "router_query_engine", None) is not None,
        "tenants": getattr(agent, "list_tenants", lambda: [])(),
    }


@app.post("/chat", response_model=None)
async def chat(request: ChatRequest):
    """Async chat: runs sync RAG in thread pool so server stays responsive."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    agent = get_agent()
    loop = asyncio.get_event_loop()
    try:
        # Run blocking RAG call in executor so we don't block the event loop
        if hasattr(agent, "query"):
            response = await loop.run_in_executor(
                None,
                lambda: agent.query(request.query, request.tenant_id),
            )
        else:
            response = await loop.run_in_executor(
                None,
                lambda: agent.get_response(request.query),
            )
        return response
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/router-info")
async def router_info():
    """Router and tenants info."""
    agent = get_agent()
    return {
        "router_enabled": getattr(agent, "router_query_engine", None) is not None,
        "tenants": getattr(agent, "list_tenants", lambda: [])(),
        "tools_count": len(getattr(agent, "tools", [])),
    }


@app.get("/tenants")
async def tenants():
    """List tenants."""
    agent = get_agent()
    return {"tenants": getattr(agent, "list_tenants", lambda: [])()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_async:app", host="0.0.0.0", port=5002, reload=True)
