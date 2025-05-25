import React, { useState } from 'react';
import api from './api';
import './UploadVideo.css';

function UploadVideo({ handleVideoUpload }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!file) {
      setError('Por favor, selecione um arquivo para upload.');
      return;
    }

    // Verifica tamanho do arquivo (max 1GB)
    const maxSize = 1024 * 1024 * 1024; // 1GB em bytes
    if (file.size > maxSize) {
      setError('O arquivo é muito grande. Tamanho máximo: 1GB.');
      return;
    }

    // Verifica tipo do arquivo
    if (!file.type.startsWith('video/')) {
      setError('Formato inválido. Por favor, selecione um arquivo de vídeo.');
      return;
    }

    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('file', file);

    setUploading(true);
    setProgress(0);

    try {
      const response = await api.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: progressEvent => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(percentCompleted);
        },
        timeout: 300000 // 5 minutos timeout para uploads grandes
      });

      setSuccess(true);
      setTitle('');
      setDescription('');
      setFile(null);

      // Reseta o input de arquivo
      document.getElementById('video-file').value = '';

      if (handleVideoUpload) {
        handleVideoUpload(response.data.filename);
      }
    } catch (error) {
      console.error('Erro ao fazer upload do vídeo:', error);
      setError(
        error.response?.data?.error || 
        'Erro ao fazer upload do vídeo. Tente novamente.'
      );
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="upload-container">
      <h2>Upload de Vídeo</h2>
      
      {success && (
        <div className="alert success">
          Vídeo enviado com sucesso! Seu vídeo está sendo processado e logo estará disponível.
        </div>
      )}
      
      {error && (
        <div className="alert error">
          {error}
        </div>
      )}
      
      <form onSubmit={handleUpload} className="upload-form">
        <div className="form-group">
          <label htmlFor="video-title">Título</label>
          <input
            id="video-title"
            type="text"
            placeholder="Digite o título do vídeo"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            disabled={uploading}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="video-description">Descrição</label>
          <textarea
            id="video-description"
            placeholder="Adicione uma descrição para o vídeo"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            disabled={uploading}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="video-file">Arquivo de Vídeo</label>
          <input
            id="video-file"
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files[0])}
            required
            disabled={uploading}
          />
          <small className="file-hint">
            Formatos suportados: MP4, WebM, AVI, MOV, MKV. Tamanho máximo: 1GB.
            {file && (
              <span className="file-info">
                <br />Arquivo selecionado: {file.name} ({formatFileSize(file.size)})
              </span>
            )}
          </small>
        </div>
        
        {uploading && (
          <div className="progress-container">
            <div className="progress-text">
              Enviando vídeo... {progress}% ({file ? formatFileSize(file.size) : ''})
            </div>
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: `${progress}%` }}>
              </div>
            </div>
          </div>
        )}
        
        <button 
          type="submit" 
          className="submit-btn"
          disabled={uploading}
        >
          {uploading ? `Enviando... ${progress}%` : 'Fazer Upload'}
        </button>
      </form>
    </div>
  );
}

export default UploadVideo;