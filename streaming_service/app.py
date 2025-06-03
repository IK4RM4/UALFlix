from flask import Flask, send_from_directory, jsonify, request, Response
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import os
import logging
import mimetypes

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurar métricas Prometheus
try:
    metrics = PrometheusMetrics(app)
    logger.info("Métricas Prometheus configuradas")
except Exception as e:
    logger.warning(f"Erro ao configurar métricas Prometheus: {e}")

# Caminho para os vídeos
VIDEO_FOLDER = '/videos'
os.makedirs(VIDEO_FOLDER, exist_ok=True)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "service": "streaming",
        "video_folder": VIDEO_FOLDER,
        "videos_count": len([f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))])
    }), 200

@app.route('/stream/<filename>')
def stream_video(filename):
    """Stream de vídeo com suporte a range requests."""
    try:
        file_path = os.path.join(VIDEO_FOLDER, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"Vídeo não encontrado: {filename}")
            return jsonify({"error": "Video not found"}), 404
        
        def generate():
            with open(file_path, 'rb') as f:
                data = f.read(1024)
                while data:
                    yield data
                    data = f.read(1024)
        
        # Detectar tipo MIME
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'video/mp4'
        
        # Obter tamanho do arquivo
        file_size = os.path.getsize(file_path)
        
        # Verificar se é uma requisição Range
        range_header = request.headers.get('Range', None)
        if range_header:
            # Parse do header Range
            byte_start = 0
            byte_end = file_size - 1
            
            if range_header.startswith('bytes='):
                byte_range = range_header[6:]
                if '-' in byte_range:
                    start, end = byte_range.split('-', 1)
                    if start:
                        byte_start = int(start)
                    if end:
                        byte_end = int(end)
            
            # Ler apenas o range solicitado
            def generate_range():
                with open(file_path, 'rb') as f:
                    f.seek(byte_start)
                    remaining = byte_end - byte_start + 1
                    while remaining:
                        chunk_size = min(1024, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        yield data
                        remaining -= len(data)
            
            # Retornar resposta 206 Partial Content
            response = Response(
                generate_range(),
                206,
                headers={
                    'Content-Type': mime_type,
                    'Accept-Ranges': 'bytes',
                    'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                    'Content-Length': str(byte_end - byte_start + 1),
                }
            )
            return response
        else:
            # Retornar arquivo completo
            response = Response(
                generate(),
                200,
                headers={
                    'Content-Type': mime_type,
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(file_size),
                }
            )
            return response
            
    except Exception as e:
        logger.error(f"Erro ao fazer stream do vídeo {filename}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/download/<filename>')
def download_video(filename):
    """Download direto do vídeo."""
    try:
        file_path = os.path.join(VIDEO_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Video not found"}), 404
            
        return send_from_directory(
            VIDEO_FOLDER, 
            filename, 
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Erro ao baixar vídeo {filename}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/info/<filename>')
def video_info(filename):
    """Informações sobre o vídeo."""
    try:
        file_path = os.path.join(VIDEO_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Video not found"}), 404
        
        stat = os.stat(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        info = {
            "filename": filename,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "mime_type": mime_type or "video/mp4",
            "created": stat.st_ctime,
            "modified": stat.st_mtime
        }
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Erro ao obter info do vídeo {filename}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/list')
def list_available_videos():
    """Lista vídeos disponíveis no storage."""
    try:
        videos = []
        for filename in os.listdir(VIDEO_FOLDER):
            if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                file_path = os.path.join(VIDEO_FOLDER, filename)
                stat = os.stat(file_path)
                videos.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "url": f"/stream/{filename}"
                })
        
        return jsonify({
            "count": len(videos),
            "videos": videos
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar vídeos: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/status')
def status_endpoint():
    """Endpoint para informações do serviço."""
    try:
        video_count = len([f for f in os.listdir(VIDEO_FOLDER) 
                          if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))])
        
        total_size = sum(os.path.getsize(os.path.join(VIDEO_FOLDER, f)) 
                        for f in os.listdir(VIDEO_FOLDER) if os.path.isfile(os.path.join(VIDEO_FOLDER, f)))
        
        status_data = {
            "service": "streaming",
            "status": "healthy",
            "video_count": video_count,
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "storage_path": VIDEO_FOLDER
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("🎥 Iniciando Streaming Service...")
    logger.info(f"📁 Pasta de vídeos: {VIDEO_FOLDER}")
    
    try:
        app.run(host='0.0.0.0', port=8001, debug=False)
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar servidor: {e}")
        exit(1)