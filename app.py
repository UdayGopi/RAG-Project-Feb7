from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import logging # PERMANENT FIX: Import the logging module
from datetime import datetime, timedelta
from uuid import uuid4
from collections import Counter
from rag_agent import RAGAgent
import sqlite3
import hashlib
import jwt
from authlib.integrations.flask_client import OAuth
from typing import Optional

# Load environment variables from .env file
load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True)

# Initialize the RAG agent
rag_agent = RAGAgent()
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_change_me")
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "10080"))  # 7 days default
CHAT_HISTORY_FILE = os.path.join(os.getcwd(), "history.json")

# OAuth setup (optional; enabled when client IDs are present)
oauth = OAuth(app)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5001")

# Optional S3 storage toggle for uploads
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()  # "local" or "s3"
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "documents")
AWS_REGION = os.getenv("AWS_REGION")

def _s3_enabled() -> bool:
    return STORAGE_BACKEND == "s3" and bool(S3_BUCKET)

_boto3 = None

def _get_s3_client():
    global _boto3
    if not _s3_enabled():
        return None
    try:
        if _boto3 is None:
            import boto3  # lazy import
            _boto3 = boto3
        session_kwargs = {}
        if AWS_REGION:
            session_kwargs["region_name"] = AWS_REGION
        session = _boto3.session.Session(**session_kwargs)
        return session.client("s3")
    except Exception as e:
        logging.error(f"S3 client init failed: {e}")
        return None

# --- Schedules storage helpers ---
SCHEDULES_FILE = os.path.join(os.getcwd(), "schedules.json")

