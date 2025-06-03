#!/usr/bin/env python3
import pika
import json
import os
import time
import logging
import threading
import subprocess
from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from datetime import datetime
from bson import ObjectId
from db_mongodb import get_mongodb_manager, with_write_db, with_read_db

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métricas Prometheus
VIDEOS_PROCESSED = Counter('videos_processed_total', 'Total videos processed')
VIDEOS_FAILED = Counter('videos_failed_total', 'Total videos failed')
PROCESSING_TIME = Histogram('video_processing_seconds', 'Time spent processing videos')
QUEUE_SIZE = Gauge('video_queue_size', 'Current queue size')

# Diretório onde os vídeos estão armazenados
VIDEO_FOLDER = '/videos'
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# Variáveis de ambiente
QUEUE_HOST = os.environ.get('QUEUE_HOST', 'queue_service')
QUEUE_USER = os.environ.get('QUEUE_USER', 'ualflix')
QUEUE_PASSWORD = os.environ.get('QUEUE_PASSWORD', 'ualflix_password')

app = Flask(__name__)

@with_write_db
def update_video_processing_status(db, video_id, status, duration=None, file_size=None, thumbnail_path=None, error_message=None):
    """Atualiza status do processamento no MongoDB"""
    try:
        update_doc = {
            '$set': {
                'status': status,
                'updated_at': datetime.utcnow()
            }
        }
        
        if duration is not None:
            update_doc['$set']['duration'] = duration
        
        if file_size is not None:
            update_doc['$set']['file_size'] = file_size
        
        if thumbnail_path is not None:
            update_doc['$set']['thumbnail_path'] = thumbnail_path
        
        if error_message is not None:
            update_doc['$set']['error_message'] = error_message
        
        result = db.videos.update_one(
            {'_id': ObjectId(video_id)},
            update_doc
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status do vídeo {video_id}: {e}")
        return False

@with_read_db
def get_video_info_from_db(db, video_id):
    """Obtém informações do vídeo do MongoDB"""
    try:
        video = db.videos.find_one({'_id': ObjectId(video_id)})
        if video:
            return {
                'id': str(video['_id']),
                'title': video.get('title'),
                'filename': video.get('filename'),
                'filepath': video.get('file_path', os.path.join(VIDEO_FOLDER, video.get('filename', ''))),
                'user_id': str(video.get('user_id', ''))
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar vídeo {video_id} no MongoDB: {e}")
        return None

@app.route('/health')
def health():
    try:
        # Testar MongoDB
        manager = get_mongodb_manager()
        db = manager.get_read_database()
        db.command('ping')
        
        # Contar vídeos processados
        videos_processed = db.videos.count_documents({'status': 'active'})
        videos_processing = db.videos.count_documents({'status': 'processing'})
        
        return jsonify({
            "status": "healthy", 
            "service": "video_processor",
            "database": "mongodb",
            "videos_processed": videos_processed,
            "videos_processing": videos_processing
        })
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/metrics')
def metrics():
    return jsonify({
        "videos_processed": VIDEOS_PROCESSED._value._value,
        "videos_failed": VIDEOS_FAILED._value._value,
        "queue_size": QUEUE_SIZE._value._value
    })

@app.route('/stats')
def get_stats():
    """Estatísticas do processador com MongoDB"""
    try:
        manager = get_mongodb_manager()
        db = manager.get_read_database()
        
        # Estatísticas de vídeos
        total_videos = db.videos.count_documents({})
        processing_videos = db.videos.count_documents({'status': 'processing'})
        active_videos = db.videos.count_documents({'status': 'active'})
        error_videos = db.videos.count_documents({'status': 'error'})
        
        # Estatísticas de processamento por usuário
        pipeline = [
            {'$group': {
                '_id': '$user_id',
                'video_count': {'$sum': 1},
                'total_duration': {'$sum': '$duration'},
                'avg_duration': {'$avg': '$duration'}
            }},
            {'$sort': {'video_count': -1}},
            {'$limit': 10}
        ]
        
        user_stats = list(db.videos.aggregate(pipeline))
        
        return jsonify({
            "service": "video_processor",
            "database": "mongodb",
            "video_statistics": {
                "total": total_videos,
                "processing": processing_videos,
                "active": active_videos,
                "error": error_videos
            },
            "top_users": [
                {
                    "user_id": str(stat['_id']),
                    "video_count": stat['video_count'],
                    "total_duration": stat.get('total_duration', 0),
                    "avg_duration": stat.get('avg_duration', 0)
                } for stat in user_stats
            ],
            "metrics": {
                "videos_processed": VIDEOS_PROCESSED._value._value,
                "videos_failed": VIDEOS_FAILED._value._value,
                "current_queue_size": QUEUE_SIZE._value._value
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({"error": str(e)}), 500

def start_metrics_server():
    """Inicia o servidor HTTP para métricas Prometheus."""
    try:
        start_http_server(9102)
        logger.info("Servidor de métricas Prometheus iniciado na porta 9102")
    except OSError as e:
        if e.errno == 98:
            logger.warning("Porta 9102 já em uso, ignorando erro e continuando...")
        else:
            raise

def start_flask_server():
    """Inicia o servidor Flask para health checks."""
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=8000)
    except OSError as e:
        if e.errno == 98:
            logger.warning("Porta 8000 já em uso, ignorando erro e continuando...")
        else:
            raise

def connect_to_rabbitmq():
    """Conecta ao RabbitMQ e retorna a conexão e o canal."""
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
        
        # Declara a fila para processamento de vídeos
        channel.queue_declare(queue='video_processing', durable=True)
        
        # Configura QoS para não sobrecarregar o worker
        channel.basic_qos(prefetch_count=1)
        
        return connection, channel
    except Exception as e:
        logger.error(f"Erro ao conectar com RabbitMQ: {e}")
        time.sleep(5)
        return None, None

def get_video_info(filepath):
    """Obtém informações do vídeo usando ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Erro ao obter informações do vídeo: {e}")
    return None

def create_thumbnail(filepath, output_path):
    """Cria uma thumbnail do vídeo."""
    try:
        cmd = [
            'ffmpeg', '-i', filepath, '-ss', '00:00:01.000', '-vframes', '1',
            '-vf', 'scale=320:240', '-y', output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Erro ao criar thumbnail: {e}")
        return False

def process_video(video_data):
    """Processa o vídeo - análise, thumbnail, validação, etc."""
    video_id = video_data.get('id')
    filename = video_data.get('filename')
    filepath = video_data.get('filepath', os.path.join(VIDEO_FOLDER, filename))
    
    logger.info(f"Iniciando processamento do vídeo: {filename} (ID: {video_id})")
    
    start_time = time.time()
    processing_results = {
        'video_id': video_id,
        'filename': filename,
        'success': False,
        'info': None,
        'thumbnail': False,
        'duration': 0,
        'file_size': 0,
        'errors': []
    }
    
    try:
        # Atualizar status para processando
        update_video_processing_status(video_id, 'processing')
        
        # Verificar se o arquivo existe
        if not os.path.exists(filepath):
            raise Exception(f"Arquivo não encontrado: {filepath}")
        
        # Obter tamanho do arquivo
        file_size = os.path.getsize(filepath)
        processing_results['file_size'] = file_size
        
        # Obter informações do vídeo
        video_info = get_video_info(filepath)
        if video_info:
            processing_results['info'] = video_info
            
            # Extrair duração
            try:
                duration = float(video_info['format']['duration'])
                processing_results['duration'] = int(duration)
                logger.info(f"Duração do vídeo: {duration} segundos")
            except:
                pass
        
        # Criar thumbnail
        thumbnail_filename = f"thumb_{filename}.jpg"
        thumbnail_path = os.path.join(VIDEO_FOLDER, thumbnail_filename)
        
        if create_thumbnail(filepath, thumbnail_path):
            processing_results['thumbnail'] = True
            logger.info(f"Thumbnail criada: {thumbnail_filename}")
        
        logger.info(f"Tamanho do arquivo: {file_size / (1024*1024):.2f} MB")
        
        # Simular processamento adicional
        time.sleep(2)
        
        # Atualizar MongoDB com resultados do processamento
        update_success = update_video_processing_status(
            video_id=video_id,
            status='active',
            duration=processing_results['duration'],
            file_size=file_size,
            thumbnail_path=thumbnail_filename if processing_results['thumbnail'] else None
        )
        
        if update_success:
            processing_results['success'] = True
            logger.info(f"✅ Vídeo processado com sucesso: {filename}")
        else:
            raise Exception("Falha ao atualizar status no MongoDB")
        
    except Exception as e:
        error_msg = str(e)
        processing_results['errors'].append(error_msg)
        logger.error(f"❌ Erro ao processar vídeo {filename}: {error_msg}")
        
        # Atualizar status para erro no MongoDB
        update_video_processing_status(
            video_id=video_id,
            status='error',
            error_message=error_msg
        )
        
        VIDEOS_FAILED.inc()
    
    finally:
        # Registrar tempo de processamento
        processing_time = time.time() - start_time
        PROCESSING_TIME.observe(processing_time)
        
        if processing_results['success']:
            VIDEOS_PROCESSED.inc()
        
        logger.info(f"Processamento concluído em {processing_time:.2f} segundos")
    
    return processing_results

def callback(ch, method, properties, body):
    """Callback executado quando uma mensagem é recebida da fila."""
    try:
        video_data = json.loads(body)
        logger.info(f"Recebido para processamento: {video_data.get('filename')} (ID: {video_data.get('id')})")
        
        # Atualizar métrica da fila
        queue_info = ch.queue_declare(queue='video_processing', passive=True)
        QUEUE_SIZE.set(queue_info.method.message_count)
        
        # Buscar informações atualizadas do vídeo no MongoDB
        video_id = video_data.get('id')
        if video_id:
            db_video_info = get_video_info_from_db(video_id)
            if db_video_info:
                # Atualizar dados com informações do MongoDB
                video_data.update(db_video_info)
        
        # Processar o vídeo
        results = process_video(video_data)
        
        # Log dos resultados
        if results['success']:
            logger.info(f"✅ Processamento bem-sucedido: {results['filename']}")
        else:
            logger.error(f"❌ Falha no processamento: {results['filename']} - Erros: {results['errors']}")
        
        # Confirmar que a mensagem foi processada
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Erro no callback: {e}")
        # Rejeitar a mensagem e não reprocessar
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    """Função principal do processador de vídeos."""
    logger.info("🎬 Video Processor com MongoDB iniciado...")
    
    # Testar MongoDB na inicialização
    try:
        manager = get_mongodb_manager()
        db = manager.get_read_database()
        db.command('ping')
        logger.info("✅ MongoDB conectado com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao MongoDB: {e}")
    
    # Inicia servidor de métricas Prometheus em uma thread separada
    metrics_thread = threading.Thread(target=start_metrics_server)
    metrics_thread.daemon = True
    metrics_thread.start()
    
    # Inicia servidor Flask para health checks em uma thread separada
    flask_thread = threading.Thread(target=start_flask_server)
    flask_thread.daemon = True
    flask_thread.start()
    
    logger.info("Servidores de métricas e health check iniciados")
    
    while True:
        try:
            connection, channel = connect_to_rabbitmq()
            
            if channel:
                logger.info("🐰 Conectado ao RabbitMQ, aguardando mensagens...")
                
                # Configura o consumo da fila
                channel.basic_consume(
                    queue='video_processing', 
                    on_message_callback=callback
                )
                
                # Inicia o consumo de mensagens
                channel.start_consuming()
            else:
                # Se falhar na conexão, aguarda e tenta novamente
                logger.error("❌ Falha na conexão com RabbitMQ, tentando novamente...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("🛑 Processador de vídeos interrompido")
            if 'connection' in locals() and connection and connection.is_open:
                connection.close()
            break
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()