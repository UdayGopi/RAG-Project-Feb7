import os
import types
import importlib
import pytest
import sys
from pathlib import Path


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Isolate CWD so sqlite/chat history write into temp dir
    tmp = tmp_path_factory.mktemp("appdata")
    os.chdir(tmp)
    # Ensure project root is importable regardless of CWD
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    # Ensure env for RAGAgent init
    os.environ.setdefault("GROQ_API_KEY", "test_key")
    # Import app
    app_module = importlib.import_module("app")
    # Patch rag_agent with a lightweight stub
    class DummyAgent:
        def get_response(self, query):
            return {
                "summary": "ok",
                "detailed_response": "details",
                "key_points": [],
                "suggestions": [],
                "follow_up_questions": [],
                "code_snippets": [],
                "sources": [],
                "needs_tenant_selection": False,
                "selected_tenant": None,
            }
        def cache_response(self, q, r):
            return None
        def rephrase_query(self, q):
            return {"suggestions": ["Try a more specific question."]}
    app_module.rag_agent = DummyAgent()
    return app_module.app.test_client()


def test_auth_providers_ok(client):
    resp = client.get("/auth/providers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "google" in data and "microsoft" in data


def test_chat_endpoint_happy_path(client):
    resp = client.post("/chat", json={"query": "hello"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "summary" in data and "detailed_response" in data


def test_chat_endpoint_requires_query(client):
    resp = client.post("/chat", json={})
    assert resp.status_code == 400