def _load_schedules():
    if not os.path.exists(SCHEDULES_FILE):
        return []
    try:
        with open(SCHEDULES_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return []

def _save_schedules(items):
    try:
        with open(SCHEDULES_FILE, 'w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2)
    except Exception as e:
        logging.error(f"Failed to save schedules: {e}")

def _s3_upload_file(local_path: str, tenant_id: str, filename: str) -> Optional[str]:
    try:
        s3 = _get_s3_client()
        if not s3:
            return None
        key = f"{S3_PREFIX.rstrip('/')}/{tenant_id}/{filename}"
        s3.upload_file(local_path, S3_BUCKET, key)
        logging.info(f"Uploaded to s3://{S3_BUCKET}/{key}")
        return key
    except Exception as e:
        logging.error(f"S3 upload failed for {filename}: {e}")
        return None

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
if MS_CLIENT_ID and MS_CLIENT_SECRET:
    oauth.register(
        name='microsoft',
        client_id=MS_CLIENT_ID,
        client_secret=MS_CLIENT_SECRET,
        server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@app.route('/auth/providers', methods=['GET'])
def auth_providers():
    return jsonify({
        "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "microsoft": bool(MS_CLIENT_ID and MS_CLIENT_SECRET)
    })

# --- Chat History Functions (per-user isolation) ---
CHAT_HISTORY_DIR = os.path.join(os.getcwd(), "chat_history")
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

def _history_path(uid: int) -> str:
    safe_uid = str(uid).strip()
    return os.path.join(CHAT_HISTORY_DIR, f"history_{safe_uid}.json")

def load_chat_history(uid: int | None = None):
    if uid is None:
        return []
    path = _history_path(uid)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_chat_history(uid: int, history):
    path = _history_path(uid)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def add_to_history(query, response):
    user = _get_auth_user()
    if not user:
        # If unauth, do not persist; fail silently to keep chat functional
        return
    uid = user.get('id')
    history = load_chat_history(uid)
    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "response": response
    })
    save_chat_history(uid, history)

############################
# Auth and User Management #
############################

DB_PATH = os.path.join(os.getcwd(), "users.db")

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    try:
        conn = _db()
        cur = conn.cursor()
        # Better concurrency for light multi-user workloads
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                avatar_url TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

def _hash_password(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()

def _make_token(payload: dict) -> str:
    data = dict(payload)
    data["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXPIRES_MIN)
    return jwt.encode(data, JWT_SECRET, algorithm="HS256")

def _verify_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])  # returns dict
    except Exception:
        return None

def _get_auth_user():
    token = None
    # Prefer HttpOnly cookie
    if 'auth_token' in request.cookies:
        token = request.cookies.get('auth_token')
    # Allow Authorization: Bearer
    if not token:
        auth = request.headers.get('Authorization', '')
        if auth.lower().startswith('bearer '):
            token = auth.split(' ', 1)[1].strip()
    if not token:
        return None
    data = _verify_token(token)
    if not data:
        return None
    # Fetch minimal profile
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, avatar_url FROM users WHERE id = ?", (data.get('uid'),))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

def _startup():
    _init_db()

# Initialize DB on module import (Flask 3.x: before_first_request removed)
_startup()

def _upsert_oauth_user(email: str, name: str, avatar_url: str) -> int:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (email.lower(),))
        row = cur.fetchone()
        if row:
            uid = row[0]
            # Update name/avatar if changed
            cur.execute("UPDATE users SET name = ?, avatar_url = ? WHERE id = ?", (name, avatar_url, uid))
            conn.commit()
            return uid
        cur.execute(
            "INSERT INTO users (email, name, password_hash, avatar_url, created_at) VALUES (?, ?, ?, ?, ?)",
            (email.lower(), name, _hash_password('oauth'), avatar_url, datetime.utcnow().isoformat())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

@app.route('/auth/login/<provider>')
def oauth_login(provider: str):
    if provider not in ('google', 'microsoft'):
        return jsonify({"error": "unsupported provider"}), 400
    client = oauth.create_client(provider)
    if not client:
        return jsonify({"error": f"{provider} not configured"}), 400
    redirect_uri = f"{APP_BASE_URL}/auth/callback/{provider}"
    extra = {}
    if provider == 'google':
        # Ensure account picker shows; offline access can provide refresh_token on server-side if needed
        extra = {"prompt": "select_account", "access_type": "offline"}
    return client.authorize_redirect(redirect_uri, **extra)

@app.route('/auth/callback/<provider>')
def oauth_callback(provider: str):
    client = oauth.create_client(provider)
    if not client:
        return jsonify({"error": f"{provider} not configured"}), 400
    token = client.authorize_access_token()
    userinfo = token.get('userinfo')
    if not userinfo:
        # OIDC-compliant providers provide userinfo via this call too
        userinfo = client.parse_id_token(token)
    if not userinfo:
        return jsonify({"error": "could not retrieve user info"}), 400

    email = (userinfo.get('email') or '').lower()
    name = userinfo.get('name') or email.split('@')[0]
    picture = userinfo.get('picture') or f"https://api.dicebear.com/8.x/bottts-neutral/svg?seed={email or 'user'}"
    if not email:
        return jsonify({"error": "email not available from provider"}), 400
    uid = _upsert_oauth_user(email, name, picture)
    session_token = _make_token({"uid": uid, "email": email})
    resp = redirect('/')
    resp.set_cookie(
        'auth_token', session_token,
        httponly=True,
        samesite='Lax',
        path='/',
        max_age=60*60*24*7,
        secure=request.is_secure
    )
    return resp

@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    password = data.get('password') or ''
    if not email or not name or not password:
        return jsonify({"error": "name, email, and password are required"}), 400
    pw_hash = _hash_password(password)
    # AI-like avatar with DiceBear using email seed (no API key, zero cost)
    avatar_url = f"https://api.dicebear.com/8.x/bottts-neutral/svg?seed={email}"
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, name, password_hash, avatar_url, created_at) VALUES (?, ?, ?, ?, ?)",
                    (email, name, pw_hash, avatar_url, datetime.utcnow().isoformat()))
        conn.commit()
        uid = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 409
    finally:
        conn.close()
    token = _make_token({"uid": uid, "email": email})
    resp = jsonify({"status": "ok", "user": {"id": uid, "email": email, "name": name, "avatar_url": avatar_url}})
    resp.set_cookie(
        'auth_token', token,
        httponly=True,
        samesite='Lax',
        path='/',
        max_age=60*60*24*7,
        secure=request.is_secure
    )
    return resp

