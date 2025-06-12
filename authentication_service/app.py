from flask import Flask, request, jsonify, session
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import os
import time
import logging
import json
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from bson import ObjectId
from db_mongodb import get_mongodb_manager, with_write_db, with_read_db

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ualflix-secret-key-change-in-production')

# Configurar métricas Prometheus
try:
    metrics = PrometheusMetrics(app)
except:
    logger.warning("Erro ao configurar métricas Prometheus")

CORS(
    app,
    resources={
        r"/*": {
            "origins": ["http://localhost", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Session-Token"],
            "supports_credentials": True
        }
    },
)

# Armazenamento simples de sessões em memória
active_sessions = {}

def generate_session_token():
    return str(uuid.uuid4())

def get_user_from_token(token):
    """Retorna informações do usuário baseado no token de sessão."""
    session_data = active_sessions.get(token)
    if session_data and session_data['expires'] > datetime.now(timezone.utc):
        return session_data['user']
    return None

@with_write_db
def create_user(db, username, email, password, is_admin=False):
    """Cria um novo usuário no MongoDB"""
    # Verificar se usuário já existe
    existing_user = db.users.find_one({'username': username})
    if existing_user:
        return None, "Username already exists"
    
    # Hash da password
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    # Criar documento do usuário
    user_doc = {
        'username': username,
        'email': email,
        'password': hashed_password,
        'is_admin': is_admin,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    # Inserir no MongoDB
    result = db.users.insert_one(user_doc)
    
    return result.inserted_id, None

@with_read_db
def authenticate_user(db, username, password):
    """Autentica usuário"""
    # Buscar usuário
    user = db.users.find_one({'username': username})
    
    if not user:
        return None, "Invalid username or password"
    
    # Verificar password
    if check_password_hash(user['password'], password):
        return {
            'id': str(user['_id']),
            'username': user['username'],
            'email': user.get('email', ''),
            'is_admin': user.get('is_admin', False)
        }, None
    
    return None, "Invalid username or password"

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"success": False, "error": "Username and password are required"}), 400

        # Se o username for "admin", tornar automaticamente admin
        is_admin = True if username.lower() == "admin" else False
        email = data.get("email", f"{username}@ualflix.com")

        # Criar usuário
        user_id, error = create_user(username, email, password, is_admin)
        
        if error:
            return jsonify({"success": False, "error": error}), 400

        # Criar sessão
        token = generate_session_token()
        active_sessions[token] = {
            'user': {
                'id': str(user_id),
                'username': username,
                'email': email,
                'is_admin': is_admin
            },
            'expires': datetime.now(timezone.utc) + timedelta(hours=24)
        }

        logger.info(f"User {username} registered successfully")
        return jsonify({
            "success": True, 
            "message": "User registered successfully",
            "token": token,
            "user": {
                "id": str(user_id),
                "username": username,
                "email": email,
                "is_admin": is_admin
            }
        }), 201

    except Exception as e:
        logger.error(f"Error in register: {e}")
        return jsonify({"success": False, "error": f"Registration failed: {str(e)}"}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"success": False, "error": "Username and password are required"}), 400

        # Autenticar usuário
        user, error = authenticate_user(username, password)
        
        if error:
            return jsonify({"success": False, "error": error}), 401

        # Criar sessão
        token = generate_session_token()
        active_sessions[token] = {
            'user': user,
            'expires': datetime.now(timezone.utc) + timedelta(hours=24)
        }

        logger.info(f"User {username} logged in successfully")
        return jsonify({
            "success": True, 
            "message": "Login successful",
            "token": token,
            "user": user
        }), 200

    except Exception as e:
        logger.error(f"Error in login: {e}")
        return jsonify({"success": False, "error": f"Login failed: {str(e)}"}), 500

@app.route("/validate", methods=["POST"])
def validate_session():
    """Valida token de sessão e retorna informações do usuário."""
    try:
        data = request.get_json()
        token = data.get("token")
        
        if not token:
            return jsonify({"success": False, "error": "Token required"}), 400
        
        user = get_user_from_token(token)
        if user:
            return jsonify({
                "success": True,
                "user": user
            }), 200
        else:
            return jsonify({"success": False, "error": "Invalid or expired token"}), 401
            
    except Exception as e:
        logger.error(f"Error in validate: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route("/logout", methods=["POST"])
def logout():
    """Remove sessão ativa."""
    try:
        data = request.get_json()
        token = data.get("token")
        
        if token and token in active_sessions:
            del active_sessions[token]
        
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route("/health", methods=["GET"])
def health_check():
    try:
        # Testar conexão MongoDB
        manager = get_mongodb_manager()
        db = manager.get_read_database()
        
        # Ping simples
        db.command('ping')
        
        # Contar usuários
        users_count = db.users.count_documents({})
        
        return jsonify({
            "status": "healthy", 
            "service": "authentication",
            "database": "mongodb",
            "users_count": users_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        return jsonify({
            "status": "unhealthy", 
            "database": "mongodb_failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    """Estatísticas do serviço de autenticação"""
    try:
        manager = get_mongodb_manager()
        
        # Métricas básicas
        metrics = manager.get_database_metrics()
        
        # Estatísticas de sessões
        active_sessions_count = len([s for s in active_sessions.values() 
                                   if s['expires'] > datetime.now(timezone.utc)])
        
        # Status do replica set
        replica_status = manager.check_replica_set_status()
        
        return jsonify({
            "service": "authentication",
            "active_sessions": active_sessions_count,
            "total_sessions_created": len(active_sessions),
            "database_metrics": metrics,
            "replica_set_status": replica_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({"error": str(e)}), 500
@app.route('/metrics')
def metrics():
    """Endpoint para Prometheus coletar métricas"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    logger.info(" Authentication Service com MongoDB iniciado")
    
    # Inicializar MongoDB
    try:
        manager = get_mongodb_manager()
        manager.create_indexes()
        manager.init_collections()
        logger.info("MongoDB inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar MongoDB: {e}")
    
    app.run(host="0.0.0.0", port=8000, debug=True)