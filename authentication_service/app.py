from flask import Flask, request, jsonify, session
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import psycopg2
import os
import time
import logging
import json
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

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

# Configuração da base de dados - SIMPLIFICADA
DB_CONFIG = {
    'host': os.environ.get('DB_MASTER_HOST', 'ualflix_db_master'),
    'port': int(os.environ.get('DB_MASTER_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'ualflix'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
}

def get_db_connection():
    """Obter conexão simples com a base de dados"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar à BD: {e}")
        raise

def generate_session_token():
    return str(uuid.uuid4())

def get_user_from_token(token):
    """Retorna informações do usuário baseado no token de sessão."""
    session_data = active_sessions.get(token)
    if session_data and session_data['expires'] > datetime.now():
        return session_data['user']
    return None

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

        # Hash the password - CORRIGIDO para ser mais simples
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if username already exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"success": False, "error": "Username already exists"}), 400

        # Insert new user - CORRIGIDO para usar campo email
        cur.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s) RETURNING id",
            (username, f"{username}@ualflix.com", hashed_password, is_admin),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # Criar sessão
        token = generate_session_token()
        active_sessions[token] = {
            'user': {
                'id': user_id,
                'username': username,
                'is_admin': is_admin
            },
            'expires': datetime.now() + timedelta(hours=24)
        }

        logger.info(f"User {username} registered successfully")
        return jsonify({
            "success": True, 
            "message": "User registered successfully",
            "token": token,
            "user": {
                "id": user_id,
                "username": username,
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

        conn = get_db_connection()
        cur = conn.cursor()

        # Get user from database
        cur.execute("SELECT id, password, is_admin FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return jsonify({"success": False, "error": "Invalid username or password"}), 401

        # Check password
        if check_password_hash(user[1], password):
            # Criar sessão
            token = generate_session_token()
            active_sessions[token] = {
                'user': {
                    'id': user[0],
                    'username': username,
                    'is_admin': user[2]
                },
                'expires': datetime.now() + timedelta(hours=24)
            }

            logger.info(f"User {username} logged in successfully")
            return jsonify({
                "success": True, 
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user[0],
                    "username": username,
                    "is_admin": user[2]
                }
            }), 200
        else:
            return jsonify({"success": False, "error": "Invalid username or password"}), 401

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
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"status": "healthy", "db_connection": "ok"}), 200
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        return jsonify({"status": "unhealthy", "db_connection": "failed"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)