@app.route('/auth/signin', methods=['POST'])
def auth_signin():
    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    pw_hash = _hash_password(password)
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, avatar_url, password_hash FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row or row[4] != pw_hash:
            return jsonify({"error": "invalid credentials"}), 401
        uid = row[0]
        name = row[2]
        avatar_url = row[3]
    finally:
        conn.close()
    token = _make_token({"uid": uid, "email": email})
    resp = jsonify({"status": "ok", "user": {"id": uid, "email": email, "name": name, "avatar_url": avatar_url}})
    resp.set_cookie(
        'auth_token', token,
        httponly=True,
        samesite='Lax',
        path='/',
        max_age=60*60*24*7,
        secure=request.is_secure
    )
    return resp

@app.route('/auth/signout', methods=['POST'])
def auth_signout():
    resp = jsonify({"status": "signed_out"})
    resp.set_cookie('auth_token', '', expires=0)
    return resp

@app.route('/me', methods=['GET'])
def get_me():
    user = _get_auth_user()
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user})

# Serve the main HTML file (require login; otherwise redirect to /auth.html)
@app.route('/')
def index():
    user = _get_auth_user()
    if not user:
        return redirect('/auth.html')
    return redirect('/welcome')

@app.route('/welcome')
def welcome_page():
    user = _get_auth_user()
    if not user:
        return redirect('/auth.html')
    return send_from_directory('static', 'welcome.html')

@app.route('/hub')
def hub_page():
    user = _get_auth_user()
    if not user:
        return redirect('/auth.html')
    return send_from_directory('static', 'care-policy-hub.html')

@app.route('/auth.html')
def serve_auth_page():
    return send_from_directory('static', 'auth.html')

# API endpoint for chat
@app.route('/chat', methods=['POST'])
def chat_handler():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "Query is required."}), 400
    
    logging.info(f"Received query: {query}")
    try:
        response = rag_agent.get_response(query)
        if not response.get("needs_tenant_selection"):
            add_to_history(query, response)
        # Post-process: if user wants only codes, extract from detailed_response heuristically
        ql = (query or '').lower()
        wants_only_codes = any(k in ql for k in ['only code', 'only codes', 'just code', 'just codes', 'codes only'])
        if wants_only_codes:
            def _extract_codes(text: str):
                if not isinstance(text, str):
                    return []
                cands, seen = [], set()
                for m in re.finditer(r"\b[A-Z0-9][A-Z0-9_-]{1,19}\b", text):
                    tok = m.group(0)
                    if any(ch.isdigit() for ch in tok) and tok not in seen:
                        seen.add(tok)
                        cands.append(tok)
                for m in re.finditer(r"\b\d{2,6}\b", text):
                    tok = m.group(0)
                    if tok not in seen:
                        seen.add(tok)
                        cands.append(tok)
                return cands[:200]
            combined = ' '.join([
                str(response.get('summary') or ''),
                str(response.get('detailed_response') or '')
            ])
            codes = _extract_codes(combined)
            if codes:
                response['codes'] = codes
        # Ensure UI sections are always present
        try:
            response.setdefault('summary', 'No summary available.' if response.get('detailed_response') else '')
            response.setdefault('detailed_response', '')
            for k in ('key_points','suggestions','follow_up_questions','code_snippets','sources'):
                v = response.get(k)
                if not isinstance(v, list):
                    response[k] = []
            if 'is_download_intent' not in response:
                response['is_download_intent'] = False
        except Exception:
            pass
        logging.info(f"Sending response: {response}")
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in chat handler: {e}", exc_info=True)
        return jsonify({"summary": "Error", "detailed_response": "I encountered a critical error on the server."}), 500

