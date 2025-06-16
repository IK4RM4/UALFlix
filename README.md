# UALFlix - Plataforma de Streaming Distribuída

## Resumo do Projeto
UALFlix é uma plataforma distribuída de streaming de vídeo baseada em microserviços, com monitorização, replicação e alta disponibilidade usando Docker Compose.

## Componentes Principais
- **Serviço de Autenticação** (porta 8000)
- **Serviço de Catálogo** (porta 8000)
- **Serviço de Streaming** (porta 8001)
- **Serviço de Administração** (porta 8002)
- **Processador de Vídeo**
- **MongoDB Replica Set**
- **RabbitMQ**
- **NGINX** (porta 8080)
- **Prometheus** (porta 9090)
- **Grafana** (porta 3001)

## Arquitetura do Sistema

### Diagrama da Arquitetura (Objetivo)

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
        │         MONITORIZAÇÃO E MÉTRICAS               
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

## RabbitMQ

O RabbitMQ é utilizado como sistema de mensageria para comunicação assíncrona entre microserviços, **exclusivamente para o processamento de vídeos** .

- **Não é utilizado para registo/login/autenticação** — essas operações são feitas diretamente via REST API.

- **Painel de Gestão:**  
  http://localhost:15672

- **Credenciais padrão:**  
  - **User:** `ualflix`  
  - **Password:** `ualflix_password`

- **Porta AMQP (para ligação dos serviços):**  
  - 5672

- **Como aceder ao painel:**  
  Basta abrir o browser e ir a [http://localhost:15672] e fazer login com as credenciais acima.

- **Configuração no docker-compose.yml:**  
  O serviço `queue_service` usa estas credenciais e está disponível para todos os microserviços via rede interna Docker.

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
- Linux, macOS ou Windows (WSL2 recomendado)

## Instalação e Uso Rápido

1. **Clonar o repositório:**
```bash
git clone <repository-url>
cd UALFlix
```

2. **Subir todos os serviços:**
```bash
make up
```

3. **Ver logs de inicialização:**
```bash
make logs
```

4. **Ver estado dos serviços:**
```bash
make ps
```

5. **Aceder à aplicação:**
- App principal: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- RabbitMQ: http://localhost:15672 (ualflix/ualflix_password)


## Comandos Úteis (Makefile)
- `make up` — Sobe todos os serviços
- `make down` — Para e remove todos os serviços
- `make ps` — Lista o estado dos containers
- `make logs` — Mostra logs em tempo real
- `make restart` — Reinicia todos os serviços
- `make build` — Faz build das imagens
- `make stop` — Para os serviços
- `make start` — Inicia serviços parados
- `make pull` — Faz pull das imagens
- `make rm` — Remove containers parados

## Monitorização
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
  - Dashboards automáticos para saúde dos serviços, requisições, erros e uso de recursos

## Troubleshooting
- **Verificar logs:**
  ```bash
  make logs
  ```
- **Reiniciar serviço específico:**
  ```bash
  docker-compose restart <service_name>
  ```
- **Verificar estado do MongoDB Replica Set:**
  ```bash
  docker-compose exec ualflix_db_primary mongosh --eval "rs.status()"
  ```

## Estrutura do Projeto
```
UALFlix/
├── authentication_service/
├── catalog_service/
├── streaming_service/
├── admin_service/
├── video_processor/
├── frontend/
├── monitoring/
├── nginx/
├── mongodb-setup/
├── docker-compose.yml
├── Makefile
└── README.md
```

## Notas
- Para ambiente de produção, recomenda-se usar Kubernetes (manifestos disponíveis em `/Tentativa_k8s`), mas o fluxo principal para testes/desenvolvimento é via Docker Compose já que kubernetes e docker-swarm nao foi implementado.
- Para personalizar variáveis de ambiente, edite o `docker-compose.yml`.

