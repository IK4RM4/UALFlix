#!/bin/bash

# Script de monitoramento do cluster Swarm
echo "📊 Monitor Docker Swarm - UALFlix Cluster"
echo "========================================"

while true; do
    clear
    echo "📊 DOCKER SWARM CLUSTER STATUS - $(date)"
    echo "========================================"
    
    echo ""
    echo "🖥️ NODES:"
    docker node ls
    
    echo ""
    echo "📋 SERVICES:"
    docker service ls
    
    echo ""
    echo "📊 TASKS DISTRIBUTION:"
    docker stack ps ualflix --format "table {{.ID}}\t{{.Name}}\t{{.Node}}\t{{.CurrentState}}"
    
    echo ""
    echo "💾 VOLUMES:"
    docker volume ls | grep ualflix
    
    echo ""
    echo "🌐 NETWORKS:"
    docker network ls | grep ualflix
    
    echo ""
    echo "📈 RESOURCE USAGE (estimado):"
    echo "CPU Nodes: $(docker node ls --format '{{.Hostname}}' | wc -l) nodes"
    echo "Services: $(docker service ls --format '{{.Name}}' | wc -l) services"
    echo "Replicas: $(docker service ls --format '{{.Replicas}}' | grep -o '[0-9]*/' | sed 's|/||' | awk '{sum+=$1} END {print sum}') replicas"
    
    echo ""
    echo "🔄 Atualizando em 30 segundos... (Ctrl+C para sair)"
    sleep 30
done
