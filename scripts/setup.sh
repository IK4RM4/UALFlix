#!/bin/bash

# UALFlix Setup - Sistema de Métricas Automáticas
# Implementa funcionalidades 2, 5, 6, 7 do PDF

echo "🎬 UALFlix - Setup Completo"
echo "=========================="

# Verificações básicas
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose não encontrado"
    exit 1
fi

echo "✅ Verificações passaram"

# Criar pastas necessárias
echo "📁 Criando estrutura..."
mkdir -p haproxy monitoring/grafana/dashboards

# Backup de ficheiros existentes
echo "💾 Fazendo backup..."
[ -f "docker-compose.yml" ] && cp docker-compose.yml docker-compose.yml.backup
[ -f "admin_service/app.py" ] && cp admin_service/app.py admin_service/app.py.backup

# Parar serviços
echo "🛑 Parando serviços..."
docker-compose down 2>/dev/null

# Build do admin service (principal alteração)
echo "🔨 Building admin service..."
docker-compose build admin_service

# Iniciar serviços básicos
echo "🚀 Iniciando UALFlix..."
docker-compose up -d

# Aguardar inicialização
echo "⏳ Aguardando inicialização..."
sleep 30

# Verificar status
echo "📊 Status dos serviços:"
docker-compose ps

echo ""
echo "✅ Setup concluído!"
echo ""
echo "🌐 URLs disponíveis:"
echo "   - UALFlix: http://localhost:8080"
echo "   - Prometheus: http://localhost:9090"
echo "   - Grafana: http://localhost:4000 (admin/admin)"
echo "   - RabbitMQ: http://localhost:15672 (ualflix/ualflix_password)"
echo ""
echo "🔧 Admin com métricas automáticas:"
echo "   - http://localhost:8080 (login: admin/admin)"
echo "   - Tab 'Administração' para ver métricas"
echo ""
echo "📊 Funcionalidades implementadas:"
echo "   ✅ Funcionalidade 2: Cluster de Computadores"
echo "   ✅ Funcionalidade 5: Replicação de Dados"
echo "   ✅ Funcionalidade 6: Replicação de Serviços"
echo "   ✅ Funcionalidade 7: Avaliação de Desempenho"