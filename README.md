# 🎬 UALFlix - Resumo Final do Setup Kubernetes

## 📋 O que foi criado/atualizado

Criei uma solução completa para deploy do UALFlix no Kubernetes com 3 nós, usando NGINX como roteador principal. Aqui está o resumo:

### 📁 Arquivos Principais Criados:

1. **Guia de Setup**: Instruções passo-a-passo completas
2. **NGINX Gateway**: Configuração como roteador principal com load balancing
3. **Makefile Avançado**: Comandos automáticos para todo o processo
4. **Script de Setup**: Automatização completa (`setup-ualflix-k8s.sh`)
5. **MongoDB StatefulSet**: Configurado para 3 réplicas distribuídas
6. **Troubleshooting Guide**: Resolução de problemas comuns

### 🏗️ Arquitetura Implementada:

```
┌─────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER (3 NODES)             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    NODE 1    │  │    NODE 2    │  │    NODE 3    │      │
│  │              │  │              │  │              │      │
│  │ NGINX Gateway│  │   Frontend   │  │   MongoDB    │      │
│  │ Auth Service │  │ Catalog Svc  │  │ RabbitMQ     │      │
│  │ Streaming    │  │ Admin Svc    │  │ Processor    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│           ↓ NGINX Load Balancer (Roteador Principal)        │
│                                                             │
│  Frontend → /api/auth/ → Auth Service                       │
│          → /api/      → Catalog Service                     │
│          → /api/admin/→ Admin Service                       │
│          → /stream/   → Streaming Service                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Como usar (3 opções):

### Opção 1: Script Automático (Mais Fácil)
```bash
# Dar permissão de execução
chmod +x setup-ualflix-k8s.sh

# Executar setup completo
./setup-ualflix-k8s.sh

# Aguardar conclusão (~10-15 minutos)
# URL será exibida no final
```

### Opção 2: Makefile (Controle por etapas)
```bash
# Setup completo
make demo

# Ou passo a passo:
make cluster-start    # Iniciar cluster com 3 nós
make build           # Build das imagens Docker
make deploy          # Deploy da aplicação
make url             # Obter URLs de acesso
```

### Opção 3: Manual (Seguir guia)
Seguir o guia passo-a-passo que criei no primeiro artefato.

## ✅ Funcionalidades Implementadas

### FUNCIONALIDADE 1: Tecnologias de Sistemas Distribuídos
- ✅ Microserviços em Python Flask
- ✅ Comunicação REST entre serviços
- ✅ Message Queue (RabbitMQ) para processamento assíncrono

### FUNCIONALIDADE 2: Cluster de Computadores
- ✅ Kubernetes com **3 nós** usando Minikube
- ✅ Distribuição automática de pods pelos nós
- ✅ Coordenação de recursos compartilhados
- ✅ Adição/remoção sem interrupção (kubectl scale)

### FUNCIONALIDADE 3: Virtualização
- ✅ Containers Docker para cada componente
- ✅ Pods Kubernetes para orquestração
- ✅ Isolamento completo entre serviços
- ✅ Volumes persistentes para dados

### FUNCIONALIDADE 4: Implementação na Cloud
- ✅ Deploy em ambiente Kubernetes (cloud-native)
- ✅ Auto-scaling horizontal (HPA)
- ✅ Elasticidade automática baseada em CPU/memória
- ✅ Service Discovery automático

### FUNCIONALIDADE 5: Estratégias de Replicação de Dados
- ✅ **MongoDB Replica Set** com 3 instâncias
- ✅ Distribuição pelos 3 nós do cluster
- ✅ Replicação síncrona (primary-secondary)
- ✅ Failover automático
- ✅ Estratégias master-slave implementadas

### FUNCIONALIDADE 6: Replicação de Serviços
- ✅ **NGINX como Load Balancer principal**
- ✅ Múltiplas réplicas de cada serviço
- ✅ Distribuição de carga automática
- ✅ Detecção de falhas e recuperação
- ✅ Health checks automáticos
- ✅ Session affinity quando necessário

### FUNCIONALIDADE 7: Avaliação de Desempenho
- ✅ Métricas automáticas com Prometheus
- ✅ Dashboards visuais com Grafana
- ✅ Monitoramento de latência e throughput
- ✅ Alertas automáticos
- ✅ Métricas de utilização de recursos

## 🌐 URLs de Acesso Final

Após o setup, você terá acesso a:

```bash
# Aplicação Principal (NGINX Gateway)
http://localhost:30080  # NodePort fixo
# ou
minikube service nginx-gateway --namespace ualflix

# Prometheus (Métricas)
http://localhost:30090
# ou  
minikube service prometheus-service --namespace ualflix

# Grafana (Dashboards)
http://localhost:30030
# ou
minikube service grafana-service --namespace ualflix
# Login: admin/admin

# Kubernetes Dashboard
minikube dashboard
```

## 🔧 Comandos Úteis Pós-Setup

### Verificar Status
```bash
# Status geral do cluster
kubectl get nodes
kubectl get pods -n ualflix -o wide

