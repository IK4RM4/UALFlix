# UALFlix - Projeto de Arquitetura Avançada de Sistemas

## Resumo do Projeto

O UALFlix é uma plataforma distribuída de streaming de vídeo que implementa conceitos avançados de arquitetura de sistemas, incluindo sistemas distribuídos, clusters de computadores, virtualização, computação em nuvem e estratégias de replicação de dados. Este projeto demonstra as sete funcionalidades obrigatórias definidas nos requisitos da disciplina de Arquitetura Avançada de Sistemas.

## Arquitetura do Sistema

### Diagrama da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLUSTER KUBERNETES                       │
│                          (3 Nós)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    NÓ 1      │  │    NÓ 2      │  │    NÓ 3      │         │
│  │              │  │              │  │              │         │
│  │ Frontend     │  │ Auth Service │  │ MongoDB      │         │
│  │ NGINX LB     │  │ Catalog Svc  │  │ Primary      │         │
│  │ Prometheus   │  │ Admin Svc    │  │              │         │
│  └──────────────┘  │ Streaming    │  │ MongoDB      │         │
│                    │ Video Proc   │  │ Secondary    │         │
│                    │ Grafana      │  │              │         │
│                    │ RabbitMQ     │  │ MongoDB      │         │
│                    └──────────────┘  │ Arbiter      │         │
│                                      └──────────────┘         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    FLUXO DE DADOS                               │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────────┐    HTTP     ┌─────────────┐
    │  Utilizador │ ────────────▶│   NGINX     │
    │   (Browser) │◀────────────│Load Balancer│
    └─────────────┘              └─────────────┘
                                        │
                  ┌─────────────────────┼─────────────────────┐
                  │                     │                     │
                  ▼                     ▼                     ▼
          ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
          │  Frontend   │       │Auth Service │       │ Admin Panel │
          │  (React)    │       │  (Flask)    │       │  (Flask)    │
          └─────────────┘       └─────────────┘       └─────────────┘
                  │                     │                     │
                  │                     │                     │
                  └─────────────────────┼─────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
            ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
            │ Catalog Svc │     │Streaming Svc│     │Video Proc   │
            │  (Upload)   │     │ (Delivery)  │     │(Processing) │
            └─────────────┘     └─────────────┘     └─────────────┘
                    │                   │                   ▲
                    │                   │                   │
                    ▼                   ▼                   │
            ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
            │  RabbitMQ   │ ────▶│Video Storage│     │   Queue     │
            │ (Mensagens) │      │ (Ficheiros) │     │ Processing  │
            └─────────────┘     └─────────────┘     └─────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────────────┐
        │            MONGODB REPLICA SET                 │
        │                                               │
        │  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
        │  │Primary  │◀─▶│Secondary│  │ Arbiter │       │
        │  │(Escrita)│  │(Leitura)│  │(Eleição)│       │
        │  └─────────┘  └─────────┘  └─────────┘       │
        └───────────────────────────────────────────────┘
                    ▲
                    │ Métricas
                    ▼
        ┌───────────────────────────────────────────────┐
        │         MONITORIZAÇÃO E MÉTRICAS               │
        │                                               │
        │  ┌─────────────┐      ┌─────────────┐         │
        │  │ Prometheus  │ ────▶│  Grafana    │         │
        │  │ (Coleta)    │      │(Dashboards) │         │
        │  └─────────────┘      └─────────────┘         │
        └───────────────────────────────────────────────┘
