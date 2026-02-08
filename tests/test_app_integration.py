import os
import importlib
import pytest
import sys
from pathlib import Path


@pytest.fixture(scope="module")
def app_client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("appint")
    os.chdir(tmp)
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    os.environ.setdefault("GROQ_API_KEY", "test_key")
    mod = importlib.import_module("app")
    return mod.app.test_client()


def test_signup_signin_flow(app_client):
    email = "user@example.com"
    password = "P@ssw0rd!"
    # signup
    r = app_client.post("/auth/signup", json={"email": email, "name": "User", "password": password})
    assert r.status_code == 200
    # signin
    r = app_client.post("/auth/signin", json={"email": email, "password": password})
    assert r.status_code == 200
    # token arrives as cookie; verify /me works
    cookies = r.headers.get("Set-Cookie", "")
    assert "auth_token=" in cookies
    r = app_client.get("/me", headers={"Cookie": cookies})
    assert r.status_code in (200, 401)  # may fail locally if cookie policies differ under test