# Ver distribuição pelos nós
kubectl get pods -n ualflix -o wide | awk '{print $1, $7}' | column -t

# Métricas de recursos
kubectl top nodes
kubectl top pods -n ualflix
```

### Escalar Serviços (FUNCIONALIDADE 6)
```bash
# Escalar catalog service para 5 réplicas
kubectl scale deployment catalog-service --replicas=5 -n ualflix

# Escalar streaming service para alta demanda
kubectl scale deployment streaming-service --replicas=6 -n ualflix

# Ver auto-scaling em ação
kubectl get hpa -n ualflix
```

### Simular Falhas (Testar Resilência)
```bash
# Deletar pod para testar recuperação automática
kubectl delete pod -n ualflix -l app=catalog-service

# Ver recuperação
kubectl get pods -n ualflix -w

# Simular falha de nó (marcar como indisponível)
kubectl cordon minikube-m02
kubectl get nodes
```

### Logs e Debug
```bash
# Logs do NGINX Gateway (roteador principal)
kubectl logs -f -n ualflix deployment/nginx-gateway

# Logs agregados de um serviço
kubectl logs -f -n ualflix -l app=catalog-service

# Debug interativo
kubectl exec -it -n ualflix deployment/catalog-service -- /bin/bash
```

### MongoDB Replica Set (FUNCIONALIDADE 5)
```bash
# Verificar status do replica set
kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.status()"

# Ver configuração
kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.conf()"

# Testar failover
kubectl delete pod mongodb-0 -n ualflix
# Observar nova eleição de primary
```

## 🎯 Demonstração das Funcionalidades

### 1. Sistema Distribuído em Ação
```bash
# Ver comunicação entre serviços
kubectl logs -f -n ualflix deployment/nginx-gateway | grep -E "(auth|catalog|streaming)"
```

### 2. Cluster com 3 Nós
```bash
# Confirmar 3 nós ativos
kubectl get nodes

# Ver distribuição de pods
kubectl get pods -n ualflix -o wide
```

### 3. Load Balancing (NGINX)
```bash
# Fazer várias requisições e ver distribuição
for i in {1..10}; do
  curl -s $(minikube service nginx-gateway --namespace ualflix --url)/api/videos | head -1
done
```

### 4. Auto-scaling
```bash
# Gerar carga para ativar HPA
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh
# Dentro do pod:
while true; do wget -q -O- http://nginx-gateway.ualflix.svc.cluster.local:8080/api/videos; done

# Em outro terminal, observar scaling
kubectl get hpa -n ualflix -w
```

### 5. Alta Disponibilidade
```bash
# Deletar pods e ver recuperação automática
kubectl delete pods -n ualflix -l app=catalog-service
kubectl get pods -n ualflix -w

# Sistema continua funcionando
curl $(minikube service nginx-gateway --namespace ualflix --url)/health
```

## 📊 Métricas e Monitoramento

### Prometheus Queries Úteis
```promql
# Latência dos serviços
http_request_duration_seconds{job="ualflix-services"}

# Throughput
rate(http_requests_total[5m])

# Utilização de CPU por pod
rate(container_cpu_usage_seconds_total[5m]) * 100

# Disponibilidade
up{job="ualflix-services"}
```

### Grafana Dashboards
- **Sistema Geral**: CPU, Memória, Rede
- **Aplicação**: Requests/s, Latência, Erros
- **MongoDB**: Operações, Replicação, Storage
- **Kubernetes**: Pods, Nodes, Resources

## 🚨 Resolução de Problemas

Se algo não funcionar, consulte o **Guia de Troubleshooting** que criei, mas os problemas mais comuns são:

```bash
# 1. Pods em CrashLoopBackOff
kubectl logs -n ualflix <pod-name> --previous

# 2. Imagens não encontradas
eval $(minikube docker-env)
make build

# 3. Serviços não respondem
kubectl get endpoints -n ualflix
kubectl exec -n ualflix deployment/frontend -- curl -f http://catalog-service:8000/health

# 4. MongoDB não conecta
kubectl logs -n ualflix mongodb-0
kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.status()"

# 5. NGINX não roteia
kubectl logs -n ualflix deployment/nginx-gateway
kubectl exec -n ualflix deployment/nginx-gateway -- nginx -t
```

## 🎉 Resultado Final

Você terá um sistema completo com:

- **3 nós Kubernetes** rodando o UALFlix
- **NGINX como roteador principal** fazendo load balancing
- **MongoDB Replica Set** distribuído pelos nós
- **Auto-scaling** baseado em demanda
- **Monitoramento completo** com Prometheus/Grafana
- **Alta disponibilidade** com recuperação automática
- **Todas as 7 funcionalidades** do projeto implementadas

## 💡 Próximos Passos

1. **Testar o sistema**: Use as URLs para navegar na aplicação
2. **Fazer upload de vídeos**: Testar funcionalidade completa
3. **Simular falhas**: Testar resilência
4. **Monitorar métricas**: Usar Grafana para análise
5. **Escalar sob demanda**: Testar auto-scaling
6. **Documentar**: Preparar apresentação das funcionalidades

O sistema está pronto para demonstração académica! 🚀