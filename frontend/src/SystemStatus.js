import React, { useState } from 'react';
import './SystemStatus.css';
import api from './api';

function SystemStatus({ status, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [selectedService, setSelectedService] = useState(null);

  const handleRefresh = async () => {
    setLoading(true);
    await onRefresh();
    setLoading(false);
  };

  const handleServiceSelect = (service) => {
    setSelectedService(service);
  };

  const handleCloseDetails = () => {
    setSelectedService(null);
  };

  const handleRestartService = async (serviceId) => {
    if (!window.confirm('Tem certeza que deseja reiniciar este serviço?')) {
      return;
    }
    
    try {
      setLoading(true);
      await api.post(`/admin/services/${serviceId}/restart`);
      await onRefresh();
      alert('Serviço reiniciado com sucesso!');
    } catch (error) {
      console.error('Erro ao reiniciar serviço:', error);
      alert('Erro ao reiniciar serviço. Verifique o console para mais detalhes.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusClass = (status) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'running':
      case 'online':
        return 'status-healthy';
      case 'degraded':
      case 'warning':
        return 'status-warning';
      case 'unhealthy':
      case 'offline':
      case 'error':
        return 'status-error';
      default:
        return 'status-unknown';
    }
  };

  if (status.loading || loading) {
    return (
      <div className="status-loading">
        <div className="loading-spinner"></div>
        <p>Carregando informações do sistema...</p>
      </div>
    );
  }

  if (status.error) {
    return (
      <div className="status-error-container">
        <p className="status-error-message">{status.error}</p>
        <button onClick={handleRefresh} className="refresh-btn">
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="system-status-container">
      <div className="status-header">
        <h2>Status do Sistema</h2>
        <button onClick={handleRefresh} className="refresh-btn" disabled={loading}>
          <span className="refresh-icon">↻</span> Atualizar
        </button>
      </div>

      <div className="services-grid">
        {status.services.map((service) => (
          <div 
            key={service.id} 
            className={`service-card ${getStatusClass(service.status)}`}
            onClick={() => handleServiceSelect(service)}
          >
            <div className="service-header">
              <h3 className="service-name">{service.name}</h3>
              <span className={`service-status ${getStatusClass(service.status)}`}>
                {service.status}
              </span>
            </div>
            <div className="service-info">
              <p><strong>Tipo:</strong> {service.type}</p>
              <p><strong>Instância:</strong> {service.instance}</p>
              <p><strong>Uptime:</strong> {service.uptime}</p>
            </div>
          </div>
        ))}
      </div>

      {selectedService && (
        <div className="service-details-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{selectedService.name}</h3>
              <button className="close-btn" onClick={handleCloseDetails}>×</button>
            </div>
            
            <div className="service-details">
              <div className="details-group">
                <h4>Informações Gerais</h4>
                <p><strong>Status:</strong> <span className={getStatusClass(selectedService.status)}>{selectedService.status}</span></p>
                <p><strong>Tipo:</strong> {selectedService.type}</p>
                <p><strong>Instância:</strong> {selectedService.instance}</p>
                <p><strong>Versão:</strong> {selectedService.version || 'N/A'}</p>
                <p><strong>Uptime:</strong> {selectedService.uptime}</p>
              </div>
              
              <div className="details-group">
                <h4>Métricas</h4>
                <p><strong>CPU:</strong> {selectedService.metrics?.cpu || 'N/A'}</p>
                <p><strong>Memória:</strong> {selectedService.metrics?.memory || 'N/A'}</p>
                <p><strong>Requests:</strong> {selectedService.metrics?.requests || 'N/A'}</p>
                <p><strong>Erros:</strong> {selectedService.metrics?.errors || 'N/A'}</p>
              </div>
              
              {selectedService.logs && (
                <div className="details-group logs-group">
                  <h4>Logs Recentes</h4>
                  <div className="logs-container">
                    {selectedService.logs.map((log, index) => (
                      <div key={index} className={`log-entry log-${log.level.toLowerCase()}`}>
                        <span className="log-timestamp">{log.timestamp}</span>
                        <span className="log-level">{log.level}</span>
                        <span className="log-message">{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="service-actions">
                <button 
                  className="restart-btn" 
                  onClick={() => handleRestartService(selectedService.id)}
                  disabled={loading}
                >
                  Reiniciar Serviço
                </button>
                <a 
                  href={`/dashboard/d/service-details/service-details?var-service=${selectedService.name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="dashboard-link"
                >
                  Ver Dashboard Completo
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SystemStatus;