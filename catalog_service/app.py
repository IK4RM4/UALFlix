from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_db_connection
from prometheus_flask_exporter import PrometheusMetrics
import os
import time
import logging
import json
import pika
import requests


# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB

# Configurar métricas Prometheus
metrics = PrometheusMetrics(app)

# Configuração do ambiente
VIDEO_FOLDER = '/videos'
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# Configuração RabbitMQ
QUEUE_HOST = os.environ.get('QUEUE_HOST', 'queue_service')
QUEUE_USER = os.environ.get('QUEUE_USER', 'ualflix')
QUEUE_PASSWORD = os.environ.get('QUEUE_PASSWORD', 'ualflix_password')

# URL do serviço de autenticação
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://authentication_service:8000')

def get_rabbitmq_connection():
    """Conecta ao RabbitMQ."""
    try:
        credentials = pika.PlainCredentials(QUEUE_USER, QUEUE_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=QUEUE_HOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declarar a fila
        channel.queue_declare(queue='video_processing', durable=True)
        
        return connection, channel
    except Exception as e:
        logger.error(f"Erro ao conectar ao RabbitMQ: {e}")
        return None, None

def send_to_processing_queue(video_data):
    """Envia dados do vídeo para a fila de processamento."""
    try:
        connection, channel = get_rabbitmq_connection()
        if channel:
            message = json.dumps(video_data)
            channel.basic_publish(
                exchange='',
                routing_key='video_processing',
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Torna a mensagem persistente
            )
            connection.close()
            logger.info(f"Vídeo enviado para processamento: {video_data['filename']}")
            return True
    except Exception as e:
        logger.error(f"Erro ao enviar para fila de processamento: {e}")
    return False

def validate_user_token(token):
    """Valida token do usuário com o serviço de autenticação."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/validate",
            json={"token": token},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get('user')
    except Exception as e:
        logger.error(f"Erro ao validar token: {e}")
    return None

@app.route('/health', methods=['GET'])
def health_check():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy", "db_connection": "ok"}), 200
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        return jsonify({"status": "unhealthy", "db_connection": "failed"}), 500

@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        
        content_length = request.content_length
        if content_length:
            logger.info(f"Recebendo upload de {content_length / (1024*1024):.2f} MB")
        # Validar token do usuário
        token = request.headers.get('X-Session-Token')
        if not token:
            return jsonify({"error": "Token de sessão obrigatório"}), 401
        
        user = validate_user_token(token)
        if not user:
            return jsonify({"error": "Token inválido ou expirado"}), 401

        title = request.form.get('title', '')
        description = request.form.get('description', '')
        file = request.files['file']

        if file and file.filename:
            timestamp = str(int(time.time()))
            safe_filename = timestamp + "_" + file.filename
            filepath = os.path.join(VIDEO_FOLDER, safe_filename)
            file.save(filepath)

            # Gerar a URL (caminho para acessar o vídeo depois)
            url = f"/stream/{safe_filename}"

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO videos (title, description, filename, url, user_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (title, description, safe_filename, url, user['id'])
            )
            video_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()

            # Enviar para fila de processamento
            video_data = {
                'id': video_id,
                'filename': safe_filename,
                'title': title,
                'user_id': user['id'],
                'filepath': filepath
            }
            send_to_processing_queue(video_data)

            return jsonify({
                "message": "Video uploaded successfully!",
                "filename": safe_filename,
                "url": url,
                "video_id": video_id
            }), 200
        else:
            return jsonify({"error": "No file uploaded"}), 400
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/videos', methods=['GET'])
def list_videos():
    try:
        # Opcional: filtrar por usuário se token fornecido
        token = request.headers.get('X-Session-Token')
        user_filter = request.args.get('user_only', 'false').lower() == 'true'
        
        user = None
        if token:
            user = validate_user_token(token)

        conn = get_db_connection()
        cur = conn.cursor()
        
        if user_filter and user:
            # Mostrar apenas vídeos do usuário
            cur.execute("""
                SELECT v.id, v.title, v.description, v.filename, v.url, v.upload_date, u.username 
                FROM videos v 
                LEFT JOIN users u ON v.user_id = u.id 
                WHERE v.user_id = %s
                ORDER BY v.upload_date DESC
            """, (user['id'],))
        else:
            # Mostrar todos os vídeos
            cur.execute("""
                SELECT v.id, v.title, v.description, v.filename, v.url, v.upload_date, u.username 
                FROM videos v 
                LEFT JOIN users u ON v.user_id = u.id 
                ORDER BY v.upload_date DESC
            """)
        
        videos = cur.fetchall()
        cur.close()
        conn.close()

        videos_list = []
        for video in videos:
            video_data = {
                'id': video[0],
                'title': video[1],
                'description': video[2],
                'filename': video[3],
                'url': video[4],
                'upload_date': video[5].isoformat() if video[5] else None,
                'uploaded_by': video[6] or 'Unknown'
            }
            videos_list.append(video_data)
        
        return jsonify(videos_list)
    except Exception as e:
        logger.error(f"Erro ao listar vídeos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/videos/<int:video_id>', methods=['GET'])
def get_video(video_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, v.title, v.description, v.filename, v.url, v.upload_date, u.username 
            FROM videos v 
            LEFT JOIN users u ON v.user_id = u.id 
            WHERE v.id = %s
        """, (video_id,))
        video = cur.fetchone()
        cur.close()
        conn.close()

        if video:
            video_data = {
                'id': video[0],
                'title': video[1],
                'description': video[2],
                'filename': video[3],
                'url': video[4],
                'upload_date': video[5].isoformat() if video[5] else None,
                'uploaded_by': video[6] or 'Unknown'
            }
            return jsonify(video_data)
        else:
            return jsonify({"error": "Video not found"}), 404
    except Exception as e:
        logger.error(f"Erro ao buscar vídeo {video_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/my-videos', methods=['GET'])
def get_my_videos():
    """Endpoint para buscar apenas vídeos do usuário autenticado."""
    try:
        token = request.headers.get('X-Session-Token')
        if not token:
            return jsonify({"error": "Token de sessão obrigatório"}), 401
        
        user = validate_user_token(token)
        if not user:
            return jsonify({"error": "Token inválido ou expirado"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, v.title, v.description, v.filename, v.url, v.upload_date, u.username 
            FROM videos v 
            LEFT JOIN users u ON v.user_id = u.id 
            WHERE v.user_id = %s
            ORDER BY v.upload_date DESC
        """, (user['id'],))
        
        videos = cur.fetchall()
        cur.close()
        conn.close()

        videos_list = []
        for video in videos:
            video_data = {
                'id': video[0],
                'title': video[1],
                'description': video[2],
                'filename': video[3],
                'url': video[4],
                'upload_date': video[5].isoformat() if video[5] else None,
                'uploaded_by': video[6] or 'Unknown'
            }
            videos_list.append(video_data)
        
        return jsonify(videos_list)
    except Exception as e:
        logger.error(f"Erro ao buscar vídeos do usuário: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)