import React, { useEffect, useState } from 'react';
import api from './api';
import './VideoList.css';

function VideoList({ videos: propVideos, loading: propLoading, error: propError, onRefresh }) {
  const [videos, setVideos] = useState(propVideos || []);
  const [loading, setLoading] = useState(propLoading || true);
  const [error, setError] = useState(propError || null);
  const [selectedVideo, setSelectedVideo] = useState(null);

  useEffect(() => {
    if (propVideos) setVideos(propVideos);
    if (propLoading !== undefined) setLoading(propLoading);
    if (propError !== undefined) setError(propError);
  }, [propVideos, propLoading, propError]);

  const fetchVideos = async () => {
    if (!onRefresh) {
      setLoading(true);
      try {
        const response = await api.get('/videos');
        setVideos(response.data);
        setError(null);
      } catch (error) {
        console.error('Erro ao buscar vídeos:', error);
        setError('Não foi possível carregar os vídeos. Tente novamente mais tarde.');
      } finally {
        setLoading(false);
      }
    } else {
      onRefresh();
    }
  };

  useEffect(() => {
    if (!propVideos) {
      fetchVideos();
    }
  }, []);

  const handleVideoSelect = (video) => {
    setSelectedVideo(video);
  };

  const handleCloseModal = () => {
    setSelectedVideo(null);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Carregando vídeos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="error-message">{error}</p>
        <button onClick={fetchVideos} className="refresh-btn">
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="video-list-container">
      <div className="video-list-header">
        <h2>Vídeos Disponíveis</h2>
        <button onClick={fetchVideos} className="refresh-btn">
          <span className="refresh-icon">↻</span> Atualizar
        </button>
      </div>

      {videos.length === 0 ? (
        <p className="no-videos">Nenhum vídeo disponível. Faça upload do seu primeiro vídeo!</p>
      ) : (
        <div className="video-grid">
          {videos.map((video) => (
            <div key={video.id} className="video-card" onClick={() => handleVideoSelect(video)}>
              <div className="video-thumbnail">
                <video preload="metadata">
                  <source src={video.url} type="video/mp4" />
                  Seu navegador não suporta a tag de vídeo.
                </video>
                <div className="play-icon">▶</div>
              </div>
              <div className="video-info">
                <h3 className="video-title">{video.title}</h3>
                <p className="video-description">{video.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedVideo && (
        <div className="video-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{selectedVideo.title}</h3>
              <button className="close-btn" onClick={handleCloseModal}>×</button>
            </div>
            <div className="video-player">
              <video controls autoPlay>
                <source src={selectedVideo.url} type="video/mp4" />
                Seu navegador não suporta a tag de vídeo.
              </video>
            </div>
            <div className="video-description">
              <p>{selectedVideo.description}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoList;