from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import os
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Caminho para os vídeos
VIDEO_FOLDER = '/videos'
os.makedirs(VIDEO_FOLDER, exist_ok=True)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/stream/<filename>')
def stream_video(filename):
    return send_from_directory(VIDEO_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)