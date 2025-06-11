# 🔧 Guia de Resolução de Problemas - UALFlix Kubernetes

## 🚨 Problemas Comuns e Soluções

### 1. Minikube não inicia ou falha

#### Problema: "docker: not found" ou "Docker não está rodando"
```bash
# Solução:
sudo systemctl start docker
sudo usermod -aG docker $USER
# Fazer logout e login novamente
```

#### Problema: Recursos insuficientes
```bash
# Verificar recursos disponíveis
docker system df
free -h

# Limpar Docker
docker system prune -a

# Reduzir recursos do Minikube
minikube start --driver=docker --nodes=3 --cpus=1 --memory=2048
```

#### Problema: Minikube trava na inicialização
```bash
# Reset completo
minikube delete
docker system prune -a
minikube start --driver=docker --nodes=3 --cpus=2 --memory=4096
```

### 2. Pods em CrashLoopBackOff

#### Verificar logs do pod
```bash
# Ver logs atuais
kubectl logs -n ualflix <pod-name>

# Ver logs anteriores
kubectl logs -n ualflix <pod-name> --previous

# Logs contínuos
kubectl logs -f -n ualflix deployment/<deployment-name>
```

#### Problemas comuns por serviço:

**MongoDB:**
```bash
# Verificar se o StatefulSet está correto
kubectl describe statefulset mongodb -n ualflix

# Verificar PVC
kubectl get pvc -n ualflix

# Logs do MongoDB
kubectl logs -n ualflix mongodb-0

# Conectar ao MongoDB para debug
kubectl exec -it -n ualflix mongodb-0 -- mongosh
```

**Serviços da aplicação:**
```bash
# Verificar se as imagens foram construídas
eval $(minikube docker-env)
docker images | grep -E "(catalog_service|auth|streaming|admin)"

# Re-build se necessário
docker build -t catalog_service:latest ./catalog_service/

# Verificar variáveis de ambiente
kubectl describe pod -n ualflix <pod-name>
```

### 3. Serviços não respondem

#### Verificar conectividade interna
```bash
# Entrar em um pod para testar
kubectl run test-pod --image=curlimages/curl -i --tty --rm -- sh

# Dentro do pod, testar serviços:
curl http://auth-service.ualflix.svc.cluster.local:8000/health
curl http://catalog-service.ualflix.svc.cluster.local:8000/health
curl http://nginx-gateway.ualflix.svc.cluster.local:8080/health
```

#### Verificar DNS
```bash
# Testar resolução DNS
kubectl exec -n ualflix deployment/frontend -- nslookup auth-service
kubectl exec -n ualflix deployment/frontend -- nslookup catalog-service
```

#### Verificar endpoints
```bash
# Ver endpoints dos serviços
kubectl get endpoints -n ualflix

# Verificar se os pods estão prontos
kubectl get pods -n ualflix -o wide
```

### 4. NGINX Gateway não funciona

#### Verificar configuração
```bash
# Ver logs do NGINX
kubectl logs -n ualflix deployment/nginx-gateway

# Verificar configuração
kubectl describe configmap nginx-config -n ualflix

# Testar configuração NGINX
kubectl exec -n ualflix deployment/nginx-gateway -- nginx -t
```

#### Problemas de roteamento
```bash
# Verificar se todos os serviços estão rodando
kubectl get services -n ualflix

# Testar roteamento específico
kubectl exec -n ualflix deployment/nginx-gateway -- curl -f http://localhost:8080/health
kubectl exec -n ualflix deployment/nginx-gateway -- curl -f http://auth-service:8000/health
```

### 5. Base de dados MongoDB

#### Verificar Replica Set
```bash
# Conectar ao MongoDB primary
kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.status()"

# Ver configuração do replica set
kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.conf()"

# Forçar nova eleição se necessário
kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.stepDown()"
```

#### Problemas de autenticação
```bash
# Verificar usuários
kubectl exec -it -n ualflix mongodb-0 -- mongosh admin --eval "db.getUsers()"

# Recriar usuário admin se necessário
kubectl exec -it -n ualflix mongodb-0 -- mongosh admin --eval "
db.createUser({
  user: 'admin',
  pwd: 'password',
  roles: [{ role: 'root', db: 'admin' }]
});"
```

#### Reset do MongoDB
```bash
# Deletar StatefulSet e PVCs
kubectl delete statefulset mongodb -n ualflix
kubectl delete pvc mongodb-data-mongodb-0 mongodb-data-mongodb-1 mongodb-data-mongodb-2 -n ualflix

# Re-aplicar
kubectl apply -f k8s/database/
```

### 6. Problemas de Recursos

#### Verificar recursos dos nós
```bash
# Ver utilização atual
kubectl top nodes
kubectl top pods -n ualflix

# Ver recursos definidos nos deployments
kubectl describe deployment -n ualflix catalog-service
```

