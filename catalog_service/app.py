from flask import Flask, request, jsonify
from flask_cors import CORS
from db_mongodb import get_mongodb_manager, with_write_db, with_read_db
from prometheus_flask_exporter import PrometheusMetrics
import os
import time
import logging
import json
import pika
import requests
from datetime import datetime
from bson import ObjectId

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
            message = json.dumps(video_data, default=str)  # default=str para ObjectId
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

@with_write_db
def create_video_record(db, title, description, filename, url, user_id):
    """Cria registro do vídeo no MongoDB"""
    video_doc = {
        'title': title,
        'description': description,
        'filename': filename,
        'url': url,
        'user_id': user_id,
        'upload_date': datetime.utcnow(),
        'view_count': 0,
        'status': 'processing',
        'duration': 0,
        'file_size': 0,
        'thumbnail_path': None
    }
    
    result = db.videos.insert_one(video_doc)
    return result.inserted_id

@with_read_db
def get_videos_list(db, user_id=None, limit=None):
    """Obtém lista de vídeos"""
    filter_doc = {}
    if user_id:
        filter_doc['user_id'] = user_id
    
    # Pipeline de agregação para incluir informações do usuário
    pipeline = [
        {'$match': filter_doc},
        {
            '$lookup': {
                'from': 'users',
                'localField': 'user_id',
                'foreignField': '_id',
                'as': 'user_info'
            }
        },
        {
            '$addFields': {
                'uploaded_by': {
                    '$ifNull': [
                        {'$arrayElemAt': ['$user_info.username', 0]},
                        'Unknown'
                    ]
                }
            }
        },
        {'$project': {'user_info': 0}},  # Remove campo temporário
        {'$sort': {'upload_date': -1}}
    ]
    
    if limit:
        pipeline.append({'$limit': limit})
    
    videos = list(db.videos.aggregate(pipeline))
    
    # Converter ObjectId para string
    for video in videos:
        video['_id'] = str(video['_id'])
        if video.get('user_id'):
            video['user_id'] = str(video['user_id'])
    
    return videos

@with_read_db
def get_video_by_id(db, video_id):
    """Obtém vídeo por ID"""
    try:
        # Pipeline de agregação para incluir informações do usuário
        pipeline = [
            {'$match': {'_id': ObjectId(video_id)}},
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user_info'
                }
            },
            {
                '$addFields': {
                    'uploaded_by': {
                        '$ifNull': [
                            {'$arrayElemAt': ['$user_info.username', 0]},
                            'Unknown'
                        ]
                    }
                }
            },
            {'$project': {'user_info': 0}}
        ]
        
        result = list(db.videos.aggregate(pipeline))
        
        if result:
            video = result[0]
            video['_id'] = str(video['_id'])
            if video.get('user_id'):
                video['user_id'] = str(video['user_id'])
            return video
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao buscar vídeo {video_id}: {e}")
        return None

@with_write_db
def increment_view_count(db, video_id, user_id=None):
    """Incrementa contador de visualizações"""
    try:
        # Atualizar contador de visualizações
        db.videos.update_one(
            {'_id': ObjectId(video_id)},
            {'$inc': {'view_count': 1}}
        )
        
        # Registrar visualização se usuário logado
        if user_id:
            view_doc = {
                'video_id': ObjectId(video_id),
                'user_id': ObjectId(user_id) if user_id != 'anonymous' else None,
                'view_date': datetime.utcnow(),
                'watch_duration': 0
            }
            db.video_views.insert_one(view_doc)
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao incrementar visualização: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    try:
        manager = get_mongodb_manager()
        db = manager.get_read_database()
        
        # Ping MongoDB
        db.command('ping')
        
        # Contar vídeos
        videos_count = db.videos.count_documents({})
        
        return jsonify({
            "status": "healthy", 
            "service": "catalog",
            "database": "mongodb",
            "videos_count": videos_count
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {e}")
        return jsonify({
            "status": "unhealthy", 
            "database": "mongodb_failed",
            "error": str(e)
        }), 500

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

            # Gerar a URL
            url = f"/stream/{safe_filename}"

            # Criar registro no MongoDB
            video_id = create_video_record(
                title=title,
                description=description,
                filename=safe_filename,
                url=url,
                user_id=ObjectId(user['id'])
            )

            # Enviar para fila de processamento
            video_data = {
                'id': str(video_id),
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
                "video_id": str(video_id)
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
        user_id = None
        
        if token:
            user = validate_user_token(token)
            if user and user_filter:
                user_id = ObjectId(user['id'])

        videos = get_videos_list(user_id=user_id)
        
        # Converter para formato esperado pelo frontend
        videos_list = []
        for video in videos:
            video_data = {
                'id': video['_id'],
                'title': video['title'],
                'description': video['description'],
                'filename': video['filename'],
                'url': video['url'],
                'upload_date': video['upload_date'].isoformat() if video.get('upload_date') else None,
                'uploaded_by': video.get('uploaded_by', 'Unknown'),
                'view_count': video.get('view_count', 0),
                'status': video.get('status', 'active'),
                'duration': video.get('duration', 0)
            }
            videos_list.append(video_data)
        
        return jsonify(videos_list)
        
    except Exception as e:
        logger.error(f"Erro ao listar vídeos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/videos/<video_id>', methods=['GET'])
def get_video(video_id):
    try:
        video = get_video_by_id(video_id)
        
        if video:
            # Incrementar contador de visualizações
            token = request.headers.get('X-Session-Token')
            user_id = None
            
            if token:
                user = validate_user_token(token)
                if user:
                    user_id = user['id']
            
            increment_view_count(video_id, user_id)
            
            video_data = {
                'id': video['_id'],
                'title': video['title'],
                'description': video['description'],
                'filename': video['filename'],
                'url': video['url'],
                'upload_date': video['upload_date'].isoformat() if video.get('upload_date') else None,
                'uploaded_by': video.get('uploaded_by', 'Unknown'),
                'view_count': video.get('view_count', 0),
                'status': video.get('status', 'active'),
                'duration': video.get('duration', 0)
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

        videos = get_videos_list(user_id=ObjectId(user['id']))
        
        videos_list = []
        for video in videos:
            video_data = {
                'id': video['_id'],
                'title': video['title'],
                'description': video['description'],
                'filename': video['filename'],
                'url': video['url'],
                'upload_date': video['upload_date'].isoformat() if video.get('upload_date') else None,
                'uploaded_by': video.get('uploaded_by', 'Unknown'),
                'view_count': video.get('view_count', 0),
                'status': video.get('status', 'active'),
                'duration': video.get('duration', 0)
            }
            videos_list.append(video_data)
        
        return jsonify(videos_list)
        
    except Exception as e:
        logger.error(f"Erro ao buscar vídeos do usuário: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_catalog_stats():
    """Estatísticas do catálogo"""
    try:
        manager = get_mongodb_manager()
        
        # Métricas da base de dados
        db_metrics = manager.get_database_metrics()
        
        # Status do replica set
        replica_status = manager.check_replica_set_status()
        
        # Teste de replicação
        replication_test = manager.test_replication_lag()
        
        return jsonify({
            "service": "catalog",
            "database_metrics": db_metrics,
            "replica_set_status": replica_status,
            "replication_test": replication_test,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("🎬 Catalog Service com MongoDB iniciado")
    
    # Inicializar MongoDB
    try:
        manager = get_mongodb_manager()
        manager.create_indexes()
        logger.info("✅ MongoDB inicializado")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar MongoDB: {e}")
    
    app.run(host="0.0.0.0", port=8000, debug=True)