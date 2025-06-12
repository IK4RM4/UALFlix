import React, { useState, useEffect, useCallback, useRef } from 'react';
import api from './api';
import './SystemStatus.css';

function SystemStatus() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedService, setSelectedService] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [connectionHistory, setConnectionHistory] = useState([]);
  const [performanceHistory, setPerformanceHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [showSystemLogs, setShowSystemLogs] = useState(false);
  const [realTimeMode, setRealTimeMode] = useState(false);
  const intervalRef = useRef(null);
  const wsRef = useRef(null);

  const fetchSystemStatus = useCallback(async (showLoading = true, source = 'manual') => {
    try {
      if (showLoading) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);

      // Fetch services with timeout and retry logic
      const servicesResponse = await fetchWithRetry('/admin/services', 3);
      
      // Validate response
      if (!Array.isArray(servicesResponse.data)) {
        throw new Error('Invalid services data format');
      }
      
      setServices(servicesResponse.data);

      // Fetch enhanced metrics
      try {
        const [metricsResponse, mongoResponse] = await Promise.allSettled([
          fetchWithRetry('/admin/metrics/summary', 2),
          fetchWithRetry('/admin/metrics/mongodb', 2)
        ]);

        const enhancedMetrics = {
          ...metricsResponse.status === 'fulfilled' ? metricsResponse.value.data : {},
          mongodb: mongoResponse.status === 'fulfilled' ? mongoResponse.value.data : null,
          dataSource: determineDataSource(servicesResponse.data),
          fetchTime: Date.now(),
          source: source
        };
        
        setMetrics(enhancedMetrics);
        updatePerformanceHistory(enhancedMetrics);
        checkForAlerts(servicesResponse.data, enhancedMetrics);
        
      } catch (metricsError) {
        console.warn('Failed to fetch enhanced metrics:', metricsError);
        setMetrics({ 
          dataSource: 'simulated', 
          error: 'Metrics unavailable',
          fetchTime: Date.now(),
          source: source 
        });
      }

      setLastUpdate(new Date());
      updateConnectionHistory(true, source);
      
    } catch (err) {
      console.error('Error fetching system status:', err);
      const errorMessage = getDetailedErrorMessage(err);
      setError(errorMessage);
      updateConnectionHistory(false, source, err.message);
      
      // Generate alerts for connection issues
      setAlerts(prev => [...prev.slice(-4), {
        id: Date.now(),
        severity: 'critical',
        service: 'admin_service',
        message: `Connection failed: ${err.message}`,
        timestamp: new Date().toISOString(),
        source: 'connection_monitor'
      }]);
      
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchWithRetry = async (endpoint, retries = 3, delay = 1000) => {
    for (let i = 0; i < retries; i++) {
      try {
        const response = await api.get(endpoint, { 
          timeout: i === 0 ? 5000 : 10000 // Longer timeout for retries
        });
        return response;
      } catch (error) {
        if (i === retries - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
      }
    }
  };

  const determineDataSource = (servicesData) => {
    // Enhanced detection logic
    const hasRealTimestamps = servicesData.some(service => 
      service.last_check && new Date(service.last_check).getTime() > Date.now() - 60000
    );
    
    const hasVariedMetrics = servicesData.some(service => 
      service.metrics && Object.values(service.metrics).some(value => 
        typeof value === 'string' && value.includes('.') && !value.endsWith('.0')
      )
    );
    
    const hasRealisticUptime = servicesData.some(service =>
      service.uptime && !service.uptime.includes('h 0m') && service.uptime !== '---'
    );

    if (hasRealTimestamps && hasVariedMetrics && hasRealisticUptime) {
      return 'real';
    } else if (hasRealTimestamps || hasVariedMetrics) {
      return 'mixed';
    } else {
      return 'simulated';
    }
  };

  const getDetailedErrorMessage = (error) => {
    if (error.code === 'ECONNREFUSED') {
      return 'Connection refused - Admin service is not responding';
    } else if (error.code === 'ETIMEDOUT') {
      return 'Request timeout - Admin service is overloaded or slow';
    } else if (error.response?.status === 404) {
      return 'Admin endpoints not found - Check service configuration';
    } else if (error.response?.status >= 500) {
      return 'Admin service internal error - Check service logs';
    } else {
      return error.message || 'Unknown connection error';
    }
  };

  const updateConnectionHistory = (success, source, errorMessage = null) => {
    setConnectionHistory(prev => [
      ...prev.slice(-19), // Keep last 20 entries
      {
        timestamp: new Date(),
        success,
        source,
        error: errorMessage,
        responseTime: Date.now() % 1000 // Simple response time simulation
      }
    ]);
  };

  const updatePerformanceHistory = (newMetrics) => {
    setPerformanceHistory(prev => [
      ...prev.slice(-29), // Keep last 30 entries
      {
        timestamp: new Date(),
        availability: parseFloat(newMetrics.system?.availability || 0),
        servicesCount: newMetrics.system?.healthy_services || 0,
        cpuUsage: parseFloat(newMetrics.performance?.cpu_usage || 0),
        memoryUsage: parseFloat(newMetrics.performance?.memory_usage || 0)
      }
    ]);
  };

  const checkForAlerts = (servicesData, metricsData) => {
    const newAlerts = [];
    const now = new Date().toISOString();

    // Check for unhealthy services
    servicesData.forEach(service => {
      if (service.status !== 'healthy') {
        newAlerts.push({
          id: `service_${service.id}_${Date.now()}`,
          severity: service.status === 'error' ? 'critical' : 'warning',
          service: service.id,
          message: `Service ${service.name} is ${service.status}`,
          timestamp: now,
          source: 'health_monitor'
        });
      }
    });

    // Check system metrics
    if (metricsData.system) {
      const availability = parseFloat(metricsData.system.availability || 100);
      if (availability < 90) {
        newAlerts.push({
          id: `availability_${Date.now()}`,
          severity: availability < 50 ? 'critical' : 'warning',
          service: 'system',
          message: `Low system availability: ${availability.toFixed(1)}%`,
          timestamp: now,
          source: 'availability_monitor'
        });
      }
    }

    // Check MongoDB status
    if (metricsData.mongodb && metricsData.mongodb.replica_set?.status !== 'healthy') {
      newAlerts.push({
        id: `mongodb_${Date.now()}`,
        severity: 'critical',
        service: 'mongodb',
        message: 'MongoDB replica set is not healthy',
        timestamp: now,
        source: 'database_monitor'
      });
    }

    setAlerts(prev => [...prev.slice(-10), ...newAlerts].slice(-15)); // Keep last 15 alerts
  };

  // WebSocket connection for real-time updates
  const setupRealTimeConnection = useCallback(() => {
    if (!realTimeMode) return;

    try {
      const wsUrl = `ws://localhost:8002/ws/metrics`;
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'metrics_update') {
            setMetrics(prev => ({ ...prev, ...data.payload }));
            setLastUpdate(new Date());
          }
        } catch (error) {
          console.error('WebSocket message error:', error);
        }
      };

      wsRef.current.onerror = () => {
        console.warn('WebSocket connection failed, falling back to polling');
        setRealTimeMode(false);
      };

    } catch (error) {
      console.warn('WebSocket not supported, using polling mode');
      setRealTimeMode(false);
    }
  }, [realTimeMode]);

  // Enhanced auto-refresh logic
  useEffect(() => {
    fetchSystemStatus(true, 'initial');
    
    if (autoRefresh && !realTimeMode) {
      intervalRef.current = setInterval(() => {
        fetchSystemStatus(false, 'auto_refresh');
      }, refreshInterval * 1000);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, realTimeMode, fetchSystemStatus]);

  useEffect(() => {
    setupRealTimeConnection();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [setupRealTimeConnection]);

  // Advanced filtering and sorting
  const filteredAndSortedServices = services
    .filter(service => {
      const matchesStatus = filterStatus === 'all' || service.status === filterStatus;
      const matchesType = filterType === 'all' || service.type === filterType;
      const matchesSearch = service.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          service.id.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesStatus && matchesType && matchesSearch;
    })
    .sort((a, b) => {
      let aValue, bValue;
      
      switch (sortBy) {
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'responseTime':
          aValue = parseFloat(a.response_time?.replace('s', '') || 0);
          bValue = parseFloat(b.response_time?.replace('s', '') || 0);
          break;
        case 'type':
          aValue = a.type;
          bValue = b.type;
          break;
        default:
          aValue = a.name;
          bValue = b.name;
      }
      
      if (sortOrder === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });

  const getServiceTypeOptions = () => {
    const types = [...new Set(services.map(s => s.type))];
    return types.sort();
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy': return '#22c55e';
      case 'unhealthy': case 'offline': return '#ef4444';
      case 'timeout': case 'warning': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const getDataSourceBadge = (dataSource) => {
    switch (dataSource) {
      case 'real':
        return <span className="data-source-badge real">Dados Reais</span>;
      case 'mixed':
        return <span className="data-source-badge mixed">Dados Mistos</span>;
      case 'simulated':
        return <span className="data-source-badge simulated">Simulado</span>;
      default:
        return <span className="data-source-badge unknown">Desconhecido</span>;
    }
  };

  const getServiceTypeIcon = (type) => {
    const icons = {
      'microservice': 'MS',
      'database': 'DB',
      'messaging': 'MQ',
      'processor': 'PR',
      'frontend': 'FE',
      'monitoring': 'MN',
      'proxy': 'PX'
    };
    return icons[type] || 'SV';
  };

  const formatUptime = (uptime) => {
    if (!uptime || uptime === '---') return 'Desconhecido';
    return uptime;
  };

  const formatMetricLabel = (key) => {
    const labels = {
      'cpu': 'CPU',
      'memory_usage': 'Mem',
      'request_rate': 'Req/s',
      'avg_response_time': 'Resp',
      'active_replicas': 'Réplicas',
      'data_size_mb': 'Dados',
      'users_count': 'Users',
      'videos_count': 'Vídeos',
      'collections': 'Coleções',
      'objects': 'Objetos',
      'replication_lag_seconds': 'Lag'
    };
    return labels[key] || key.split('_')[0];
  };

  const formatMetricValue = (key, value) => {
    if (typeof value === 'number') {
      if (key.includes('_mb')) return `${value}MB`;
      if (key.includes('_seconds')) return `${value}s`;
      if (key.includes('_percent')) return `${value}%`;
      if (value > 1000) return `${(value / 1000).toFixed(1)}k`;
      return value.toString();
    }
    return value?.toString().length > 8 ? value.toString().substring(0, 8) + '...' : value;
  };

  const truncateMessage = (message, maxLength) => {
    if (!message) return '';
    return message.length > maxLength ? message.substring(0, maxLength) + '...' : message;
  };

  const copyServiceInfo = (service) => {
    const info = {
      name: service.name,
      status: service.status,
      type: service.type,
      instance: service.instance,
      response_time: service.response_time,
      uptime: service.uptime,
      metrics: service.metrics
    };
    
    navigator.clipboard.writeText(JSON.stringify(info, null, 2)).then(() => {
      alert('Informações copiadas para o clipboard');
    }).catch(() => {
      alert('Erro ao copiar informações');
    });
  };

  const restartService = async (serviceId) => {
    if (!window.confirm(`Tem a certeza que quer reiniciar ${serviceId}?`)) {
      return;
    }

    try {
      const response = await api.post(`/admin/services/${serviceId}/restart`);
      if (response.data.success) {
        alert(`Serviço ${serviceId} reiniciado com sucesso!`);
        setTimeout(() => fetchSystemStatus(false, 'restart_action'), 3000);
      } else {
        alert(`Falha ao reiniciar serviço: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Erro ao reiniciar serviço:', error);
      alert('Erro ao reiniciar serviço. Verifique os logs.');
    }
  };

  const exportSystemReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      services: services,
      metrics: metrics,
      connectionHistory: connectionHistory,
      performanceHistory: performanceHistory,
      alerts: alerts,
      summary: {
        totalServices: services.length,
        healthyServices: services.filter(s => s.status === 'healthy').length,
        dataSource: metrics?.dataSource,
        availability: metrics?.system?.availability
      }
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ualflix-system-report-${new Date().toISOString().slice(0, 19)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Performance chart component
  const MiniChart = ({ data, color = '#e50914' }) => {
    if (!data || data.length < 2) return <div className="mini-chart-empty">Sem dados</div>;
    
    const max = Math.max(...data.map(d => d.value));
    const min = Math.min(...data.map(d => d.value));
    const range = max - min || 1;
    
    return (
      <div className="mini-chart">
        <svg width="80" height="30" viewBox="0 0 80 30">
          <polyline
            points={data.map((d, i) => 
              `${(i / (data.length - 1)) * 80},${30 - ((d.value - min) / range) * 30}`
            ).join(' ')}
            fill="none"
            stroke={color}
            strokeWidth="2"
          />
        </svg>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="system-status">
        <div className="status-header">
          <h2>Estado do Sistema</h2>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>A carregar estado do sistema...</p>
          <small>A conectar aos serviços de administração...</small>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="system-status">
        <div className="status-header">
          <h2>Estado do Sistema</h2>
          <div className="header-controls">
            <button onClick={() => fetchSystemStatus(true, 'error_retry')} className="btn btn-primary">
              Tentar Novamente
            </button>
          </div>
        </div>
        <div className="error-container">
          <div className="error-icon">!</div>
          <h3>Erro de Conexão</h3>
          <p className="error-message">{error}</p>
          
          <div className="connection-diagnostics">
            <h4>Diagnóstico de Conexão</h4>
            <div className="diagnostic-grid">
              <div className="diagnostic-item">
                <span className="label">Última tentativa:</span>
                <span className="value">{lastUpdate?.toLocaleTimeString() || 'Nunca'}</span>
              </div>
              <div className="diagnostic-item">
                <span className="label">Histórico de conexões:</span>
                <span className="value">
                  {connectionHistory.length > 0 ? 
                    `${connectionHistory.filter(h => h.success).length}/${connectionHistory.length} sucessos` : 
                    'Sem histórico'
                  }
                </span>
              </div>
            </div>
          </div>

          <div className="error-suggestions">
            <h4>Passos de Resolução:</h4>
            <ol>
              <li>Verificar se o admin service está em execução: <code>docker-compose ps admin_service</code></li>
              <li>Verificar logs do serviço: <code>docker-compose logs admin_service</code></li>
              <li>Reiniciar o serviço: <code>docker-compose restart admin_service</code></li>
              <li>Verificar conectividade de rede entre contentores</li>
              <li>Verificar se o MongoDB está acessível</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  const healthyServices = services.filter(s => s.status === 'healthy').length;
  const totalServices = services.length;

  return (
    <div className="system-status">
      <div className="status-header">
        <h2>Painel de Administração do Sistema</h2>
        <div className="header-info">
          {metrics?.dataSource && getDataSourceBadge(metrics.dataSource)}
          <span className="system-time">
            Última atualização: {lastUpdate?.toLocaleTimeString()}
            {refreshing && <span className="refreshing-indicator"> (A atualizar...)</span>}
          </span>
        </div>
        <div className="header-controls">
          <div className="control-group">
            <label>
              <input
                type="checkbox"
                checked={realTimeMode}
                onChange={(e) => setRealTimeMode(e.target.checked)}
              />
              Tempo Real
            </label>
          </div>
          
          <div className="control-group">
            <label>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                disabled={realTimeMode}
              />
              Auto-refresh
            </label>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              disabled={!autoRefresh || realTimeMode}
            >
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
              <option value={300}>5m</option>
            </select>
          </div>

          <button 
            onClick={() => fetchSystemStatus(false, 'manual_refresh')} 
            className="btn btn-primary"
            disabled={refreshing}
          >
            {refreshing ? 'A atualizar...' : 'Atualizar'}
          </button>

          <button 
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="btn btn-secondary"
          >
            {showAdvanced ? 'Simples' : 'Avançado'}
          </button>

          <button 
            onClick={exportSystemReport}
            className="btn btn-secondary"
          >
            Exportar Relatório
          </button>
        </div>
      </div>

      {/* Enhanced System Overview */}
      <div className="system-overview">
        <div className="overview-card">
          <div className="card-header">
            <h3>Resumo do Sistema</h3>
            <div className="chart-container">
              <MiniChart 
                data={performanceHistory.map(h => ({ value: h.availability }))}
                color="#22c55e"
              />
            </div>
          </div>
          <div className="overview-stats">
            <div className="stat-item">
              <div className="stat-value" style={{ 
                color: healthyServices === totalServices ? '#22c55e' : '#ef4444' 
              }}>
                {healthyServices}/{totalServices}
              </div>
              <div className="stat-label">Serviços Saudáveis</div>
            </div>
            {metrics?.system && (
              <>
                <div className="stat-item">
                  <div className="stat-value">{metrics.performance?.cpu_usage || 'N/A'}</div>
                  <div className="stat-label">CPU Sistema</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{metrics.performance?.memory_usage || 'N/A'}</div>
                  <div className="stat-label">Memória Sistema</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value" style={{
                    color: parseFloat(metrics.system.availability || 0) >= 95 ? '#22c55e' : 
                           parseFloat(metrics.system.availability || 0) >= 80 ? '#f59e0b' : '#ef4444'
                  }}>
                    {metrics.system.availability || 'N/A'}
                  </div>
                  <div className="stat-label">Disponibilidade</div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* MongoDB Enhanced Status */}
        {metrics?.mongodb && (
          <div className="overview-card">
            <div className="card-header">
              <h3>Estado MongoDB</h3>
              <span className={`status-indicator ${metrics.mongodb.replica_set?.status || 'unknown'}`}>
                {metrics.mongodb.replica_set?.status || 'Desconhecido'}
              </span>
            </div>
            <div className="mongodb-details">
              <div className="replica-set-info">
                <div className="replica-member">
                  <span className="role">Primary</span>
                  <span className="status">{metrics.mongodb.replica_set?.primary_healthy ? 'Ativo' : 'Erro'}</span>
                </div>
                <div className="replica-member">
                  <span className="role">Secondary</span>
                  <span className="member-count">{metrics.mongodb.replica_set?.healthy_members || 0}/{metrics.mongodb.replica_set?.total_members || 0}</span>
                </div>
                <div className="replica-stats">
                  <div className="stat">
                    <span className="label">Lag Replicação:</span>
                    <span className="value">{metrics.mongodb.replication?.lag_seconds || 0}s</span>
                  </div>
                  <div className="stat">
                    <span className="label">Tamanho Dados:</span>
                    <span className="value">{metrics.mongodb.performance?.data_size_mb || 0} MB</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Connection Health */}
        <div className="overview-card">
          <div className="card-header">
            <h3>Saúde da Conexão</h3>
            <div className="connection-indicator">
              {connectionHistory.slice(-5).map((conn, i) => (
                <span 
                  key={i} 
                  className={`connection-dot ${conn.success ? 'success' : 'failure'}`}
                  title={`${conn.timestamp.toLocaleTimeString()} - ${conn.success ? 'Sucesso' : conn.error}`}
                />
              ))}
            </div>
          </div>
          <div className="connection-stats">
            <div className="stat-item">
              <div className="stat-value">
                {connectionHistory.length > 0 ? 
                  Math.round((connectionHistory.filter(h => h.success).length / connectionHistory.length) * 100) : 0
                }%
              </div>
              <div className="stat-label">Taxa Sucesso</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{connectionHistory.length}</div>
              <div className="stat-label">Total Tentativas</div>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="advanced-controls">
          <div className="filters-row">
            <div className="filter-group">
              <label>Pesquisar:</label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Nome do serviço..."
                className="search-input"
              />
            </div>
            
            <div className="filter-group">
              <label>Estado:</label>
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                <option value="all">Todos</option>
                <option value="healthy">Saudável</option>
                <option value="unhealthy">Não Saudável</option>
                <option value="timeout">Timeout</option>
                <option value="error">Erro</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Tipo:</label>
              <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                <option value="all">Todos</option>
                {getServiceTypeOptions().map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label>Ordenar por:</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="name">Nome</option>
                <option value="status">Estado</option>
                <option value="type">Tipo</option>
                <option value="responseTime">Tempo Resposta</option>
              </select>
              <button 
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="sort-order-btn"
              >
                {sortOrder === 'asc' ? 'ASC' : 'DESC'}
              </button>
            </div>
          </div>

          <div className="view-options">
            <button 
              onClick={() => setShowSystemLogs(!showSystemLogs)}
              className="btn btn-secondary btn-sm"
            >
              {showSystemLogs ? 'Ocultar' : 'Mostrar'} Logs Sistema
            </button>
          </div>
        </div>
      )}

      {/* Enhanced Alerts Section */}
      {alerts.length > 0 && (
        <div className="alerts-section">
          <div className="alerts-header">
            <h3>Alertas do Sistema ({alerts.length})</h3>
            <button 
              onClick={() => setAlerts([])}
              className="btn btn-secondary btn-sm"
            >
              Limpar Todos
            </button>
          </div>
          <div className="alerts-list">
            {alerts.slice(-5).map((alert) => (
              <div key={alert.id} className={`alert alert-${alert.severity}`}>
                <div className="alert-content">
                  <div className="alert-header">
                    <strong>{alert.service}:</strong>
                    <span className="alert-source">[{alert.source}]</span>
                  </div>
                  <div className="alert-message">{alert.message}</div>
                </div>
                <div className="alert-meta">
                  <span className="alert-time">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                  <button 
                    onClick={() => setAlerts(prev => prev.filter(a => a.id !== alert.id))}
                    className="alert-dismiss"
                  >
                    X
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Logs Panel */}
      {showAdvanced && showSystemLogs && (
        <div className="system-logs-panel">
          <div className="logs-header">
            <h3>Logs do Sistema</h3>
            <div className="logs-controls">
              <select className="log-level-filter">
                <option value="all">Todos os Níveis</option>
                <option value="error">Apenas Erros</option>
                <option value="warning">Avisos e Erros</option>
                <option value="info">Info e Acima</option>
              </select>
            </div>
          </div>
          <div className="logs-container">
            {connectionHistory.slice(-10).map((entry, index) => (
              <div key={index} className={`log-entry ${entry.success ? 'log-info' : 'log-error'}`}>
                <span className="log-timestamp">{entry.timestamp.toLocaleTimeString()}</span>
                <span className="log-level">{entry.success ? 'INFO' : 'ERROR'}</span>
                <span className="log-message">
                  {entry.success ? 
                    `Connection successful via ${entry.source} (${entry.responseTime}ms)` :
                    `Connection failed via ${entry.source}: ${entry.error}`
                  }
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Enhanced Services Grid */}
      <div className="services-section">
        <div className="services-header">
          <h3>Estado dos Serviços ({filteredAndSortedServices.length}/{totalServices})</h3>
          <div className="services-summary">
            <span className="healthy-count">
              {filteredAndSortedServices.filter(s => s.status === 'healthy').length} Saudáveis
            </span>
            <span className="unhealthy-count">
              {filteredAndSortedServices.filter(s => s.status !== 'healthy').length} Com Problemas
            </span>
          </div>
        </div>
        
        <div className="services-grid">
          {filteredAndSortedServices.map((service) => (
            <div 
              key={service.id} 
              className={`service-card ${service.status} ${selectedService?.id === service.id ? 'selected' : ''}`}
              style={{ borderColor: getStatusColor(service.status) }}
              onClick={() => setSelectedService(service)}
            >
              <div className="service-header">
                <div className="service-name">
                  <span className="service-icon">{getServiceTypeIcon(service.type)}</span>
                  <span className="name-text">{service.name}</span>
                  {service.cluster_info?.replicas > 1 && (
                    <span className="replica-badge">{service.cluster_info.replicas}x</span>
                  )}
                </div>
                <div className="service-status-group">
                  <span 
                    className="service-status"
                    style={{ backgroundColor: getStatusColor(service.status) }}
                  >
                    {service.status}
                  </span>
                  {service.automatic_metrics_enabled && (
                    <span className="metrics-badge" title="Métricas automáticas ativas">METR</span>
                  )}
                </div>
              </div>
              
              <div className="service-info">
                <div className="info-grid">
                  <div className="info-item">
                    <span className="label">Tipo:</span>
                    <span className="value">{service.type}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Instância:</span>
                    <span className="value" title={service.instance}>{service.instance}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Resposta:</span>
                    <span className="value response-time">{service.response_time}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Uptime:</span>
                    <span className="value">{formatUptime(service.uptime)}</span>
                  </div>
                </div>
              </div>

              {/* Enhanced Metrics Display */}
              {service.metrics && (
                <div className="service-metrics-preview">
                  <div className="metrics-header">
                    <span>Métricas</span>
                    <div className="metrics-badges">
                      {service.metrics.source === 'mongodb_primary' && (
                        <span className="metrics-badge mongodb" title="Dados MongoDB Primary">MongoDB-P</span>
                      )}
                      {service.metrics.source === 'mongodb_secondary' && (
                        <span className="metrics-badge mongodb" title="Dados MongoDB Secondary">MongoDB-S</span>
                      )}
                      {service.metrics.source === 'prometheus' && (
                        <span className="metrics-badge prometheus" title="Dados Prometheus">Prometheus</span>
                      )}
                      {service.metrics.source === 'real_replica_set' && (
                        <span className="metrics-badge real" title="Dados Reais do Replica Set">Real</span>
                      )}
                      {service.metrics.source?.includes('simulated') && (
                        <span className="metrics-badge simulated" title="Dados Simulados">Simulado</span>
                      )}
                    </div>
                  </div>
                  
                  <div className="metrics-grid-preview">
                    {Object.entries(service.metrics)
                      .filter(([key]) => !['source', 'error', 'connection_type'].includes(key))
                      .slice(0, 4)
                      .map(([key, value]) => (
                      <div key={key} className="metric-preview">
                        <div className="metric-label" title={key}>
                          {formatMetricLabel(key)}:
                        </div>
                        <div className="metric-value" title={`${key}: ${value}`}>
                          {formatMetricValue(key, value)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Database Specific Info */}
              {service.replica_set_info && (
                <div className="replica-set-preview">
                  <div className="replica-info">
                    <span className="replica-role">{service.replica_set_info.role}</span>
                    {service.replica_set_info.members_count && (
                      <span className="replica-members">
                        {service.replica_set_info.members_count} membros
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Recent Activity */}
              {service.logs && service.logs.length > 0 && (
                <div className="recent-activity">
                  <div className="activity-header">Atividade Recente:</div>
                  <div className="activity-item">
                    <span className={`activity-level ${service.logs[0].level.toLowerCase()}`}>
                      {service.logs[0].level}
                    </span>
                    <span className="activity-message" title={service.logs[0].message}>
                      {truncateMessage(service.logs[0].message, 40)}
                    </span>
                    <span className="activity-time">{service.logs[0].timestamp}</span>
                  </div>
                </div>
              )}

              <div className="service-actions">
                <button 
                  className="btn btn-sm btn-primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedService(service);
                  }}
                >
                  Detalhes
                </button>
                
                <button 
                  className="btn btn-sm btn-warning"
                  onClick={(e) => {
                    e.stopPropagation();
                    restartService(service.id);
                  }}
                  disabled={service.status === 'healthy'}
                  title={service.status === 'healthy' ? 'Serviço está saudável' : 'Reiniciar serviço'}
                >
                  Reiniciar
                </button>

                {showAdvanced && (
                  <button 
                    className="btn btn-sm btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      copyServiceInfo(service);
                    }}
                    title="Copiar informações para clipboard"
                  >
                    COPY
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Enhanced Service Detail Modal */}
      {selectedService && (
        <ServiceDetailModal 
          service={selectedService} 
          onClose={() => setSelectedService(null)}
          metrics={metrics}
          showAdvanced={showAdvanced}
          onRestart={restartService}
        />
      )}
    </div>
  );
}

// Enhanced Service Detail Modal Component
function ServiceDetailModal({ service, onClose, metrics, showAdvanced, onRestart }) {
  const [activeTab, setActiveTab] = useState('overview');
  
  if (!service) return null;

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy': return '#22c55e';
      case 'unhealthy': case 'offline': return '#ef4444';
      case 'timeout': case 'warning': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const formatMetricLabelDetailed = (key) => {
    const labels = {
      'cpu': 'Utilização de CPU',
      'memory_usage': 'Utilização de Memória',
      'request_rate': 'Taxa de Requisições',
      'avg_response_time': 'Tempo Médio de Resposta',
      'active_replicas': 'Réplicas Ativas',
      'data_size_mb': 'Tamanho dos Dados',
      'storage_size_mb': 'Tamanho do Storage',
      'index_size_mb': 'Tamanho dos Índices',
      'users_count': 'Número de Utilizadores',
      'videos_count': 'Número de Vídeos',
      'views_count': 'Número de Visualizações',
      'collections': 'Número de Coleções',
      'objects': 'Número de Objetos',
      'replication_lag_seconds': 'Lag de Replicação',
      'uptime': 'Tempo de Funcionamento'
    };
    return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatMetricValueDetailed = (key, value) => {
    if (typeof value === 'number') {
      if (key.includes('_mb')) return `${value.toLocaleString()} MB`;
      if (key.includes('_seconds')) return `${value} segundos`;
      if (key.includes('_percent')) return `${value}%`;
      if (key.includes('_count')) return value.toLocaleString();
      if (value > 1000000) return `${(value / 1000000).toFixed(2)}M`;
      if (value > 1000) return `${(value / 1000).toFixed(1)}K`;
      return value.toLocaleString();
    }
    return value?.toString() || 'N/A';
  };

  const getMetricDescription = (key) => {
    const descriptions = {
      'cpu': 'Percentagem de utilização do processador',
      'memory_usage': 'Memória RAM utilizada pelo serviço',
      'request_rate': 'Número de requisições por segundo',
      'avg_response_time': 'Tempo médio para processar requisições',
      'data_size_mb': 'Espaço ocupado pelos dados na base de dados',
      'users_count': 'Total de utilizadores registados no sistema',
      'videos_count': 'Total de vídeos no catálogo',
      'replication_lag_seconds': 'Atraso na sincronização entre réplicas'
    };
    return descriptions[key] || '';
  };

  return (
    <div className="service-modal-overlay" onClick={onClose}>
      <div className="service-modal-content enhanced" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <h3>{service.name} - Informações Detalhadas</h3>
            <div className="service-badges">
              <span 
                className="status-badge"
                style={{ backgroundColor: getStatusColor(service.status) }}
              >
                {service.status}
              </span>
              <span className="type-badge">{service.type}</span>
            </div>
          </div>
          <button className="close-btn" onClick={onClose}>X</button>
        </div>
        
        <div className="modal-tabs">
          <button 
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Visão Geral
          </button>
          <button 
            className={`tab-btn ${activeTab === 'metrics' ? 'active' : ''}`}
            onClick={() => setActiveTab('metrics')}
          >
            Métricas
          </button>
          <button 
            className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('logs')}
          >
            Logs
          </button>
          {showAdvanced && (
            <button 
              className={`tab-btn ${activeTab === 'advanced' ? 'active' : ''}`}
              onClick={() => setActiveTab('advanced')}
            >
              Avançado
            </button>
          )}
        </div>

        <div className="modal-body">
          {activeTab === 'overview' && (
            <div className="service-overview-tab">
              <div className="service-details-grid">
                <div className="detail-section">
                  <h4>Informação Básica</h4>
                  <div className="detail-item">
                    <span className="label">ID do Serviço:</span>
                    <span className="value">{service.id}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Tipo:</span>
                    <span className="value">{service.type}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Instância:</span>
                    <span className="value">{service.instance}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">URL:</span>
                    <span className="value">{service.url}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Estado:</span>
                    <span 
                      className="value status-badge"
                      style={{ backgroundColor: getStatusColor(service.status) }}
                    >
                      {service.status}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Tempo de Resposta:</span>
                    <span className="value">{service.response_time}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Uptime:</span>
                    <span className="value">{service.uptime || 'Desconhecido'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Última Verificação:</span>
                    <span className="value">{service.last_check || 'Nunca'}</span>
                  </div>
                </div>

                {service.cluster_info && (
                  <div className="detail-section">
                    <h4>Informação do Cluster</h4>
                    <div className="detail-item">
                      <span className="label">Nó:</span>
                      <span className="value">{service.cluster_info.node}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Réplicas:</span>
                      <span className="value">{service.cluster_info.replicas}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Load Balancing:</span>
                      <span className="value">{service.cluster_info.load_balanced ? 'Ativo' : 'Inativo'}</span>
                    </div>
                  </div>
                )}

                {service.replica_set_info && (
                  <div className="detail-section">
                    <h4>Replica Set da Base de Dados</h4>
                    <div className="detail-item">
                      <span className="label">Papel:</span>
                      <span className="value">{service.replica_set_info.role}</span>
                    </div>
                    {service.replica_set_info.replica_set_name && (
                      <div className="detail-item">
                        <span className="label">Nome do Replica Set:</span>
                        <span className="value">{service.replica_set_info.replica_set_name}</span>
                      </div>
                    )}
                    {service.replica_set_info.members_count && (
                      <div className="detail-item">
                        <span className="label">Membros:</span>
                        <span className="value">{service.replica_set_info.members_count}</span>
                      </div>
                    )}
                    {service.replica_set_info.status && (
                      <div className="detail-item">
                        <span className="label">Estado:</span>
                        <span className="value">{service.replica_set_info.status}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="service-metrics-tab">
              {service.metrics ? (
                <div className="metrics-detailed">
                  <div className="metrics-source-info">
                    <h4>Fonte das Métricas</h4>
                    <div className="source-badge-large">
                      {service.metrics.source === 'mongodb_primary' && (
                        <span className="source-indicator mongodb">MongoDB Primary - Dados Reais</span>
                      )}
                      {service.metrics.source === 'mongodb_secondary' && (
                        <span className="source-indicator mongodb">MongoDB Secondary - Dados Reais</span>
                      )}
                      {service.metrics.source === 'prometheus' && (
                        <span className="source-indicator prometheus">Prometheus - Dados Reais</span>
                      )}
                      {service.metrics.source?.includes('simulated') && (
                        <span className="source-indicator simulated">Dados Simulados</span>
                      )}
                      {service.metrics.source?.includes('error') && (
                        <span className="source-indicator error">Erro na Recolha</span>
                      )}
                    </div>
                  </div>

                  <div className="metrics-grid-detailed">
                    {Object.entries(service.metrics)
                      .filter(([key]) => !['source', 'connection_type'].includes(key))
                      .map(([key, value]) => (
                      <div key={key} className="metric-detailed">
                        <div className="metric-label-detailed">
                          {formatMetricLabelDetailed(key)}
                        </div>
                        <div className="metric-value-detailed">
                          {formatMetricValueDetailed(key, value)}
                        </div>
                        <div className="metric-description">
                          {getMetricDescription(key)}
                        </div>
                      </div>
                    ))}
                  </div>

                  {service.database_type === 'mongodb' && (
                    <div className="mongodb-specific-metrics">
                      <h4>Métricas Específicas MongoDB</h4>
                      <div className="mongodb-metrics-grid">
                        {service.metrics.data_size_mb && (
                          <div className="mongodb-metric">
                            <span className="label">Tamanho dos Dados:</span>
                            <span className="value">{service.metrics.data_size_mb} MB</span>
                          </div>
                        )}
                        {service.metrics.collections && (
                          <div className="mongodb-metric">
                            <span className="label">Coleções:</span>
                            <span className="value">{service.metrics.collections}</span>
                          </div>
                        )}
                        {service.metrics.users_count !== undefined && (
                          <div className="mongodb-metric">
                            <span className="label">Utilizadores:</span>
                            <span className="value">{service.metrics.users_count}</span>
                          </div>
                        )}
                        {service.metrics.videos_count !== undefined && (
                          <div className="mongodb-metric">
                            <span className="label">Vídeos:</span>
                            <span className="value">{service.metrics.videos_count}</span>
                          </div>
                        )}
                        {service.metrics.replication_lag_seconds !== undefined && (
                          <div className="mongodb-metric">
                            <span className="label">Lag de Replicação:</span>
                            <span className="value">{service.metrics.replication_lag_seconds}s</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="no-metrics">
                  <p>Sem métricas disponíveis para este serviço.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="service-logs-tab">
              {service.logs && service.logs.length > 0 ? (
                <div className="logs-detailed">
                  <div className="logs-header">
                    <h4>Logs Recentes ({service.logs.length})</h4>
                    <div className="logs-controls">
                      <select className="log-filter">
                        <option value="all">Todos os Níveis</option>
                        <option value="ERROR">Apenas Erros</option>
                        <option value="WARNING">Avisos</option>
                        <option value="INFO">Informação</option>
                      </select>
                    </div>
                  </div>
                  <div className="logs-container-detailed">
                    {service.logs.map((log, index) => (
                      <div key={index} className={`log-entry-detailed log-${log.level.toLowerCase()}`}>
                        <div className="log-meta">
                          <span className="log-timestamp">{log.timestamp}</span>
                          <span className={`log-level level-${log.level.toLowerCase()}`}>
                            {log.level}
                          </span>
                        </div>
                        <div className="log-message-detailed">{log.message}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="no-logs">
                  <p>Sem logs disponíveis para este serviço.</p>
                  <small>Os logs podem não estar configurados ou acessíveis.</small>
                </div>
              )}
            </div>
          )}

          {activeTab === 'advanced' && showAdvanced && (
            <div className="service-advanced-tab">
              <div className="advanced-sections">
                <div className="advanced-section">
                  <h4>Informação Técnica</h4>
                  <div className="technical-info">
                    <div className="tech-item">
                      <span className="label">Fonte da Descoberta:</span>
                      <span className="value">{service.source || 'direct_discovery'}</span>
                    </div>
                    <div className="tech-item">
                      <span className="label">Métricas Automáticas:</span>
                      <span className="value">{service.automatic_metrics_enabled ? 'Ativadas' : 'Desativadas'}</span>
                    </div>
                    {service.version && (
                      <div className="tech-item">
                        <span className="label">Versão:</span>
                        <span className="value">{service.version}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="advanced-section">
                  <h4>Configuração de Rede</h4>
                  <div className="network-info">
                    <div className="network-item">
                      <span className="label">Protocolo:</span>
                      <span className="value">HTTP/1.1</span>
                    </div>
                    <div className="network-item">
                      <span className="label">Porta:</span>
                      <span className="value">{service.instance.split(':')[1] || 'N/A'}</span>
                    </div>
                    <div className="network-item">
                      <span className="label">Timeout:</span>
                      <span className="value">10s</span>
                    </div>
                  </div>
                </div>

                <div className="advanced-section">
                  <h4>Dados Raw</h4>
                  <div className="raw-data">
                    <pre>{JSON.stringify(service, null, 2)}</pre>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        <div className="modal-footer">
          <div className="footer-actions">
            <button 
              className="btn btn-danger"
              onClick={() => onRestart(service.id)}
              disabled={service.status === 'healthy'}
            >
              Reiniciar Serviço
            </button>
            
            <button 
              className="btn btn-secondary"
              onClick={() => {
                const serviceInfo = JSON.stringify(service, null, 2);
                navigator.clipboard.writeText(serviceInfo);
                alert('Informações copiadas para o clipboard');
              }}
            >
              Copiar Info
            </button>

            {service.url && (
              <a 
                href={service.url + '/health'} 
                target="_blank" 
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                Testar Endpoint
              </a>
            )}
          </div>
          
          <button className="btn btn-primary" onClick={onClose}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

export default SystemStatus;