# API endpoint for feedback
@app.route('/feedback', methods=['POST'])
def feedback_handler():
    data = request.json
    query = data.get('query')
    is_helpful = data.get('is_helpful')
    
    logging.info(f"Feedback received for query '{query}': {'Helpful' if is_helpful else 'Not Helpful'}")
    
    if is_helpful:
        try:
            # Load most recent response for this exact query
            history = load_chat_history()
            # Find last matching query entry
            last = next((item for item in reversed(history) if item.get('query') == query), None)
            if last and isinstance(last.get('response'), dict):
                resp = last['response']
                # Compute max relevance among sources
                sources = resp.get('sources') or []
                max_rel = 0.0
                for s in sources:
                    try:
                        v = float(s.get('relevance', 0) or 0)
                        if v > max_rel:
                            max_rel = v
                    except Exception:
                        continue
                if max_rel >= 0.9 and resp.get('selected_tenant'):
                    rag_agent.cache_response(query, resp)
                    return jsonify({"status": "cached"})
        except Exception as e:
            logging.error(f"Failed to cache helpful response: {e}", exc_info=True)
        return jsonify({"status": "received"}), 200

    if not is_helpful:
        try:
            suggestions = rag_agent.rephrase_query(query)
            return jsonify(suggestions)
        except Exception as e:
            logging.error(f"Failed to rephrase query: {e}", exc_info=True)
            return jsonify({"suggestions": []})
            
    return jsonify({"status": "Feedback received"}), 200

# API endpoint for document/URL upload
@app.route('/upload', methods=['POST'])
def upload_handler():
    if 'new_tenant_id' in request.form and request.form['new_tenant_id']:
        tenant_id = request.form['new_tenant_id']
    elif 'tenant_id' in request.form and request.form['tenant_id']:
        tenant_id = request.form['tenant_id']
    else:
        return jsonify({"error": "Tenant ID is required."}), 400

    all_details = []
    all_errors = []
    
    files = request.files.getlist('files') or []
    actual_files = [f for f in files if getattr(f, 'filename', None)]
    if actual_files:
        _res = rag_agent.ingest_files(tenant_id, actual_files)
        if isinstance(_res, tuple):
            saved, file_errors = _res
        else:
            saved, file_errors = (_res or []), []
        if saved:
            all_details.extend([f"Successfully ingested file: {f}" for f in saved])
            # Optionally upload to S3 as well (still keeping local for indexing)
            if _s3_enabled():
                tenant_dir = os.path.join(rag_agent.documents_dir, tenant_id)
                for fname in saved:
                    local_path = os.path.join(tenant_dir, fname)
                    _s3_upload_file(local_path, tenant_id, fname)
        if file_errors:
            all_errors.extend(file_errors)
        # Augment PDFs with table-extracted numeric rows to improve recall
        try:
            import os as _os
            tenant_dir = _os.path.join(rag_agent.documents_dir, tenant_id)
            try:
                import camelot
                for root, _, fs in _os.walk(tenant_dir):
                    for f in fs:
                        if not f.lower().endswith('.pdf'):
                            continue
                        pdf_path = _os.path.join(root, f)
                        try:
                            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
                        except Exception:
                            try:
                                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
                            except Exception:
                                tables = None
                        if not tables or tables.n == 0:
                            continue
                        out_lines = []
                        for t in tables:
                            try:
                                df = t.df
                                for row in df.values.tolist():
                                    row_text = " | ".join([str(x).strip() for x in row if str(x).strip()])
                                    if any(c.isdigit() for c in row_text):
                                        out_lines.append(row_text)
                            except Exception:
                                continue
                        if out_lines:
                            sidecar = pdf_path + '.tables.txt'
                            with open(sidecar, 'w', encoding='utf-8') as fh:
                                fh.write("\n".join(out_lines))
                # Rebuild index to include sidecars
                try:
                    rag_agent._rebuild_router_engine()
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    url = request.form.get('url')
    if url:
        saved, url_errors = rag_agent.ingest_url(tenant_id, url)
        if saved:
            all_details.extend([f"Successfully ingested content from URL: {url}"])
        if url_errors:
            all_errors.extend(url_errors)
        # Also augment any PDFs now present
        try:
            import os as _os
            tenant_dir = _os.path.join(rag_agent.documents_dir, tenant_id)
            try:
                import camelot
                for root, _, fs in _os.walk(tenant_dir):
                    for f in fs:
                        if not f.lower().endswith('.pdf'):
                            continue
                        pdf_path = _os.path.join(root, f)
                        try:
                            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
                        except Exception:
                            try:
                                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
                            except Exception:
                                tables = None
                        if not tables or tables.n == 0:
                            continue
                        out_lines = []
                        for t in tables:
                            try:
                                df = t.df
                                for row in df.values.tolist():
                                    row_text = " | ".join([str(x).strip() for x in row if str(x).strip()])
                                    if any(c.isdigit() for c in row_text):
                                        out_lines.append(row_text)
                            except Exception:
                                continue
                        if out_lines:
                            sidecar = pdf_path + '.tables.txt'
                            with open(sidecar, 'w', encoding='utf-8') as fh:
                                fh.write("\n".join(out_lines))
                try:
                    rag_agent._rebuild_router_engine()
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    if not all_details and not all_errors:
        return jsonify({"error": "No files or URL provided."}), 400
        
    if all_errors:
        message = "Ingestion completed with some errors."
        status_code = 207
    else:
        message = "Ingestion completed successfully."
        status_code = 200
        
    return jsonify({
        "message": message,
        "details": all_details,
        "errors": all_errors
    }), status_code

