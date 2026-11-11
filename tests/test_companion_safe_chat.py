"""Companion confinement and real subprocess model HTTP transport."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from companion import safe_chat as safe


@pytest.fixture
def model_process():
    code = r'''
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class H(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n))
        ok = self.path == "/v1/chat/completions" and self.headers.get("Authorization") == "Bearer fixture-key" and body.get("stream") is False and "tools" not in body
        data = json.dumps({"choices": [{"message": {"content": "fixture reply"}}]}).encode()
        self.send_response(200 if ok else 403)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
s = HTTPServer(("127.0.0.1", 0), H)
print(s.server_port, flush=True)
s.serve_forever()
'''
    proc = subprocess.Popen([sys.executable, "-u", "-c", code], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        port = int(proc.stdout.readline())
        yield port
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        proc.stdout.close()


@pytest.fixture
def client(tmp_path, monkeypatch, model_process):
    key = tmp_path / "fixture-key.txt"
    key.write_text("fixture-key", encoding="utf-8")
    monkeypatch.setattr(safe, "_key_file", lambda: key)
    monkeypatch.setattr(safe, "_LOCAL_URL", f"http://127.0.0.1:{model_process}/v1/chat/completions")
    app = FastAPI()
    @app.middleware("http")
    async def fixture_auth(request: Request, call_next):
        # Isolated auth adapter: never claim this tests production token middleware.
        if request.headers.get("authorization") == "Bearer fixture-token":
            request.state.api_token = True
            request.state.api_token_scopes = ["chat", "companion"]
        return await call_next(request)
    app.add_api_route("/api/companion/safe-chat", safe.safe_chat, methods=["POST"])
    with TestClient(app) as test_client:
        yield test_client


def test_local_model_real_child_process_and_auth(client):
    body = {"messages": [{"role": "user", "content": "hello"}]}
    assert client.post("/api/companion/safe-chat", json=body).status_code == 403
    response = client.post("/api/companion/safe-chat", json=body, headers={"Authorization": "Bearer fixture-token"})
    assert response.status_code == 200
    assert response.json() == {"response": "fixture reply"}
    assert response.headers["cache-control"] == "no-store"
    assert "fixture-key" not in response.text


@pytest.mark.parametrize("body", [{"messages": [{"role": "system", "content": "x"}]},
    {"messages": [{"role": "user", "content": "x"}], "tools": []},
    {"messages": [{"role": "assistant", "content": "x"}]}, {"messages": []}])
def test_invalid_body_rejected(client, body):
    response = client.post("/api/companion/safe-chat", json=body, headers={"Authorization": "Bearer fixture-token"})
    assert response.status_code == 422


def test_companion_route_whitelist():
    assert safe.companion_route_allowed("POST", "/api/companion/safe-chat")
    for path in ("/api/chat_stream", "/api/v1/chat", "/api/companion/pair", "/api/webhooks", "/api/tools/bash", "/api/companion/models"):
        assert not safe.companion_route_allowed("POST", path)
        assert not safe.companion_route_allowed("GET", path)


def test_model_unavailable(client, monkeypatch):
    monkeypatch.setattr(safe, "_LOCAL_URL", "http://127.0.0.1:1/v1/chat/completions")
    response = client.post("/api/companion/safe-chat", json={"messages": [{"role": "user", "content": "hello"}]}, headers={"Authorization": "Bearer fixture-token"})
    assert response.status_code == 503
    assert "fixture-key" not in response.text


def test_real_auth_middleware_confines_companion_in_separate_process(tmp_path):
    import os
    import textwrap
    root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env.update({"AUTH_ENABLED": "true", "LOCALHOST_BYPASS": "false", "PYTHON_DOTENV_DISABLED": "1",
                "ODYSSEUS_DISABLE_MCP": "1", "ODYSSEUS_DATA_DIR": str(tmp_path),
                "DATABASE_URL": f"sqlite:///{tmp_path / 'auth.db'}", "PYTHONPATH": str(root),
                "CHROMADB_HOST": "127.0.0.1", "CHROMADB_PORT": "9", "CHROMADB_CONNECT_TIMEOUT": "0.01"})
    probe = textwrap.dedent('''
        import bcrypt
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import app as module
        class Manager:
            is_configured = True
        module.auth_manager = Manager()
        token = 'ody_fixture_token_for_testing'
        digest = bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
        ordinary = 'ody_ordinary_token_for_testing'
        ordinary_digest = bcrypt.hashpw(ordinary.encode(), bcrypt.gensalt()).decode()
        module._token_cache = {token[:8]: [('id', digest, 'fixture-owner', ['chat', 'companion'])], ordinary[:8]: [('id2', ordinary_digest, 'fixture-owner', ['chat'])]}
        module.app.state._token_cache_dirty = False
        target = FastAPI()
        @target.api_route('/{rest:path}', methods=['GET', 'POST'])
        def reached(): return {'reached': True}
        target.add_middleware(module.AuthMiddleware)
        with TestClient(target) as c:
            headers = {'Authorization': 'Bearer ' + token}
            assert c.post('/api/companion/safe-chat', headers=headers).status_code == 200
            for path in ['/api/chat_stream', '/api/v1/chat', '/api/webhooks', '/api/companion/pair', '/api/tools/bash']:
                assert c.post(path, headers=headers).status_code == 403
            assert c.post('/api/companion/safe-chat', headers={'Authorization': 'Bearer ody_invalid_token'}).status_code == 401
            assert c.post('/api/chat_stream', headers={'Authorization': 'Bearer ' + ordinary}).status_code == 200
        print('PASS')
    ''')
    result = subprocess.run([sys.executable, "-c", probe], env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr[-3000:]
    assert "PASS" in result.stdout
