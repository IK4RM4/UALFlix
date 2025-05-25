UALFlix - Sistema de Métricas Automáticas
Sistema de streaming com métricas automáticas que implementa todas as funcionalidades exigidas no PDF.

🎯 Funcionalidades Implementadas
✅ Funcionalidade 2: Cluster de Computadores
✅ Funcionalidade 5: Replicação de Dados
✅ Funcionalidade 6: Replicação de Serviços
✅ Funcionalidade 7: Avaliação de Desempenho (AUTOMÁTICA)

📋 Alterações Principais
1. admin_service/app.py
Sistema automático de coleta de métricas
Análise de tendências em tempo real
Métricas de latência, throughput e recursos
Fallback automático se Prometheus falhar
2. admin_service/requirements.txt
Adicionadas dependências: psutil, prometheus-client
3. monitoring/prometheus.yml
Configuração otimizada para métricas automáticas
Scraping frequente (5s) para dados em tempo real
4. monitoring/alert.rules
Alertas automáticos baseados em métricas
Detecção de anomalias de performance
🚀 Como Usar
Setup Rápido
bash
# Dar permissões ao script
chmod +x setup.sh

# Executar setup
./setup.sh
Setup Manual
bash
# Parar serviços
docker-compose down

# Build do admin service
docker-compose build admin_service

# Iniciar tudo
docker-compose up -d
🌐 URLs Importantes
UALFlix: http://localhost:8080
Prometheus: http://localhost:9090
Grafana: http://localhost:4000 (admin/admin)
RabbitMQ: http://localhost:15672 (ualflix/ualflix_password)
📊 Como Ver as Métricas
Aceder a http://localhost:8080
Registar utilizador "admin" com password "admin"
Ir ao tab "Administração"
Ver métricas automáticas em tempo real
Endpoints de Métricas Automáticas
bash
# Métricas automáticas completas
curl http://localhost:8002/api/admin/metrics/automatic

# Análise de tendências
curl http://localhost:8002/api/admin/performance/trends

# Status de serviços com métricas
curl http://localhost:8002/api/admin/services
🔧 Funcionalidades Técnicas
Funcionalidade 7: Avaliação de Desempenho
Latência: Medição automática de tempo de resposta
Throughput: Contagem automática de requests/segundo
Recursos: Monitorização de CPU, memória, disco
Análise: Tendências automáticas e alertas
Funcionalidade 2: Cluster de Computadores
Service Discovery: Descoberta automática via Prometheus
Coordenação: Métricas de tempo de coordenação
Nós: Contagem automática de nós saudáveis
Funcionalidades 5 e 6: Replicação
Réplicas: Simulação de múltiplas instâncias
Load Balancer: HAProxy configurado
Status: Monitorização automática de réplicas
📈 Métricas Automáticas Disponíveis
O sistema coleta automaticamente:

ualflix_system_request_duration_seconds - Latência
ualflix_system_requests_total - Throughput
ualflix_system_cpu_percent - CPU por serviço
ualflix_system_memory_percent - Memória por serviço
ualflix_cluster_nodes_total - Nós do cluster
ualflix_replica_status - Status das réplicas
ualflix_system_availability_percent - Disponibilidade
🚨 Alertas Automáticos
O sistema gera alertas automáticos para:

CPU > 80%
Memória > 85%
Latência > 2s
Disponibilidade < 90%
Réplicas offline
📝 Logs
Ver logs em tempo real:

bash
# Admin service (métricas)
docker-compose logs -f admin_service

# Prometheus
docker-compose logs -f prometheus

# Todos os serviços
docker-compose logs -f
🔍 Troubleshooting
Se métricas não aparecem:
bash
# Verificar se admin_service está up
curl http://localhost:8002/health

# Verificar Prometheus
curl http://localhost:9090/-/healthy

# Restart se necessário
docker-compose restart admin_service prometheus
Se Prometheus não liga:
bash
# Verificar configuração
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml

# Ver logs
docker-compose logs prometheus
✨ Destaques
100% Automático: Todas as métricas são coletadas automaticamente
Tempo Real: Dashboards atualizam a cada 5-15 segundos
Fallback: Sistema funciona mesmo se Prometheus falhar
Análise: Tendências automáticas com recomendações
PDF Compliant: Implementa todas as funcionalidades exigidas
