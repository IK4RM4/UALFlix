# PowerShell script for setting up Minikube registry on Windows

Write-Host "Configurando registry para cluster multi-no..." -ForegroundColor Blue

# Enable registry addon if not already enabled
$registryStatus = minikube addons list | Select-String "registry"
if (-not ($registryStatus -match "enabled")) {
    Write-Host "Habilitando registry addon..."
    minikube addons enable registry
}

# Wait for registry pod to be ready
Write-Host "Aguardando registry pod ficar pronto..."
$maxAttempts = 30
$attempt = 0
$ready = $false

while (-not $ready -and $attempt -lt $maxAttempts) {
    $podStatus = kubectl get pods -n kube-system -l kubernetes.io/minikube-addons=registry -o jsonpath='{.items[0].status.phase}'
    if ($podStatus -eq "Running") {
        $ready = $true
        Write-Host "Registry pod está pronto!" -ForegroundColor Green
    } else {
        $attempt++
        Write-Host "Aguardando registry pod... ($attempt/$maxAttempts)"
        Start-Sleep -Seconds 5
    }
}

if (-not $ready) {
    Write-Host "Erro: Registry pod não ficou pronto após $maxAttempts tentativas" -ForegroundColor Red
    exit 1
}

# Get the registry port
$registryPort = "52652"

# Forward the registry port
Write-Host "Iniciando port-forward para registry..."
$job = Start-Process -FilePath "kubectl" -ArgumentList "port-forward", "-n", "kube-system", "service/registry", "$registryPort:5000" -PassThru -NoNewWindow

# Wait a moment to ensure port-forward is established
Start-Sleep -Seconds 5

# Verify port-forward is working
$portCheck = Test-NetConnection -ComputerName localhost -Port $registryPort -WarningAction SilentlyContinue
if (-not $portCheck.TcpTestSucceeded) {
    Write-Host "Erro: Não foi possível estabelecer conexão com o registry na porta $registryPort" -ForegroundColor Red
    if ($job -and (Get-Process -Id $job.Id -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $job.Id
    }
    exit 1
}

Write-Host "Registry configurado em localhost:$registryPort" -ForegroundColor Green

# Build and push images
Write-Host "Building e enviando imagens para registry local..." -ForegroundColor Blue

$services = @(
    "frontend",
    "authentication_service",
    "catalog_service",
    "streaming_service",
    "admin_service",
    "video_processor"
)

foreach ($service in $services) {
    $servicePath = Join-Path -Path $PSScriptRoot -ChildPath $service
    if (Test-Path $servicePath) {
        Write-Host "Building $service..."
        try {
            docker build -t "localhost:$registryPort/$service:latest" $servicePath
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Erro ao buildar $service" -ForegroundColor Red
                continue
            }
            
            docker push "localhost:$registryPort/$service:latest"
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Erro ao fazer push de $service" -ForegroundColor Red
                continue
            }
            
            Write-Host "$service buildado e enviado com sucesso!" -ForegroundColor Green
        } catch {
            Write-Host "Erro ao processar $service: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "Directory not found: $servicePath" -ForegroundColor Yellow
    }
}

Write-Host "Todas as imagens no registry local!" -ForegroundColor Green

# Stop port forwarding if still running
if ($job -and (Get-Process -Id $job.Id -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $job.Id
} 