```

### Componentes Principais

#### Serviços da Aplicação
- **Serviço de Autenticação**: Gestão de utilizadores e sessões
- **Serviço de Catálogo**: Gestão de metadados de vídeos e upload
- **Serviço de Streaming**: Entrega de conteúdo com suporte a range requests
- **Serviço de Administração**: Monitorização e gestão do sistema
- **Processador de Vídeo**: Processamento assíncrono e geração de thumbnails

#### Componentes de Infraestrutura
- **MongoDB Replica Set**: Configuração Primary-Secondary-Arbiter para replicação
- **RabbitMQ**: Fila de mensagens para processamento assíncrono
- **NGINX**: Balanceador de carga e proxy reverso
- **Prometheus**: Recolha de métricas e monitorização
- **Grafana**: Visualização de performance e dashboards

## Funcionalidades Implementadas

### Funcionalidade 1: Tecnologias de Implementação de Sistemas Distribuídos
O sistema implementa uma arquitetura de microserviços com comunicação REST API entre componentes. Os serviços são desenhados para independência e escalabilidade, utilizando filas de mensagens assíncronas para processamento desacoplado.

**Detalhes de Implementação:**
- Microserviços Python Flask com endpoints REST
- Fila de mensagens RabbitMQ para workflow de processamento de vídeo
- Service discovery através de redes de contentores
- Comunicação inter-serviços com gestão de timeouts e retries

### Funcionalidade 2: Implementação de Cluster de Computadores
A aplicação executa num cluster Kubernetes com suporte para deployment multi-nó. A gestão de recursos e coordenação de nós é gerida através da orquestração do Kubernetes.

**Detalhes de Implementação:**
- Cluster Kubernetes com número configurável de nós
- Distribuição de pods pelos nós do cluster
- Failover automático e gestão de nós
- Alocação de recursos e gestão de restrições

### Funcionalidade 3: Virtualização de Computadores
Todos os componentes são containerizados usando Docker, proporcionando isolamento e ambientes de deployment consistentes em diferentes plataformas.

**Detalhes de Implementação:**
- Contentores Docker para cada componente de serviço
- Builds multi-stage para tamanhos de imagem otimizados
- Volume mounting para armazenamento persistente de dados
- Health checks de contentores e políticas de restart

### Funcionalidade 4: Implementação na Cloud
O sistema é desenhado para deployment cloud-native com suporte para escalamento horizontal e integração com fornecedores de cloud.

**Detalhes de Implementação:**
- Manifestos de deployment nativos do Kubernetes
- Configuração de Horizontal Pod Autoscaler (HPA)
- Capacidades de integração com armazenamento cloud
- Gestão de configuração específica por ambiente

### Funcionalidade 5: Estratégias de Replicação de Dados
A implementação do replica set MongoDB proporciona redundância de dados e capacidades de escalamento de leitura.

**Detalhes de Implementação:**
- Configuração MongoDB Primary-Secondary-Arbiter
- Failover automático com mecanismos de eleição
- Roteamento de read preference para distribuição de carga
- Monitorização de lag de replicação e alertas

### Funcionalidade 6: Replicação de Serviços
Balanceamento de carga e redundância de serviços garantem alta disponibilidade e tolerância a falhas.

**Detalhes de Implementação:**
- Balanceador de carga NGINX com múltiplas instâncias backend
- Service mesh do Kubernetes para comunicação interna
- Endpoints de health check para monitorização de serviços
- Substituição automática de pods em caso de falha

### Funcionalidade 7: Avaliação de Desempenho
Monitorização abrangente e recolha de métricas proporcionam insights sobre performance e fiabilidade do sistema.

**Detalhes de Implementação:**
- Recolha de métricas Prometheus de todos os serviços
- Dashboards Grafana para visualização
- Métricas de performance personalizadas e regras de alertas
- Monitorização de saúde do sistema em tempo real

## Requisitos do Sistema

### Requisitos Mínimos
- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM
- 20GB espaço livre em disco
- Linux, macOS, ou Windows com WSL2

### Recomendado para Produção
- Cluster Kubernetes com 3+ nós
- 16GB RAM por nó
- Armazenamento SSD para base de dados
- Balanceador de carga para acesso externo

## Instalação e Deployment

### Início Rápido com Docker Compose

1. Clonar o repositório:
```bash
git clone <repository-url>
cd ualflix
```

2. Iniciar todos os serviços:
```bash
docker-compose up -d
```

3. Aguardar inicialização dos serviços (aproximadamente 2-3 minutos):
```bash
docker-compose logs -f mongodb_replica_init
```

4. Aceder à aplicação:
- Aplicação principal: http://localhost:8080
- Dashboard admin: http://localhost:8080 (login como admin)
- Métricas Prometheus: http://localhost:9090
- Dashboards Grafana: http://localhost:3001 (admin/admin)

### Deployment Kubernetes

Para deployment de produção com funcionalidade completa de cluster:

1. Verificar disponibilidade do cluster Kubernetes:
```bash
kubectl cluster-info
```

2. Usar o Makefile fornecido para deployment automatizado:
```bash
# Iniciar cluster de 3 nós com Minikube
make cluster-start

