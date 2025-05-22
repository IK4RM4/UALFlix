from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_db_connection
import os
import time
import logging
import json
import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/*": {
            "origins": ["http://localhost", "http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)

@app.route("/register", methods=["POST"])
def register():
    try:
        # CORREÇÃO: usar request.get_json() em vez de request.get_json
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify(
                    {"success": False, "error": "Username and password are required"}
                ),
                400,
            )

         # NOVA LÓGICA: Se o username for "admin", tornar automaticamente admin
        is_admin = True if username.lower() == "admin" else False

        # Hash the password
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if username already exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"success": False, "error": "Username already exists"}), 400

        # Insert new user with admin logic
        cur.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
            (username, hashed_password, is_admin),
        )
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"User {username} registered successfully")
        return (
            jsonify({"success": True, "message": "User registered successfully"}),
            201,
        )

    except Exception as e:
        logger.error(f"Error in register: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify(
                    {"success": False, "error": "Username and password are required"}
                ),
                400,
            )

        conn = get_db_connection()
        cur = conn.cursor()

        # Get user from database
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return (
                jsonify({"success": False, "error": "Invalid username or password"}),
                401,
            )

        # Check password
        if check_password_hash(user[1], password):
            logger.info(f"User {username} logged in successfully")
            return jsonify({"success": True, "message": "Login successful"}), 200
        else:
            return (
                jsonify({"success": False, "error": "Invalid username or password"}),
                401,
            )

    except Exception as e:
        logger.error(f"Error in login: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy", "db_connection": "ok"}), 200
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        return jsonify({"status": "unhealthy", "db_connection": "failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)