# API endpoint to get the list of tenants
@app.route('/tenants', methods=['GET'])
def get_tenants():
    try:
        tenants = [d for d in os.listdir(rag_agent.documents_dir) if os.path.isdir(os.path.join(rag_agent.documents_dir, d))]
        return jsonify({"tenants": tenants})
    except FileNotFoundError:
        return jsonify({"tenants": []})
    except Exception as e:
        logging.error(f"Error getting tenants: {e}", exc_info=True)
        return jsonify({"error": "Could not retrieve tenants."}), 500

# API endpoint for chat history
@app.route('/history', methods=['GET'])
def history_handler():
    user = _get_auth_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    uid = user.get('id')
    history = load_chat_history(uid)
    start_date_str = request.args.get('start')
    end_date_str = request.args.get('end')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str + "T00:00:00")
            end_date = datetime.fromisoformat(end_date_str + "T23:59:59")
            
            filtered_history = [
                item for item in history
                if start_date <= datetime.fromisoformat(item['timestamp']) <= end_date
            ]
            return jsonify(filtered_history)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid date format."}), 400
            
    return jsonify(history)

# API endpoint for analytics
@app.route('/analytics', methods=['GET'])
def analytics_handler():
    user = _get_auth_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    uid = user.get('id')
    history = load_chat_history(uid)
    tenant_counts = Counter()
    for item in history:
        response = item.get("response", {})
        tenant = response.get("selected_tenant")
        if tenant:
            tenant_counts[tenant] += 1
            
    labels = list(tenant_counts.keys())
    data = list(tenant_counts.values())
    
    return jsonify({"labels": labels, "data": data})

# API endpoint for downloading files
@app.route('/download/<tenant_id>/<path:filename>')
def download_file(tenant_id, filename):
    tenant_dir = os.path.join(rag_agent.documents_dir, tenant_id)
    return send_from_directory(tenant_dir, filename, as_attachment=True)


