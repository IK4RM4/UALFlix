#!/bin/bash

# Script para escalar serviços no Swarm
echo "📈 Docker Swarm Service Scaling"

if [ $# -eq 0 ]; then
    echo "Uso: $0 <action>"
    echo ""
    echo "Actions disponíveis:"
    echo "  scale-up     - Aumentar réplicas"
    echo "  scale-down   - Diminuir réplicas"
    echo "  auto-scale   - Escalonamento automático baseado em carga"
    echo "  status       - Ver status atual"
    exit 1
fi

ACTION=$1

case $ACTION in
    "scale-up")
        echo "📈 Aumentando réplicas dos serviços..."
        docker service scale ualflix_authentication_service=5
        docker service scale ualflix_catalog_service=5
        docker service scale ualflix_streaming_service=5
        docker service scale ualflix_frontend=3
        docker service scale ualflix_video_processor=3
        echo "✅ Scale-up concluído!"
        ;;
        
    "scale-down")
        echo "📉 Diminuindo réplicas dos serviços..."
        docker service scale ualflix_authentication_service=2
        docker service scale ualflix_catalog_service=2
        docker service scale ualflix_streaming_service=2
        docker service scale ualflix_frontend=1
        docker service scale ualflix_video_processor=1
        echo "✅ Scale-down concluído!"
        ;;
        
    "auto-scale")
        echo "🤖 Escalonamento automático baseado em métricas..."
        
        # Verificar número de nodes disponíveis
        NODE_COUNT=$(docker node ls --filter role=worker --format "{{.ID}}" | wc -l)
        TOTAL_NODES=$(docker node ls --format "{{.ID}}" | wc -l)
        
        echo "Nodes disponíveis: $TOTAL_NODES (Workers: $NODE_COUNT)"
        
        # Escalonamento baseado no número de nodes
        if [ $TOTAL_NODES -ge 3 ]; then
            echo "✅ Cluster com 3+ nodes - Escalonamento completo"
            docker service scale ualflix_authentication_service=3
            docker service scale ualflix_catalog_service=3
            docker service scale ualflix_streaming_service=3
            docker service scale ualflix_frontend=2
            docker service scale ualflix_video_processor=2
        else
            echo "⚠️ Cluster com poucos nodes - Escalonamento conservador"
            docker service scale ualflix_authentication_service=2
            docker service scale ualflix_catalog_service=2
            docker service scale ualflix_streaming_service=2
            docker service scale ualflix_frontend=1
            docker service scale ualflix_video_processor=1
        fi
        
        echo "✅ Auto-scale concluído!"
        ;;
        
    "status")
        echo "📊 Status atual dos serviços:"
        docker service ls
        echo ""
        echo "📍 Distribuição por node:"
        docker stack ps ualflix --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"
        ;;
        
    *)
        echo "❌ Action desconhecida: $ACTION"
        exit 1
        ;;
esac
