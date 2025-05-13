from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_db_connection
import os
import time
import logging
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuração do ambiente
VIDEO_FOLDER = '/videos'
os.makedirs(VIDEO_FOLDER, exist_ok=True)

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
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        file = request.files['file']

        if file and file.filename:
            timestamp = str(int(time.time()))
            safe_filename = timestamp + "_" + file.filename
            filepath = os.path.join(VIDEO_FOLDER, safe_filename)
            file.save(filepath)

            # Gerar a URL (caminho para acessar o vídeo depois)
            url = f"/videos/{safe_filename}"

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO videos (title, description, filename, url) VALUES (%s, %s, %s, %s) RETURNING id",
                (title, description, safe_filename, url)
            )
            video_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()

            return jsonify({"message": "Video uploaded successfully!",
                           "filename": safe_filename,
                           "url": url}), 200
        else:
            return jsonify({"error": "No file uploaded"}), 400
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/videos', methods=['GET'])
def list_videos():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, description, filename, url FROM videos")
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
                'url': video[4]
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
        cur.execute("SELECT id, title, description, filename, url FROM videos WHERE id = %s", (video_id,))
        video = cur.fetchone()
        cur.close()
        conn.close()

        if video:
            video_data = {
                'id': video[0],
                'title': video[1],
                'description': video[2],
                'filename': video[3],
                'url': video[4]
            }
            return jsonify(video_data)
        else:
            return jsonify({"error": "Video not found"}), 404
    except Exception as e:
        logger.error(f"Erro ao buscar vídeo {video_id}: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)