# Build e deploy de todos os serviços
make build
make deploy

# Obter URLs de acesso
make url
```

3. Deployment manual alternativo:
```bash
# Aplicar todos os manifestos Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/database/
kubectl apply -f k8s/messaging/
kubectl apply -f k8s/services/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress/
kubectl apply -f k8s/monitoring/
```

## Configuração

### Variáveis de Ambiente

O sistema suporta configuração através de variáveis de ambiente:

```bash
# Configuração da Base de Dados
MONGODB_CONNECTION_STRING=mongodb://ualflix_db_primary:27017,ualflix_db_secondary:27017/ualflix?replicaSet=ualflix-replica-set
MONGODB_DATABASE=ualflix
MONGODB_REPLICA_SET=ualflix-replica-set

# Configuração da Fila
QUEUE_HOST=queue_service
QUEUE_USER=ualflix
QUEUE_PASSWORD=ualflix_password

# Segurança
SECRET_KEY=your-secret-key-here

# URLs dos Serviços
AUTH_SERVICE_URL=http://authentication_service:8000
```

### Limites de Recursos

As alocações de recursos padrão podem ser ajustadas nos manifestos Kubernetes:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## Guia de Utilização

### Operações de Utilizador

1. **Registo de Utilizador**: Criar novas contas através da interface web
2. **Upload de Vídeo**: Utilizadores autenticados podem fazer upload de ficheiros até 1GB
3. **Streaming de Vídeo**: Reproduzir vídeos com suporte a download progressivo
4. **Gestão de Vídeos**: Utilizadores podem visualizar e gerir o seu conteúdo

### Operações Administrativas

1. **Monitorização do Sistema**: Aceder a métricas em tempo real através do painel admin
2. **Gestão de Serviços**: Monitorizar saúde dos serviços e reiniciar serviços falhados
3. **Administração da Base de Dados**: Visualizar estado do replica set MongoDB e métricas
4. **Análise de Performance**: Usar dashboards Grafana para insights detalhados

### Endpoints da API

#### Serviço de Autenticação (Porta 8000)
```
POST /register - Registo de utilizador
POST /login - Autenticação de utilizador
POST /validate - Validação de token
POST /logout - Terminação de sessão
GET /health - Verificação de saúde do serviço
```

#### Serviço de Catálogo (Porta 8000)
```
GET /videos - Listar todos os vídeos
GET /videos/{id} - Obter detalhes de vídeo específico
POST /upload - Upload de novo vídeo
GET /my-videos - Listar vídeos do utilizador
GET /health - Verificação de saúde do serviço
```

#### Serviço de Streaming (Porta 8001)
```
GET /stream/{filename} - Stream de conteúdo de vídeo
GET /download/{filename} - Download de ficheiro de vídeo
GET /info/{filename} - Obter informações do vídeo
GET /list - Listar vídeos disponíveis
GET /health - Verificação de saúde do serviço
```

#### Serviço de Administração (Porta 8002)
```
GET /api/admin/services - Obter estado dos serviços
GET /api/admin/metrics/summary - Obter métricas do sistema
GET /api/admin/metrics/mongodb - Obter métricas da base de dados
GET /health - Verificação de saúde do serviço
```

## Monitorização e Métricas

### Métricas Prometheus

O sistema expõe várias métricas para monitorização:

- **Saúde dos Serviços**: `up{job="service_name"}`
- **Taxa de Requisições**: `http_requests_total`
- **Tempo de Resposta**: `http_request_duration_seconds`
- **Taxa de Erro**: `http_requests_total{status=~"4..|5.."}`
- **Métricas da Base de Dados**: `ualflix_mongodb_*`
- **Processamento de Vídeo**: `videos_processed_total`, `videos_failed_total`
- **Recursos do Sistema**: `ualflix_system_cpu_percent`, `ualflix_system_memory_percent`

### Dashboards Grafana

Dashboards pré-configurados proporcionam visualização para:

- Visão geral do sistema e saúde dos serviços
- Análise de taxa de requisições e tempo de resposta
- Monitorização de taxa de erro
- Performance da base de dados e estado da replicação
- Tendências de utilização de recursos
- Métricas de processamento de vídeo

### Gestão de Logs

Os logs da aplicação estão disponíveis através do Docker/Kubernetes:

```bash
# Logs do Docker Compose
docker-compose logs -f [service_name]