#### Ajustar recursos se necessário
```bash
# Editar deployment para reduzir recursos
kubectl edit deployment catalog-service -n ualflix

# Ou aplicar patch
kubectl patch deployment catalog-service -n ualflix -p '{"spec":{"template":{"spec":{"containers":[{"name":"catalog-service","resources":{"requests":{"memory":"128Mi","cpu":"100m"},"limits":{"memory":"256Mi","cpu":"250m"}}}]}}}}'
```

### 7. Problemas de Rede

#### Verificar políticas de rede
```bash
# Ver se há network policies
kubectl get networkpolicies -n ualflix

# Testar conectividade entre pods
kubectl exec -n ualflix deployment/frontend -- ping catalog-service
```

#### Verificar firewall/iptables
```bash
# No host, verificar se portas estão abertas
sudo iptables -L
sudo ufw status
```

### 8. Problemas de Storage

#### Verificar Persistent Volumes
```bash
# Ver PVs e PVCs
kubectl get pv
kubectl get pvc -n ualflix

# Verificar detalhes
kubectl describe pvc mongodb-data-mongodb-0 -n ualflix
```

#### Limpar storage órfão
```bash
# Deletar PVCs órfãos
kubectl delete pvc --all -n ualflix

# Re-aplicar database
kubectl apply -f k8s/database/
```

### 9. Comandos de Debug Gerais

#### Informações do cluster
```bash
# Status geral
kubectl cluster-info

# Eventos recentes
kubectl get events -n ualflix --sort-by=.metadata.creationTimestamp

# Verificar addons do Minikube
minikube addons list
```

#### Restart de componentes
```bash
# Restart de um deployment
kubectl rollout restart deployment/catalog-service -n ualflix

# Restart de todos os deployments
kubectl rollout restart deployment --all -n ualflix

# Verificar status do rollout
kubectl rollout status deployment/catalog-service -n ualflix
```

#### Limpeza completa
```bash
# Deletar namespace (remove tudo)
kubectl delete namespace ualflix

# Restart do Minikube
minikube stop
minikube start

# Ou reset completo
minikube delete
minikube start --driver=docker --nodes=3 --cpus=2 --memory=4096
```

## 🎯 Checklist de Verificação

Use este checklist quando algo não funcionar:

### ✅ Cluster
- [ ] Minikube está rodando: `minikube status`
- [ ] 3 nós estão ativos: `kubectl get nodes`
- [ ] Addons estão habilitados: `minikube addons list`

### ✅ Imagens
- [ ] Docker environment configurado: `eval $(minikube docker-env)`
- [ ] Imagens foram construídas: `docker images | grep -E "(frontend|catalog|auth)"`
- [ ] ImagePullPolicy é Never nos deployments

### ✅ Namespace e Recursos
- [ ] Namespace existe: `kubectl get namespace ualflix`
- [ ] Secrets foram aplicados: `kubectl get secrets -n ualflix`
- [ ] ConfigMaps foram aplicados: `kubectl get configmaps -n ualflix`

### ✅ Database
- [ ] MongoDB pods estão rodando: `kubectl get pods -n ualflix -l app=mongodb`
- [ ] Replica Set está configurado: `kubectl exec -it -n ualflix mongodb-0 -- mongosh --eval "rs.status()"`
- [ ] PVCs estão bound: `kubectl get pvc -n ualflix`

### ✅ Serviços
- [ ] Todos os pods estão Ready: `kubectl get pods -n ualflix`
- [ ] Services têm endpoints: `kubectl get endpoints -n ualflix`
- [ ] NGINX Gateway está respondendo: `curl $(minikube service nginx-gateway --namespace ualflix --url)/health`

### ✅ Rede
- [ ] DNS está funcionando: `kubectl exec -n ualflix deployment/frontend -- nslookup catalog-service`
- [ ] Conectividade interna: `kubectl exec -n ualflix deployment/frontend -- curl -f http://catalog-service:8000/health`

## 📞 Quando Pedir Ajuda

Se os problemas persistirem, colete estas informações:

```bash
# Informações do ambiente
kubectl version
minikube version
docker version

# Status completo
kubectl get all -n ualflix -o wide
kubectl describe nodes
kubectl get events -n ualflix --sort-by=.metadata.creationTimestamp

# Logs dos serviços com problema
kubectl logs -n ualflix deployment/nginx-gateway --tail=50
kubectl logs -n ualflix deployment/catalog-service --tail=50
kubectl logs -n ualflix mongodb-0 --tail=50

# Configurações
kubectl get configmap app-config -n ualflix -o yaml
kubectl describe deployment catalog-service -n ualflix
```

Estas informações ajudarão a identificar rapidamente o problema! 🚀