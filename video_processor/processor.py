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

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "video_processor"})

@app.route('/metrics')
def metrics():
    return jsonify({
        "videos_processed": VIDEOS_PROCESSED._value._value,
        "videos_failed": VIDEOS_FAILED._value._value,
        "queue_size": QUEUE_SIZE._value._value
    })

def start_metrics_server():
    """Inicia o servidor HTTP para métricas Prometheus."""
    try:
        start_http_server(9102)
        logger.info("Servidor de métricas Prometheus iniciado na porta 9102")
    except OSError as e:
        if e.errno == 98:  # Endereço já em uso
            logger.warning("Porta 9102 já em uso, ignorando erro e continuando...")
        else:
            raise

def start_flask_server():
    """Inicia o servidor Flask para health checks."""
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=8000)
    except OSError as e:
        if e.errno == 98:  # Endereço já em uso
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
        time.sleep(5)  # Espera antes de tentar novamente
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
    filename = video_data.get('filename')
    filepath = video_data.get('filepath', os.path.join(VIDEO_FOLDER, filename))
    
    logger.info(f"Iniciando processamento do vídeo: {filename}")
    
    start_time = time.time()
    processing_results = {
        'filename': filename,
        'success': False,
        'info': None,
        'thumbnail': False,
        'duration': 0,
        'errors': []
    }
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(filepath):
            raise Exception(f"Arquivo não encontrado: {filepath}")
        
        # Obter informações do vídeo
        video_info = get_video_info(filepath)
        if video_info:
            processing_results['info'] = video_info
            
            # Extrair duração
            try:
                duration = float(video_info['format']['duration'])
                processing_results['duration'] = duration
                logger.info(f"Duração do vídeo: {duration} segundos")
            except:
                pass
        
        # Criar thumbnail
        thumbnail_path = os.path.join(VIDEO_FOLDER, f"thumb_{filename}.jpg")
        if create_thumbnail(filepath, thumbnail_path):
            processing_results['thumbnail'] = True
            logger.info(f"Thumbnail criada: thumb_{filename}.jpg")
        
        # Validar formato e qualidade
        file_size = os.path.getsize(filepath)
        logger.info(f"Tamanho do arquivo: {file_size / (1024*1024):.2f} MB")
        
        # Simular processamento adicional
        time.sleep(2)
        
        processing_results['success'] = True
        logger.info(f"Vídeo processado com sucesso: {filename}")
        
    except Exception as e:
        error_msg = str(e)
        processing_results['errors'].append(error_msg)
        logger.error(f"Erro ao processar vídeo {filename}: {error_msg}")
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
        logger.info(f"Recebido para processamento: {video_data.get('filename')}")
        
        # Atualizar métrica da fila
        queue_info = ch.queue_declare(queue='video_processing', passive=True)
        QUEUE_SIZE.set(queue_info.method.message_count)
        
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
    logger.info("🎬 Iniciando Video Processor...")
    
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