# Logs do Kubernetes
kubectl logs -f deployment/[service_name] -n ualflix
```

## Resolução de Problemas

### Problemas Comuns

#### Inicialização do MongoDB Replica Set
Se o replica set falhar ao inicializar:
```bash
# Verificar estado do replica set
docker-compose exec ualflix_db_primary mongosh --eval "rs.status()"

# Reinicializar se necessário
docker-compose restart mongodb_replica_init
```

#### Problemas de Comunicação entre Serviços
Verificar conectividade dos serviços:
```bash
# Testar endpoints dos serviços
curl http://localhost:8080/api/auth/health
curl http://localhost:8080/api/health

# Verificar redes de contentores
docker network ls
docker network inspect ualflix_ualflix_net
```

#### Problemas de Pods no Kubernetes
Diagnosticar problemas de pods:
```bash
# Verificar estado dos pods
kubectl get pods -n ualflix

# Ver logs dos pods
kubectl logs [pod-name] -n ualflix

# Descrever pod para eventos
kubectl describe pod [pod-name] -n ualflix
```

#### Problemas de Performance
Monitorizar recursos do sistema:
```bash
# Verificar utilização de recursos
kubectl top nodes
kubectl top pods -n ualflix

# Escalar serviços se necessário
kubectl scale deployment [service-name] --replicas=3 -n ualflix
```

## Desenvolvimento

### Estrutura do Projeto

```
ualflix/
├── authentication_service/     # Microserviço de autenticação
├── catalog_service/           # Gestão do catálogo de vídeos
├── streaming_service/         # Streaming e entrega de vídeos
├── admin_service/            # Administração e monitorização
├── video_processor/          # Processamento assíncrono de vídeo
├── frontend/                 # Aplicação web React
├── k8s/                     # Manifestos de deployment Kubernetes
├── monitoring/              # Configuração Prometheus e Grafana
├── nginx/                   # Configuração do balanceador de carga
├── mongodb-setup/           # Scripts de inicialização da BD
├── docker-compose.yml       # Setup do ambiente de desenvolvimento
├── Makefile                # Comandos de deployment automatizado
└── README.md               # Esta documentação
```

### Workflow de Desenvolvimento

1. **Desenvolvimento Local**: Usar Docker Compose para iteração rápida
2. **Testes**: Testes de serviços individuais com contentores isolados
3. **Integração**: Testes completos do sistema com todos os serviços
4. **Deployment**: Deployment Kubernetes para ambiente tipo produção

### Contribuição

1. Seguir a estrutura de código existente e convenções de nomenclatura
2. Adicionar health checks e métricas apropriadas aos novos serviços
3. Atualizar manifestos Kubernetes para novos componentes
4. Documentar alterações de configuração e modificações da API

## Considerações de Segurança

### Autenticação e Autorização
- Autenticação baseada em sessões com geração segura de tokens
- Hashing de passwords usando algoritmos padrão da indústria
- Separação de papéis admin para funções de gestão do sistema

### Segurança de Rede
- Comunicação interna entre serviços através de redes privadas
- Acesso externo através de proxy reverso com rate limiting
- Terminação TLS ao nível do balanceador de carga (configurável)

### Proteção de Dados
- Acesso à base de dados restrito aos serviços da aplicação
- Validação de upload de ficheiros e restrições de tamanho
- Configuração sensível através de secrets do Kubernetes

## Otimização de Performance

### Otimização da Base de Dados
- Operações de leitura distribuídas pelos membros do replica set
- Otimização de índices para padrões de query comuns
- Connection pooling para utilização eficiente de recursos

### Estratégia de Caching
- Caching ao nível da aplicação para dados frequentemente acedidos
- Capacidades de integração CDN para entrega de conteúdo de vídeo
- Headers de cache do browser para assets estáticos

### Estratégias de Escalamento
- Auto-scaling horizontal de pods baseado em utilização de CPU e memória
- Read replicas da base de dados para performance de leitura melhorada
- Escalamento da fila de mensagens para workload de processamento de vídeo
