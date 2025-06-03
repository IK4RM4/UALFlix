#!/bin/bash
# scripts/deploy_to_aws.sh
# FUNCIONALIDADE 4: IMPLEMENTACAO NA CLOUD - Deploy Real na AWS
# 
# Este script implementa deploy completo do UALFlix na AWS usando:
# - EKS (Elastic Kubernetes Service) para orquestracao
# - ECR (Elastic Container Registry) para imagens Docker
# - RDS MongoDB Atlas para base de dados cloud
# - ALB (Application Load Balancer) para load balancing
# - Auto Scaling Groups para elasticidade
# - CloudWatch para monitoramento

set -e  # Parar em caso de erro

# =====================================================================
# CONFIGURACOES E VARIAVEIS
# =====================================================================

# Configuracoes AWS
AWS_REGION="${AWS_REGION:-eu-west-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
CLUSTER_NAME="${CLUSTER_NAME:-ualflix-eks-cluster}"
ECR_REPOSITORY_PREFIX="${ECR_REPOSITORY_PREFIX:-ualflix}"

# Configuracoes do projeto
PROJECT_NAME="ualflix"
NAMESPACE="ualflix"
DOMAIN_NAME="${DOMAIN_NAME:-ualflix.example.com}"

# Configuracoes EKS
EKS_NODE_TYPE="${EKS_NODE_TYPE:-t3.medium}"
EKS_MIN_NODES="${EKS_MIN_NODES:-2}"
EKS_MAX_NODES="${EKS_MAX_NODES:-10}"
EKS_DESIRED_NODES="${EKS_DESIRED_NODES:-3}"

# Lista de servicos para build e deploy
SERVICES=(
    "frontend"
    "authentication_service" 
    "catalog_service"
    "streaming_service"
    "admin_service"
    "video_processor"
)

# =====================================================================
# FUNCOES UTILITARIAS
# =====================================================================

print_header() {
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

print_step() {
    echo "[STEP] $1"
}

print_info() {
    echo "[INFO] $1"
}

print_error() {
    echo "[ERROR] $1"
}

print_success() {
    echo "[SUCCESS] $1"
}

check_prerequisites() {
    print_step "Verificando pre-requisitos..."
    
    # Verificar AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI nao encontrado. Instale: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    # Verificar eksctl
    if ! command -v eksctl &> /dev/null; then
        print_error "eksctl nao encontrado. Instale: https://eksctl.io/"
        exit 1
    fi
    
    # Verificar kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl nao encontrado. Instale: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker nao encontrado. Instale: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Verificar autenticacao AWS
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS nao autenticado. Execute: aws configure"
        exit 1
    fi
    
    # Obter Account ID automaticamente
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        print_info "AWS Account ID detectado: $AWS_ACCOUNT_ID"
    fi
    
    print_success "Pre-requisitos verificados com sucesso!"
}

# =====================================================================
# FUNCAO 1: CRIAR REPOSITORIOS ECR
# =====================================================================

create_ecr_repositories() {
    print_step "Criando repositorios ECR..."
    
    for service in "${SERVICES[@]}"; do
        repo_name="${ECR_REPOSITORY_PREFIX}/${service}"
        
        print_info "Criando repositorio: $repo_name"
        
        # Criar repositorio se nao existir
        if ! aws ecr describe-repositories --repository-names "$repo_name" --region "$AWS_REGION" &> /dev/null; then
            aws ecr create-repository \
                --repository-name "$repo_name" \
                --region "$AWS_REGION" \
                --image-scanning-configuration scanOnPush=true \
                --encryption-configuration encryptionType=AES256
            
            print_success "Repositorio $repo_name criado"
        else
            print_info "Repositorio $repo_name ja existe"
        fi
        
        # Configurar politica de lifecycle
        aws ecr put-lifecycle-policy \
            --repository-name "$repo_name" \
            --region "$AWS_REGION" \
            --lifecycle-policy-text '{
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Keep only 10 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
                        },
                        "action": {
                            "type": "expire"
                        }
                    }
                ]
            }'
    done
    
    print_success "Repositorios ECR criados com sucesso!"
}

# =====================================================================
# FUNCAO 2: BUILD E PUSH DAS IMAGENS
# =====================================================================

build_and_push_images() {
    print_step "Building e pushing imagens Docker..."
    
    # Login no ECR
    print_info "Fazendo login no ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    for service in "${SERVICES[@]}"; do
        print_info "Building imagem para $service..."
        
        # Nome da imagem
        image_name="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_PREFIX}/${service}:latest"
        
        # Build da imagem
        docker build -t "$image_name" "./${service}/"
        
        # Push da imagem
        print_info "Pushing $service para ECR..."
        docker push "$image_name"
        
        print_success "Imagem $service enviada para ECR"
    done
    
    print_success "Todas as imagens enviadas para ECR!"
}

# =====================================================================
# FUNCAO 3: CRIAR CLUSTER EKS
# =====================================================================

create_eks_cluster() {
    print_step "Criando cluster EKS..."
    
    # Verificar se cluster ja existe
    if eksctl get cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_info "Cluster $CLUSTER_NAME ja existe"
        return 0
    fi
    
    print_info "Criando cluster EKS: $CLUSTER_NAME"
    
    # Criar arquivo de configuracao EKS
    cat > eks-cluster-config.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: ${CLUSTER_NAME}
  region: ${AWS_REGION}
  version: "1.28"

# FUNCIONALIDADE 2: CLUSTER DE COMPUTADORES - 3 nos
nodeGroups:
  - name: ualflix-nodes
    instanceType: ${EKS_NODE_TYPE}
    minSize: ${EKS_MIN_NODES}
    maxSize: ${EKS_MAX_NODES}
    desiredCapacity: ${EKS_DESIRED_NODES}
    volumeSize: 20
    volumeType: gp3
    
    # FUNCIONALIDADE 4: CLOUD - Auto-scaling
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        ebs: true
        efs: true
        albIngress: true
    
    # Labels para distribuicao de pods
    labels:
      role: worker
      environment: production
    
    # Taints para controle de scheduling
    taints:
      - key: ualflix.com/dedicated
        value: "true"
        effect: NoSchedule

# FUNCIONALIDADE 7: MONITORING - CloudWatch
cloudWatch:
  clusterLogging:
    enable: true
    logTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]

# Add-ons necessarios
addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest

# FUNCIONALIDADE 4: CLOUD - Configuracoes avancadas
managedNodeGroups:
  - name: ualflix-managed-nodes
    instanceTypes: ["${EKS_NODE_TYPE}"]
    minSize: ${EKS_MIN_NODES}
    maxSize: ${EKS_MAX_NODES}
    desiredCapacity: ${EKS_DESIRED_NODES}
    
    # FUNCIONALIDADE 2: Distribuicao multi-AZ
    availabilityZones: ["${AWS_REGION}a", "${AWS_REGION}b", "${AWS_REGION}c"]
    
    # Volume configuration
    volumeSize: 20
    volumeType: gp3
    volumeEncrypted: true
    
    # Security
    privateNetworking: true
    
    # Auto-scaling policies
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        albIngress: true
EOF
    
    # Criar cluster
    eksctl create cluster -f eks-cluster-config.yaml
    
    # Configurar kubectl
    aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME"
    
    print_success "Cluster EKS criado com sucesso!"
}

# =====================================================================
# FUNCAO 4: INSTALAR ADDONS DO CLUSTER
# =====================================================================

install_cluster_addons() {
    print_step "Instalando addons do cluster..."
    
    # AWS Load Balancer Controller (FUNCIONALIDADE 6: Load Balancing)
    print_info "Instalando AWS Load Balancer Controller..."
    
    # Criar service account
    eksctl create iamserviceaccount \
        --cluster="$CLUSTER_NAME" \
        --namespace=kube-system \
        --name=aws-load-balancer-controller \
        --role-name="${CLUSTER_NAME}-AWSLoadBalancerControllerRole" \
        --attach-policy-arn=arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess \
        --approve \
        --region="$AWS_REGION"
    
    # Instalar via Helm
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName="$CLUSTER_NAME" \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller \
        --set region="$AWS_REGION" \
        --set vpcId=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --query "cluster.resourcesVpcConfig.vpcId" --output text)
    
    # Cluster Autoscaler (FUNCIONALIDADE 4: Elasticidade)
    print_info "Instalando Cluster Autoscaler..."
    
    eksctl create iamserviceaccount \
        --cluster="$CLUSTER_NAME" \
        --namespace=kube-system \
        --name=cluster-autoscaler \
        --attach-policy-arn=arn:aws:iam::aws:policy/AutoScalingFullAccess \
        --approve \
        --region="$AWS_REGION"
    
    # Aplicar Cluster Autoscaler
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
    
    # Configurar para o cluster
    kubectl patch deployment cluster-autoscaler \
        -n kube-system \
        -p '{"spec":{"template":{"metadata":{"annotations":{"cluster-autoscaler.kubernetes.io/safe-to-evict": "false"}}}}}'
    
    kubectl patch deployment cluster-autoscaler \
        -n kube-system \
        -p '{"spec":{"template":{"spec":{"containers":[{"name":"cluster-autoscaler","command":["./cluster-autoscaler","--v=4","--stderrthreshold=info","--cloud-provider=aws","--skip-nodes-with-local-storage=false","--expander=least-waste","--node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/'$CLUSTER_NAME'"]}]}}}}'
    
    # Metrics Server (FUNCIONALIDADE 7: Metricas)
    print_info "Instalando Metrics Server..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    # EBS CSI Driver para persistent volumes
    print_info "Instalando EBS CSI Driver..."
    eksctl create iamserviceaccount \
        --cluster="$CLUSTER_NAME" \
        --namespace=kube-system \
        --name=ebs-csi-controller-sa \
        --attach-policy-arn=arn:aws:iam::aws:policy/service-role/Amazon_EBS_CSI_DriverPolicy \
        --approve \
        --region="$AWS_REGION"
    
    print_success "Addons instalados com sucesso!"
}

# =====================================================================
# FUNCAO 5: GERAR MANIFESTS KUBERNETES PARA AWS
# =====================================================================

generate_k8s_manifests() {
    print_step "Gerando manifests Kubernetes para AWS..."
    
    # Criar diretorio para manifests AWS
    mkdir -p k8s-aws
    
    # Namespace
    cat > k8s-aws/namespace.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${NAMESPACE}
  labels:
    name: ${NAMESPACE}
    environment: production
    project: ualflix
EOF

    # ConfigMap com configuracoes AWS
    cat > k8s-aws/configmap.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ualflix-config
  namespace: ${NAMESPACE}
data:
  # AWS Configuration
  AWS_REGION: "${AWS_REGION}"
  
  # Database Configuration (MongoDB Atlas)
  MONGODB_CONNECTION_STRING: "mongodb+srv://ualflix:\${MONGODB_PASSWORD}@ualflix-cluster.mongodb.net/ualflix?retryWrites=true&w=majority"
  MONGODB_DATABASE: "ualflix"
  
  # Service URLs
  AUTH_SERVICE_URL: "http://auth-service:8000"
  CATALOG_SERVICE_URL: "http://catalog-service:8000"
  STREAMING_SERVICE_URL: "http://streaming-service:8001"
  ADMIN_SERVICE_URL: "http://admin-service:8002"
  
  # Application Settings
  FLASK_ENV: "production"
  LOG_LEVEL: "INFO"
  
  # Cloud Settings
  ENVIRONMENT: "aws"
  CLUSTER_NAME: "${CLUSTER_NAME}"
EOF

    # Secrets
    cat > k8s-aws/secrets.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ualflix-secrets
  namespace: ${NAMESPACE}
type: Opaque
data:
  # MongoDB Password (base64 encoded)
  MONGODB_PASSWORD: $(echo -n "your-mongodb-password-here" | base64)
  
  # JWT Secret
  JWT_SECRET: $(echo -n "ualflix-jwt-secret-change-in-production" | base64)
  
  # Application Secrets
  SECRET_KEY: $(echo -n "ualflix-secret-key-aws-production" | base64)
EOF

    # Gerar deployments para cada servico
    for service in "${SERVICES[@]}"; do
        generate_service_deployment "$service"
    done
    
    # Gerar servicos
    generate_services
    
    # Gerar ingress
    generate_ingress
    
    # Gerar HPA (Horizontal Pod Autoscaler)
    generate_hpa
    
    print_success "Manifests Kubernetes gerados!"
}

generate_service_deployment() {
    local service=$1
    local image="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_PREFIX}/${service}:latest"
    
    # Configuracoes especificas por servico
    case $service in
        "frontend")
            port=3000
            replicas=2
            ;;
        "authentication_service")
            port=8000
            replicas=3
            ;;
        "catalog_service")
            port=8000
            replicas=4
            ;;
        "streaming_service")
            port=8001
            replicas=4
            ;;
        "admin_service")
            port=8002
            replicas=2
            ;;
        "video_processor")
            port=8000
            replicas=2
            ;;
        *)
            port=8000
            replicas=2
            ;;
    esac
    
    cat > "k8s-aws/${service}-deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${service}
  namespace: ${NAMESPACE}
  labels:
    app: ${service}
    tier: application
    environment: production
spec:
  replicas: ${replicas}
  selector:
    matchLabels:
      app: ${service}
  template:
    metadata:
      labels:
        app: ${service}
        tier: application
        environment: production
      annotations:
        # FUNCIONALIDADE 7: Prometheus metrics
        prometheus.io/scrape: "true"
        prometheus.io/port: "${port}"
        prometheus.io/path: "/metrics"
    spec:
      # FUNCIONALIDADE 2: Distribuicao pelos nos
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - ${service}
              topologyKey: kubernetes.io/hostname
      
      containers:
      - name: ${service}
        image: ${image}
        imagePullPolicy: Always
        ports:
        - containerPort: ${port}
          name: http
        
        # Configuracoes de recursos
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        # Environment variables
        envFrom:
        - configMapRef:
            name: ualflix-config
        - secretRef:
            name: ualflix-secrets
        
        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: ${port}
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: ${port}
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        
        # Security context
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          runAsUser: 1000
      
      # Service account
      serviceAccountName: default
      
      # Restart policy
      restartPolicy: Always
EOF
}

generate_services() {
    print_info "Gerando Services Kubernetes..."
    
    for service in "${SERVICES[@]}"; do
        case $service in
            "frontend")
                port=3000
                ;;
            "authentication_service")
                port=8000
                ;;
            "catalog_service")
                port=8000
                ;;
            "streaming_service")
                port=8001
                ;;
            "admin_service")
                port=8002
                ;;
            "video_processor")
                port=8000
                ;;
        esac
        
        cat > "k8s-aws/${service}-service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: ${service}
  namespace: ${NAMESPACE}
  labels:
    app: ${service}
    tier: application
spec:
  selector:
    app: ${service}
  ports:
  - port: ${port}
    targetPort: ${port}
    protocol: TCP
    name: http
  type: ClusterIP
EOF
    done
}

generate_ingress() {
    print_info "Gerando Ingress com ALB..."
    
    cat > k8s-aws/ingress.yaml << EOF
# FUNCIONALIDADE 6: LOAD BALANCING - AWS Application Load Balancer
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ualflix-ingress
  namespace: ${NAMESPACE}
  annotations:
    # AWS Load Balancer Controller
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTP
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    
    # FUNCIONALIDADE 4: CLOUD - Certificado SSL automatico
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:${AWS_REGION}:${AWS_ACCOUNT_ID}:certificate/your-certificate-id
    
    # Health checks
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '30'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '3'
    
    # Load balancing
    alb.ingress.kubernetes.io/load-balancer-name: ualflix-alb
    alb.ingress.kubernetes.io/group.name: ualflix
    
    # FUNCIONALIDADE 7: Monitoring
    alb.ingress.kubernetes.io/tags: Environment=production,Project=ualflix,Course=ArquiteturaAvancada
spec:
  rules:
  - host: ${DOMAIN_NAME}
    http:
      paths:
      # Frontend
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
      
      # Authentication API
      - path: /api/auth
        pathType: Prefix
        backend:
          service:
            name: authentication_service
            port:
              number: 8000
      
      # Admin API
      - path: /api/admin
        pathType: Prefix
        backend:
          service:
            name: admin_service
            port:
              number: 8002
      
      # Catalog API
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: catalog_service
            port:
              number: 8000
      
      # Streaming
      - path: /stream
        pathType: Prefix
        backend:
          service:
            name: streaming_service
            port:
              number: 8001
EOF
}

generate_hpa() {
    print_info "Gerando Horizontal Pod Autoscalers..."
    
    # HPA para servicos principais
    for service in "authentication_service" "catalog_service" "streaming_service"; do
        cat > "k8s-aws/${service}-hpa.yaml" << EOF
# FUNCIONALIDADE 4: CLOUD - Auto-scaling automatico
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ${service}-hpa
  namespace: ${NAMESPACE}
  labels:
    app: ${service}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${service}
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 60
EOF
    done
}

# =====================================================================
# FUNCAO 6: DEPLOY DA APLICACAO
# =====================================================================

deploy_application() {
    print_step "Fazendo deploy da aplicacao no EKS..."
    
    # Aplicar todos os manifests
    print_info "Aplicando manifests Kubernetes..."
    
    # Namespace primeiro
    kubectl apply -f k8s-aws/namespace.yaml
    
    # ConfigMaps e Secrets
    kubectl apply -f k8s-aws/configmap.yaml
    kubectl apply -f k8s-aws/secrets.yaml
    
    # Deployments
    for service in "${SERVICES[@]}"; do
        print_info "Deploying $service..."
        kubectl apply -f "k8s-aws/${service}-deployment.yaml"
        kubectl apply -f "k8s-aws/${service}-service.yaml"
    done
    
    # HPA
    for service in "authentication_service" "catalog_service" "streaming_service"; do
        kubectl apply -f "k8s-aws/${service}-hpa.yaml"
    done
    
    # Ingress (ALB)
    kubectl apply -f k8s-aws/ingress.yaml
    
    print_success "Deploy da aplicacao concluido!"
}

# =====================================================================
# FUNCAO 7: CONFIGURAR MONITORING
# =====================================================================

setup_monitoring() {
    print_step "Configurando monitoring com CloudWatch e Prometheus..."
    
    # CloudWatch Container Insights
    print_info "Instalando CloudWatch Container Insights..."
    
    # Criar namespace
    kubectl create namespace amazon-cloudwatch || true
    
    # Instalar CloudWatch agent
    kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
    
    # Configurar logs
    eksctl utils associate-iam-oidc-provider --cluster="$CLUSTER_NAME" --region="$AWS_REGION" --approve
    
    # Prometheus para metricas customizadas
    print_info "Instalando Prometheus..."
    
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    helm install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set prometheus.prometheusSpec.retention=7d \
        --set grafana.adminPassword=admin123 \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=10Gi
    
    print_success "Monitoring configurado!"
}

# =====================================================================
# FUNCAO 8: VERIFICAR DEPLOY
# =====================================================================

verify_deployment() {
    print_step "Verificando deploy..."
    
    # Verificar pods
    print_info "Status dos pods:"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Verificar services
    print_info "Status dos services:"
    kubectl get services -n "$NAMESPACE"
    
    # Verificar ingress
    print_info "Status do ingress:"
    kubectl get ingress -n "$NAMESPACE"
    
    # Obter URL do Load Balancer
    print_info "Aguardando Load Balancer ficar pronto..."
    sleep 60
    
    ALB_URL=$(kubectl get ingress ualflix-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [ -n "$ALB_URL" ]; then
        print_success "Deploy concluido com sucesso!"
        print_success "URL da aplicacao: https://$ALB_URL"
        print_success "Dominio configurado: https://$DOMAIN_NAME"
    else
        print_info "Load Balancer ainda sendo provisionado..."
        print_info "Execute: kubectl get ingress -n $NAMESPACE para verificar status"
    fi
    
    # HPA status
    print_info "Status do Auto-scaling:"
    kubectl get hpa -n "$NAMESPACE"
    
    # Nodes status
    print_info "Status dos nos:"
    kubectl get nodes -o wide
}

# =====================================================================
# FUNCAO 9: CLEANUP (OPCIONAL)
# =====================================================================

cleanup_aws_resources() {
    print_step "Limpando recursos AWS..."
    
    read -p "Tem certeza que quer deletar todos os recursos? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        print_info "Cleanup cancelado"
        return 0
    fi
    
    # Deletar aplicacao
    print_info "Deletando aplicacao..."
    kubectl delete namespace "$NAMESPACE" || true
    
    # Deletar cluster EKS
    print_info "Deletando cluster EKS..."
    eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION"
    
    # Deletar repositorios ECR
    print_info "Deletando repositorios ECR..."
    for service in "${SERVICES[@]}"; do
        aws ecr delete-repository \
            --repository-name "${ECR_REPOSITORY_PREFIX}/${service}" \
            --region "$AWS_REGION" \
            --force || true
    done
    
    print_success "Cleanup concluido!"
}

# =====================================================================
# FUNCAO PRINCIPAL
# =====================================================================

show_usage() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  deploy      - Deploy completo na AWS (default)"
    echo "  build       - Apenas build e push das imagens"
    echo "  cluster     - Apenas criar cluster EKS"
    echo "  app         - Apenas deploy da aplicacao"
    echo "  monitoring  - Apenas configurar monitoring"
    echo "  verify      - Verificar status do deploy"
    echo "  cleanup     - Limpar todos os recursos AWS"
    echo "  help        - Mostrar esta ajuda"
    echo ""
    echo "Variaveis de ambiente:"
    echo "  AWS_REGION              - Regiao AWS (default: eu-west-1)"
    echo "  AWS_ACCOUNT_ID          - ID da conta AWS (auto-detectado)"
    echo "  CLUSTER_NAME            - Nome do cluster EKS (default: ualflix-eks-cluster)"
    echo "  DOMAIN_NAME             - Dominio da aplicacao (default: ualflix.example.com)"
    echo "  EKS_NODE_TYPE           - Tipo de instancia EC2 (default: t3.medium)"
    echo "  EKS_MIN_NODES           - Minimo de nos (default: 2)"
    echo "  EKS_MAX_NODES           - Maximo de nos (default: 10)"
    echo "  EKS_DESIRED_NODES       - Nos desejados (default: 3)"
    echo ""
    echo "Exemplo:"
    echo "  AWS_REGION=us-east-1 DOMAIN_NAME=ualflix.meudominio.com $0 deploy"
}

main() {
    local command="${1:-deploy}"
    
    print_header "UALFlix - Deploy AWS (FUNCIONALIDADE 4: Cloud)"
    print_info "Comando: $command"
    print_info "Regiao AWS: $AWS_REGION"
    print_info "Cluster: $CLUSTER_NAME"
    print_info "Dominio: $DOMAIN_NAME"
    
    case $command in
        "deploy")
            check_prerequisites
            create_ecr_repositories
            build_and_push_images
            create_eks_cluster
            install_cluster_addons
            generate_k8s_manifests
            deploy_application
            setup_monitoring
            verify_deployment
            ;;
        "build")
            check_prerequisites
            create_ecr_repositories
            build_and_push_images
            ;;
        "cluster")
            check_prerequisites
            create_eks_cluster
            install_cluster_addons
            ;;
        "app")
            check_prerequisites
            generate_k8s_manifests
            deploy_application
            ;;
        "monitoring")
            check_prerequisites
            setup_monitoring
            ;;
        "verify")
            verify_deployment
            ;;
        "cleanup")
            cleanup_aws_resources
            ;;
        "help")
            show_usage
            ;;
        *)
            print_error "Comando desconhecido: $command"
            show_usage
            exit 1
            ;;
    esac
}

# =====================================================================
# VERIFICACOES INICIAIS
# =====================================================================

# Verificar se esta na raiz do projeto
if [ ! -f "docker-compose.yml" ]; then
    print_error "Execute este script na raiz do projeto UALFlix!"
    exit 1
fi

# Verificar se tem os diretorios dos servicos
for service in "${SERVICES[@]}"; do
    if [ ! -d "$service" ]; then
        print_error "Diretorio do servico nao encontrado: $service"
        exit 1
    fi
done

# =====================================================================
# EXECUCAO
# =====================================================================

# Trap para cleanup em caso de interrupcao
trap 'print_error "Deploy interrompido"; exit 1' INT TERM

# Executar funcao principal
main "$@"

print_success "Script concluido com sucesso!"
print_info "FUNCIONALIDADE 4: IMPLEMENTACAO NA CLOUD - Completamente implementada!"
print_info ""
print_info "Funcionalidades AWS implementadas:"
print_info "- EKS (Elastic Kubernetes Service) para orquestracao"
print_info "- ECR (Elastic Container Registry) para imagens Docker"
print_info "- ALB (Application Load Balancer) para load balancing"
print_info "- Auto Scaling Groups para elasticidade"
print_info "- CloudWatch para monitoramento"
print_info "- Container Insights para logs"
print_info "- Prometheus/Grafana para metricas customizadas"
print_info ""
print_info "Caracteristicas cloud implementadas:"
print_info "- Elasticidade automatica (HPA)"
print_info "- Alta disponibilidade (multi-AZ)"
print_info "- Tolerancia a falhas (auto-recovery)"
print_info "- Escalabilidade horizontal"
print_info "- Monitoramento e alertas"
print_info "- Load balancing automatico"
print_info "- SSL/TLS automatico"
print_info ""
print_info "Para monitorar o sistema:"
print_info "  kubectl get pods -n $NAMESPACE"
print_info "  kubectl get hpa -n $NAMESPACE"
print_info "  kubectl logs -f deployment/catalog-service -n $NAMESPACE"
print_info ""
print_info "Para acessar monitoramento:"
print_info "  kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090"
print_info "  kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"