# Inline view endpoint (PDFs open in-browser; others streamed inline if possible)
@app.route('/view/<tenant_id>/<path:filename>')
def view_file(tenant_id, filename):
    tenant_dir = os.path.join(rag_agent.documents_dir, tenant_id)
    file_path = os.path.join(tenant_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    # Let Flask infer mimetype; force inline Content-Disposition
    resp = send_from_directory(tenant_dir, filename, as_attachment=False)
    try:
        resp.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{filename}"
    except Exception:
        pass
    return resp


"""Ensure clients don't cache HTML/JS so UI changes are reflected immediately"""

@app.route('/auth/forgot', methods=['POST'])
def auth_forgot():
    try:
        data = request.get_json(force=True)
        email = (data.get('email') or '').strip().lower()
        captcha_answer = data.get('captcha_answer')
        captcha_expected = data.get('captcha_expected')
        if not email:
            return jsonify({"error": "email is required"}), 400
        try:
            if int(captcha_answer) != int(captcha_expected):
                return jsonify({"error": "Captcha failed"}), 400
        except Exception:
            return jsonify({"error": "Captcha failed"}), 400
        logging.info(f"Password reset requested for {email}")
        return jsonify({"status": "ok", "message": "If the email exists, a reset link has been sent."})
    except Exception as e:
        logging.error(f"Forgot password error: {e}", exc_info=True)
        return jsonify({"error": "Internal error"}), 500

@app.route('/schedules', methods=['GET'])
def list_schedules():
    user = _get_auth_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    items = _load_schedules()
    # Migrate legacy items without id
    changed = False
    for it in items:
        if not it.get('id'):
            it['id'] = str(uuid4())
            changed = True
    if changed:
        _save_schedules(items)
    resp = jsonify({"schedules": items})
    try:
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
    except Exception:
        pass
    return resp

@app.route('/schedules', methods=['POST'])
def add_schedule():
    user = _get_auth_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    tenant = (data.get('tenant') or '').strip()
    url = (data.get('url') or '').strip()
    frequency = (data.get('frequency') or '').strip()  # hourly|daily|weekly|monthly|3months|6months
    start_iso = (data.get('start_time') or '').strip()
    if not tenant or not url or frequency not in ("hourly","daily","weekly","monthly","3months","6months"):
        return jsonify({"error": "tenant, url and valid frequency are required"}), 400
    items = _load_schedules()
    item = {
        "id": str(uuid4()),
        "tenant": tenant,
        "url": url,
        "frequency": frequency,
        "start_time": start_iso,
        "created_at": datetime.utcnow().isoformat()
    }
    items.append(item)
    _save_schedules(items)
    return jsonify({"status": "ok", "schedule": item})

@app.route('/schedules/<sid>', methods=['DELETE'])
def delete_schedule(sid: str):
    user = _get_auth_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    items = _load_schedules()
    new_items = [it for it in items if str(it.get('id')) != str(sid)]
    if len(new_items) == len(items):
        return jsonify({"error": "not found"}), 404
    _save_schedules(new_items)
    return jsonify({"status": "deleted", "id": sid})

@app.route('/schedules/<sid>', methods=['PUT'])
def update_schedule(sid: str):
    user = _get_auth_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    tenant = (data.get('tenant') or '').strip()
    url = (data.get('url') or '').strip()
    frequency = (data.get('frequency') or '').strip()
    start_iso = (data.get('start_time') or '').strip()
    if not tenant or not url or frequency not in ("hourly","daily","weekly","monthly","3months","6months"):
        return jsonify({"error": "tenant, url and valid frequency are required"}), 400
    items = _load_schedules()
    found = False
    for it in items:
        if str(it.get('id')) == str(sid):
            it.update({
                "tenant": tenant,
                "url": url,
                "frequency": frequency,
                "start_time": start_iso,
                "updated_at": datetime.utcnow().isoformat()
            })
            found = True
            break
    if not found:
        return jsonify({"error": "not found"}), 404
    _save_schedules(items)
    return jsonify({"status": "updated", "schedule": it})

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=False)

