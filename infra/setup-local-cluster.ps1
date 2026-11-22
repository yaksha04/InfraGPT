# InfraGPT Local Kubernetes Setup Script (PowerShell)
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " InfraGPT Local Kubernetes Setup " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Apply Namespaces
Write-Host "[1/3] Creating Namespaces (production, staging, infragpt-system)..." -ForegroundColor Yellow
kubectl apply -f infra/k8s-setup/00-namespaces.yaml

# 2. Apply RBAC Security
Write-Host "[2/3] Configuring RBAC Security (ServiceAccount, ClusterRole)..." -ForegroundColor Yellow
kubectl apply -f infra/k8s-setup/01-serviceaccount.yaml
kubectl apply -f infra/k8s-setup/02-clusterrole.yaml
kubectl apply -f infra/k8s-setup/03-clusterrolebinding.yaml

# 3. Deploy Demo Workloads
Write-Host "[3/3] Deploying Viva Demo Microservices..." -ForegroundColor Yellow
kubectl apply -f infra/demo-workloads/

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Cluster Setup Complete!" -ForegroundColor Green
Write-Host " Run: kubectl get pods -n production" -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan
