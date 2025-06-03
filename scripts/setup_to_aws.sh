#!/bin/bash
# scripts/setup_aws.sh
# Script de configuracao inicial para AWS
# Execute ANTES do deploy_to_aws.sh

set -e

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

print_warning() {
    echo "[WARNING] $1"
}

# =====================================================================
# INSTALACAO DE FERRAMENTAS
# =====================================================================

install_aws_cli() {
    print_step "Verificando AWS CLI..."
    
    if command -v aws &> /dev/null; then
        print_info "AWS CLI ja instalado: $(aws --version)"
        return 0
    fi
    
    print_info "Instalando AWS CLI..."
    
    # Detectar OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install awscli
        else
            curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
            sudo installer -pkg AWSCLIV2.pkg -target /
            rm AWSCLIV2.pkg
        fi
    else
        print_error "OS nao suportado. Instale AWS CLI manualmente: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    print_success "AWS CLI instalado!"
}

install_eksctl() {
    print_step "Verificando eksctl..."
    
    if command -v eksctl &> /dev/null; then
        print_info "eksctl ja instalado: $(eksctl version)"
        return 0
    fi
    
    print_info "Instalando eksctl..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
        sudo mv /tmp/eksctl /usr/local/bin
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew tap weaveworks/tap
            brew install weaveworks/tap/eksctl
        else
            curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Darwin_amd64.tar.gz" | tar xz -C /tmp
            sudo mv /tmp/eksctl /usr/local/bin
        fi
    else
        print_error "OS nao suportado. Instale eksctl manualmente: https://eksctl.io/"
        exit 1
    fi
    
    print_success "eksctl instalado!"
}

install_kubectl() {
    print_step "Verificando kubectl..."
    
    if command -v kubectl &> /dev/null; then
        print_info "kubectl ja instalado: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
        return 0
    fi
    
    print_info "Instalando kubectl..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install kubectl
        else
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
            chmod +x kubectl
            sudo mv kubectl /usr/local/bin/
        fi
    else
        print_error "OS nao suportado. Instale kubectl manualmente: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    
    print_success "kubectl instalado!"
}

install_helm() {
    print_step "Verificando Helm..."
    
    if command -v helm &> /dev/null; then
        print_info "Helm ja instalado: $(helm version --short)"
        return 0
    fi
    
    print_info "Instalando Helm..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install helm
        else
            curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
        fi
    else
        print_error "OS nao suportado. Instale Helm manualmente: https://helm.sh/"
        exit 1
    fi
    
    print_success "Helm instalado!"
}

# =====================================================================
# CONFIGURACAO AWS
# =====================================================================

configure_aws() {
    print_step "Configurando AWS CLI..."
    
    # Verificar se ja esta configurado
    if aws sts get-caller-identity &> /dev/null; then
        print_info "AWS ja configurado:"
        aws sts get-caller-identity
        
        read -p "Quer reconfigurar? (y/n): " reconfigure
        if [ "$reconfigure" != "y" ]; then
            return 0
        fi
    fi
    
    print_info "Execute 'aws configure' e insira suas credenciais AWS:"
    print_info "- Access Key ID: (sua chave de acesso)"
    print_info "- Secret Access Key: (sua chave secreta)"
    print_info "- Default region: eu-west-1 (ou sua regiao preferida)"
    print_info "- Default output format: json"
    
    aws configure
    
    # Verificar configuracao
    if aws sts get-caller-identity &> /dev/null; then
        print_success "AWS configurado com sucesso!"
        aws sts get-caller-identity
    else
        print_error "Falha na configuracao AWS"
        exit 1
    fi
}

# =====================================================================
# VERIFICACOES DE PERMISSOES
# =====================================================================

check_aws_permissions() {
    print_step "Verificando permissoes AWS..."
    
    # Lista de servicos necessarios
    services_to_check=(
        "eks"
        "ecr"
        "ec2"
        "iam"
        "cloudformation"
        "autoscaling"
        "elasticloadbalancing"
        "logs"
        "cloudwatch"
    )
    
    print_info "Verificando acesso aos servicos AWS..."
    
    for service in "${services_to_check[@]}"; do
        case $service in
            "eks")
                if aws eks list-clusters --region eu-west-1 &> /dev/null; then
                    print_info "✓ EKS: OK"
                else
                    print_warning "✗ EKS: Sem permissao ou servico indisponivel"
                fi
                ;;
            "ecr")
                if aws ecr describe-repositories --region eu-west-1 &> /dev/null; then
                    print_info "✓ ECR: OK"
                else
                    print_warning "✗ ECR: Sem permissao"
                fi
                ;;
            "ec2")
                if aws ec2 describe-instances --region eu-west-1 &> /dev/null; then
                    print_info "✓ EC2: OK"
                else
                    print_warning "✗ EC2: Sem permissao"
                fi
                ;;
            "iam")
                if aws iam list-roles &> /dev/null; then
                    print_info "✓ IAM: OK"
                else
                    print_warning "✗ IAM: Sem permissao"
                fi
                ;;
            "cloudformation")
                if aws cloudformation list-stacks --region eu-west-1 &> /dev/null; then
                    print_info "✓ CloudFormation: OK"
                else
                    print_warning "✗ CloudFormation: Sem permissao"
                fi
                ;;
        esac
    done
    
    print_info "Verificacao de permissoes concluida"
    print_warning "Se houver avisos acima, consulte o administrador AWS"
}

# =====================================================================
# CONFIGURAR DOMINIO (OPCIONAL)
# =====================================================================

setup_domain() {
    print_step "Configuracao de dominio (opcional)..."
    
    read -p "Tem um dominio para o UALFlix? (y/n): " has_domain
    
    if [ "$has_domain" = "y" ]; then
        read -p "Digite o dominio (ex: ualflix.meusite.com): " domain
        
        print_info "Para usar seu dominio, voce precisa:"
        print_info "1. Ter o dominio registrado"
        print_info "2. Configurar Route 53 ou DNS provider"
        print_info "3. Obter certificado SSL via ACM"
        print_info ""
        print_info "Comandos uteis:"
        print_info "# Listar hosted zones"
        print_info "aws route53 list-hosted-zones"
        print_info ""
        print_info "# Requisitar certificado SSL"
        print_info "aws acm request-certificate --domain-name $domain --validation-method DNS --region eu-west-1"
        print_info ""
        print_info "Anote o ARN do certificado para usar no deploy"
        
        # Salvar configuracao
        echo "DOMAIN_NAME=$domain" > .env.aws
        print_success "Dominio salvo em .env.aws"
    else
        print_info "Usando dominio padrao do Load Balancer AWS"
        echo "DOMAIN_NAME=ualflix.example.com" > .env.aws
    fi
}

# =====================================================================
# CRIAR ARQUIVO DE CONFIGURACAO
# =====================================================================

create_config_file() {
    print_step "Criando arquivo de configuracao..."
    
    # Obter account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region)
    
    cat > .env.aws << EOF
# Configuracao AWS para UALFlix
# Gerado automaticamente em $(date)

# AWS Configuration
AWS_REGION=${AWS_REGION:-eu-west-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}

# EKS Configuration
CLUSTER_NAME=ualflix-eks-cluster
EKS_NODE_TYPE=t3.medium
EKS_MIN_NODES=2
EKS_MAX_NODES=10
EKS_DESIRED_NODES=3

# ECR Configuration
ECR_REPOSITORY_PREFIX=ualflix

# Domain Configuration (edite conforme necessario)
DOMAIN_NAME=ualflix.example.com

# MongoDB Atlas (configure suas credenciais)
MONGODB_PASSWORD=your-mongodb-password-here

# SSL Certificate ARN (obtenha via ACM)
CERTIFICATE_ARN=arn:aws:acm:${AWS_REGION:-eu-west-1}:${AWS_ACCOUNT_ID}:certificate/your-certificate-id

# Opcional: Tags para recursos
PROJECT_TAG=UALFlix
COURSE_TAG=ArquiteturaAvancada
ENVIRONMENT_TAG=production
EOF
    
    print_success "Arquivo .env.aws criado!"
    print_info "Edite .env.aws antes de executar o deploy"
}

# =====================================================================
# VERIFICACAO FINAL
# =====================================================================

final_check() {
    print_step "Verificacao final..."
    
    print_info "Ferramentas instaladas:"
    echo "  AWS CLI: $(aws --version)"
    echo "  eksctl: $(eksctl version)"
    echo "  kubectl: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    echo "  Helm: $(helm version --short)"
    echo "  Docker: $(docker --version)"
    
    print_info "Configuracao AWS:"
    aws sts get-caller-identity
    
    print_info "Proximos passos:"
    print_info "1. Edite .env.aws com suas configuracoes"
    print_info "2. Configure MongoDB Atlas (ou use RDS)"
    print_info "3. Configure certificado SSL se tiver dominio"
    print_info "4. Execute: source .env.aws && ./scripts/deploy_to_aws.sh"
    
    print_success "Setup AWS concluido!"
}

# =====================================================================
# FUNCAO PRINCIPAL
# =====================================================================

main() {
    print_header "UALFlix - Setup AWS (FUNCIONALIDADE 4)"
    
    print_info "Este script prepara o ambiente para deploy na AWS"
    print_info "Execute ANTES de usar deploy_to_aws.sh"
    
    # Verificar se esta na raiz do projeto
    if [ ! -f "docker-compose.yml" ]; then
        print_error "Execute este script na raiz do projeto UALFlix!"
        exit 1
    fi
    
    # Instalacao de ferramentas
    install_aws_cli
    install_eksctl
    install_kubectl
    install_helm
    
    # Configuracao AWS
    configure_aws
    check_aws_permissions
    
    # Configuracao opcional
    setup_domain
    create_config_file
    
    # Verificacao final
    final_check
}

# =====================================================================
# MENU INTERATIVO (OPCIONAL)
# =====================================================================

show_menu() {
    echo "============================================================"
    echo "UALFlix - Setup AWS"
    echo "============================================================"
    echo "1. Setup completo (recomendado)"
    echo "2. Apenas instalar ferramentas"
    echo "3. Apenas configurar AWS"
    echo "4. Verificar permissoes"
    echo "5. Configurar dominio"
    echo "6. Criar arquivo de configuracao"
    echo "7. Sair"
    echo "============================================================"
    read -p "Escolha uma opcao (1-7): " choice
    
    case $choice in
        1) main ;;
        2) install_aws_cli; install_eksctl; install_kubectl; install_helm ;;
        3) configure_aws ;;
        4) check_aws_permissions ;;
        5) setup_domain ;;
        6) create_config_file ;;
        7) exit 0 ;;
        *) print_error "Opcao invalida"; show_menu ;;
    esac
}

# =====================================================================
# EXECUCAO
# =====================================================================

if [ "$1" = "--menu" ]; then
    show_menu
else
    main
fi