#!/usr/bin/env python3
import pika
import json
import os
import time
import logging
import socket
import threading
from flask import Flask, jsonify

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    return jsonify({"status": "healthy"})

def start_metrics_server():
    """Inicia o servidor HTTP para health checks."""
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=9102)
    except OSError as e:
        if e.errno == 98:  # Endereço já em uso
            logger.warning("Porta 9102 já em uso, ignorando erro e continuando...")
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

def callback(ch, method, properties, body):
    """Callback executado quando uma mensagem é recebida da fila."""
    video_data = json.loads(body)
    logger.info(f"Recebido para processamento: {video_data.get('filename')}")
    
    # Processa o vídeo (simplificado)
    try:
        time.sleep(2)  # Simulando processamento
        logger.info(f"Vídeo processado com sucesso: {video_data.get('filename')}")
    except Exception as e:
        logger.error(f"Erro ao processar vídeo: {e}")
    
    # Confirma que a mensagem foi processada
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    """Função principal do processador de vídeos."""
    # Inicia servidor de métricas em uma thread separada
    metrics_thread = threading.Thread(target=start_metrics_server)
    metrics_thread.daemon = True
    metrics_thread.start()
    
    while True:
        try:
            connection, channel = connect_to_rabbitmq()
            
            if channel:
                logger.info("Conectado ao RabbitMQ, aguardando mensagens...")
                
                # Configura o consumo da fila
                channel.basic_consume(queue='video_processing', 
                                     on_message_callback=callback)
                
                # Inicia o consumo de mensagens
                channel.start_consuming()
            else:
                # Se falhar na conexão, aguarda e tenta novamente
                logger.error("Falha na conexão com RabbitMQ, tentando novamente...")
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Processador de vídeos interrompido")
            if connection and connection.is_open:
                connection.close()
            break
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            time.sleep(5)

if __name__ == "__main__":
    logger.info("Iniciando processador de vídeos...")
    main()