"""
Modern Flask app using new modular RAG structure.
Uses agents/rag_agent.py with proper router query engine integration.
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
from werkzeug.utils import secure_filename

# Import from NEW modular structure
from agents import get_rag_agent, initialize_agent
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize RAG agent (uses new modular structure)
logger.info("Initializing ModernRAGAgent with new structure...")
agent = get_rag_agent()
logger.info("✅ Agent initialized successfully")

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'csv', 'json', 'md'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve main page."""
    return send_from_directory('static', 'index.html')


@app.route('/care-policy-hub')
def care_policy_hub():
    """Serve care policy hub page."""
    return send_from_directory('static', 'care-policy-hub.html')


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "agent": "ModernRAGAgent",
        "structure": "modular",
        "router_enabled": agent.router_query_engine is not None,
        "tenants": agent.list_tenants(),
        "config": {
            "llm_provider": settings.LLM_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "storage_backend": settings.STORAGE_BACKEND,
            "vector_store": settings.VECTOR_STORE
        }
    }), 200


@app.route('/stats', methods=['GET'])
def stats():
    """Get system statistics."""
    try:
        stats = agent.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """
    Chat endpoint using router query engine.
    Routes queries to correct tenant automatically.
    """
    try:
        data = request.json
        query = data.get('query')
        tenant_id = data.get('tenant_id')  # Optional
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        logger.info(f"Processing query: {query[:100]}...")
        if tenant_id:
            logger.info(f"  Tenant: {tenant_id}")
        else:
            logger.info("  Tenant: auto-detect via router")
        
        # Query agent (router handles tenant routing automatically!)
        response = agent.query(query, tenant_id)
        
        # Log response
        logger.info(f"Response generated: {len(response.get('detailed_response', ''))} chars")
        logger.info(f"  Sources: {len(response.get('sources', []))}")
        
        # Check if sources show URLs (not content)
        sources = response.get('sources', [])
        for source in sources:
            source_val = source.get('source', '')
            if len(source_val) > 500:
                logger.warning(f"⚠️  Source seems to be content, not URL: {source_val[:100]}...")
            else:
                logger.info(f"  ✅ Source: {source_val}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "summary": "Error",
            "detailed_response": f"An error occurred: {str(e)}",
            "sources": []
        }), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload and ingest file with automatic metadata tracking.
    """
    try:
        # Check file
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        tenant_id = request.form.get('tenant_id')
        
        if not tenant_id:
            return jsonify({"error": "tenant_id is required"}), 400
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": f"File type not allowed. Allowed: {ALLOWED_EXTENSIONS}"}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        logger.info(f"File uploaded: {filename} for tenant: {tenant_id}")
        
        # Ingest file (metadata automatically tracked!)
        result = agent.ingest_file(file_path, tenant_id)
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if result['success']:
            logger.info(f"✅ File ingested: {result}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Ingestion failed: {result}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/ingest-url', methods=['POST'])
def ingest_url():
    """
    Ingest URL with automatic metadata tracking.
    URLs are automatically tracked for citations!
    """
    try:
        data = request.json
        url = data.get('url')
        tenant_id = data.get('tenant_id')
        
        if not url or not tenant_id:
            return jsonify({"error": "url and tenant_id are required"}), 400
        
        logger.info(f"Ingesting URL: {url} for tenant: {tenant_id}")
        
        # Ingest URL (metadata automatically tracked!)
        result = agent.ingest_url(url, tenant_id)
        
        if result['success']:
            logger.info(f"✅ URL ingested: {result}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ URL ingestion failed: {result}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"URL ingest error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/tenants', methods=['GET'])
def list_tenants():
    """List all available tenants."""
    try:
        tenants = agent.list_tenants()
        return jsonify({
            "tenants": tenants,
            "count": len(tenants)
        }), 200
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/router-info', methods=['GET'])
def router_info():
    """Get router query engine information."""
    try:
        return jsonify({
            "router_enabled": agent.router_query_engine is not None,
            "tenants": agent.list_tenants(),
            "tools_count": len(agent.tools),
            "description": "Router automatically routes queries to correct tenant based on query content"
        }), 200
    except Exception as e:
        logger.error(f"Error getting router info: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal error: {e}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Starting Flask app with NEW MODULAR STRUCTURE")
    logger.info("=" * 60)
    logger.info(f"Agent: ModernRAGAgent")
    logger.info(f"Router: {'✅ Enabled' if agent.router_query_engine else '❌ No tenants yet'}")
    logger.info(f"Tenants: {agent.list_tenants()}")
    logger.info(f"LLM: {settings.LLM_PROVIDER}/{settings.LLM_MODEL}")
    logger.info(f"Embeddings: {settings.EMBEDDING_PROVIDER}/{settings.EMBEDDING_MODEL}")
    logger.info(f"Storage: {settings.STORAGE_BACKEND}")
    logger.info(f"Vector Store: {settings.VECTOR_STORE}")
    logger.info("=" * 60)
    
    # Run app
    app.run(
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        debug=settings.DEBUG
    )
