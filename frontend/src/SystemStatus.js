import React, { useState, useEffect } from 'react';
import api from './api';
import './SystemStatus.css';

function SystemStatus() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [refreshing, setRefreshing] = useState(false);  // ← Novo estado

  const fetchSystemStatus = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true);
      } else {
        setRefreshing(true);  // ← Mostrar apenas spinner pequeno
      }
      setError(null);

      // Buscar status dos serviços com timeout menor
      const servicesResponse = await api.get('/admin/services', { 
        timeout: 10000  // ← 10 segundos timeout
      });
      setServices(servicesResponse.data);

      // Buscar métricas do sistema
      try {
        const metricsResponse = await api.get('/admin/metrics/summary', {
          timeout: 5000  // ← 5 segundos timeout
        });
        setMetrics(metricsResponse.data);
      } catch (metricsError) {
        console.warn('Erro ao buscar métricas:', metricsError);
        // Não falhar se métricas não estiverem disponíveis
      }

      setLastUpdate(new Date());
    } catch (err) {
      console.error('Erro ao buscar status do sistema:', err);
      setError('Não foi possível carregar o status do sistema.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus(true);  // ← Loading completo na primeira vez
    
    // Auto-refresh a cada 30 segundos (sem loading completo)
    const interval = setInterval(() => {
      fetchSystemStatus(false);  // ← Refresh sem loading completo
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return '#10b981'; // verde
      case 'unhealthy':
      case 'offline':
        return '#ef4444'; // vermelho
      case 'timeout':
      case 'warning':
        return '#f59e0b'; // amarelo
      default:
        return '#6b7280'; // cinza
    }
  };

  const getStatusText = (status) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'Saudável';
      case 'unhealthy':
        return 'Não Saudável';
      case 'offline':
        return 'Offline';
      case 'timeout':
        return 'Timeout';
      case 'error':
        return 'Erro';
      default:
        return status;
    }
  };

  const formatUptime = (startTime) => {
    if (!startTime) return '---';
    
    const now = new Date();
    const start = new Date(startTime);
    const diff = now - start;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const restartService = async (serviceId) => {
    try {
      const response = await api.post(`/admin/services/${serviceId}/restart`);
      if (response.data.success) {
        alert(`Serviço ${serviceId} reiniciado com sucesso!`);
        // Aguardar um pouco e atualizar status
        setTimeout(fetchSystemStatus, 3000);
      } else {
        alert(`Erro ao reiniciar serviço: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Erro ao reiniciar serviço:', error);
      alert('Erro ao reiniciar serviço');
    }
  };

  if (loading) {
    return (
      <div className="system-status">
        <div className="status-header">
          <h2>Status do Sistema</h2>
        </div>
        <div className="loading">Carregando status dos serviços...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="system-status">
        <div className="status-header">
          <h2>Status do Sistema</h2>
          <div className="header-info">
            <span className="last-update error-text">
              ⚠️ Erro ao conectar com Admin Service
            </span>
            <button onClick={fetchSystemStatus} className="refresh-btn">
              🔄 Tentar Novamente
            </button>
          </div>
        </div>
        <div className="error-details">
          <h3>🚨 Problema de Conectividade</h3>
          <p><strong>Erro:</strong> {error}</p>
          <p><strong>Possíveis causas:</strong></p>
          <ul>
            <li>Admin Service está offline ou com problemas</li>
            <li>Problemas de rede entre serviços</li>
            <li>Sobrecarga do sistema</li>
          </ul>
          <p><strong>Soluções:</strong></p>
          <ul>
            <li>Verificar se o admin_service está a correr: <code>docker-compose ps admin_service</code></li>
            <li>Verificar logs: <code>docker-compose logs admin_service</code></li>
            <li>Reiniciar serviço: <code>docker-compose restart admin_service</code></li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="system-status">
      <div className="status-header">
        <h2>Status do Sistema</h2>
        <div className="header-info">
          <span className="last-update">
            Última atualização: {lastUpdate?.toLocaleTimeString('pt-PT')}
            {refreshing && <span className="refreshing-indicator"> 🔄</span>}
          </span>
          <button 
            onClick={() => fetchSystemStatus(false)} 
            className="refresh-btn"
            disabled={refreshing}
          >
            {refreshing ? '🔄 Atualizando...' : '🔄 Atualizar'}
          </button>
        </div>
      </div>

      {/* Resumo geral */}
      {metrics && (
        <div className="system-summary">
          <div className="summary-card">
            <h3>
              Resumo do Sistema 
              {metrics.prometheus_available && (
                <span className="prometheus-badge">📊 Prometheus</span>
              )}
              {!metrics.prometheus_available && (
                <span className="simulated-badge">⚠️ Simulado</span>
              )}
            </h3>
            <div className="summary-stats">
              <div className="stat">
                <span className="stat-label">Serviços Ativos:</span>
                <span className="stat-value" style={{
                  color: metrics.system.healthy_services === metrics.system.total_services ? '#10b981' : '#ef4444'
                }}>
                  {metrics.system.healthy_services}/{metrics.system.total_services}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">CPU Sistema:</span>
                <span className="stat-value">{metrics.performance.cpu_usage}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Memória Sistema:</span>
                <span className="stat-value">{metrics.performance.memory_usage}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Disponibilidade:</span>
                <span className="stat-value" style={{
                  color: parseFloat(metrics.system.availability) >= 100 ? '#10b981' : 
                         parseFloat(metrics.system.availability) >= 80 ? '#f59e0b' : '#ef4444'
                }}>
                  {metrics.system.availability}
                </span>
              </div>
              {metrics.performance.requests_rate && (
                <div className="stat">
                  <span className="stat-label">Requests/s:</span>
                  <span className="stat-value">{metrics.performance.requests_rate}</span>
                </div>
              )}
              {metrics.system.unhealthy_services > 0 && (
                <div className="stat alert-stat">
                  <span className="stat-label">Serviços com Problemas:</span>
                  <span className="stat-value" style={{ color: '#ef4444' }}>
                    {metrics.system.unhealthy_services}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Alertas */}
      {metrics && metrics.alerts && metrics.alerts.length > 0 && (
        <div className="alerts-section">
          <h3>🚨 Alertas</h3>
          <div className="alerts-list">
            {metrics.alerts.map((alert, index) => (
              <div key={index} className={`alert alert-${alert.severity}`}>
                <strong>{alert.service}:</strong> {alert.message}
                <span className="alert-time">
                  {new Date(alert.timestamp).toLocaleTimeString('pt-PT')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid de serviços */}
      <div className="services-grid">
        {services.map((service) => (
          <div 
            key={service.id} 
            className="service-card"
            style={{ borderColor: getStatusColor(service.status) }}
          >
            <div className="service-header">
              <h3>{service.name}</h3>
              <span 
                className="service-status"
                style={{ backgroundColor: getStatusColor(service.status) }}
              >
                {getStatusText(service.status)}
              </span>
            </div>
            
            <div className="service-info">
              <div className="info-row">
                <span className="info-label">Tipo:</span>
                <span className="info-value">{service.type}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Instância:</span>
                <span className="info-value">{service.instance}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Uptime:</span>
                <span className="info-value">{service.uptime}</span>
              </div>
              {service.response_time && (
                <div className="info-row">
                  <span className="info-label">Tempo Resposta:</span>
                  <span className="info-value">{service.response_time}</span>
                </div>
              )}
              {service.version && (
                <div className="info-row">
                  <span className="info-label">Versão:</span>
                  <span className="info-value">{service.version}</span>
                </div>
              )}
            </div>

            {/* Métricas específicas do serviço */}
            {service.metrics && (
              <div className="service-metrics">
                <h4>
                  Métricas 
                  {service.metrics.source === 'prometheus' && (
                    <span className="metrics-source prometheus">📊 Real</span>
                  )}
                  {service.metrics.source === 'simulated' && (
                    <span className="metrics-source simulated">⚠️ Sim</span>
                  )}
                </h4>
                <div className="metrics-grid">
                  {Object.entries(service.metrics).filter(([key]) => key !== 'source').map(([key, value]) => (
                    <div key={key} className="metric">
                      <span className="metric-label">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                      </span>
                      <span className="metric-value">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Logs recentes */}
            {service.logs && service.logs.length > 0 && (
              <div className="service-logs">
                <h4>Logs Recentes</h4>
                <div className="logs-list">
                  {service.logs.slice(0, 3).map((log, index) => (
                    <div key={index} className={`log-entry log-${log.level.toLowerCase()}`}>
                      <span className="log-time">{log.timestamp}</span>
                      <span className="log-level">{log.level}</span>
                      <span className="log-message">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ações */}
            <div className="service-actions">
              <button 
                onClick={() => restartService(service.id)}
                className="action-btn restart-btn"
                disabled={service.status === 'healthy'}
              >
                🔄 Reiniciar
              </button>

            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SystemStatus;