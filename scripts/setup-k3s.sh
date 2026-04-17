#!/bin/bash

# K3s Cluster Setup Script
# This script sets up a complete K3s cluster with all required components

set -e

CLUSTER_NAME="${1:-paperintel-prod}"
DOMAIN="${2:-paperintel.example.com}"
K3S_VERSION="${3:-v1.27.4}"
DEPLOY_MONITORING="${4:-true}"

echo "🚀 Starting K3s Cluster Setup..."
echo "📋 Cluster Name: ${CLUSTER_NAME}"
echo "🌐 Domain: ${DOMAIN}"
echo "📦 K3s Version: ${K3S_VERSION}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "⚠️  This script must be run as root"
   exit 1
fi

# Update system
echo "🔄 Updating system packages..."
apt-get update
apt-get install -y curl wget git jq

# Install K3s
echo "📥 Installing K3s..."
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=${K3S_VERSION} sh -

# Wait for K3s to be ready
echo "⏳ Waiting for K3s to be ready..."
sleep 10

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
chmod 644 /etc/rancher/k3s/k3s.yaml

# Verify installation
echo "✅ Verifying K3s installation..."
k3s kubectl cluster-info
k3s kubectl get nodes

# Install Helm
echo "📥 Installing Helm..."
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install ingress-nginx
echo "📥 Installing Ingress NGINX..."
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# Install cert-manager for SSL
echo "📥 Installing Cert-Manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s

# Create ClusterIssuer for Let's Encrypt
echo "🔐 Creating Let's Encrypt ClusterIssuer..."
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@${DOMAIN}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Install Metrics Server (if not already installed)
echo "📥 Installing Metrics Server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Create paperintel namespace and apply manifests
echo "📦 Setting up PaperIntel application..."
kubectl create namespace paperintel --dry-run=client -o yaml | kubectl apply -f -

# Apply K8s manifests
kubectl apply -f k8s/namespace-rbac.yaml
kubectl apply -f k8s/configmap-secret.yaml
kubectl apply -f k8s/dependencies.yaml

echo "⏳ Waiting for dependencies to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n paperintel --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=redis -n paperintel --timeout=300s || true

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service-ingress-hpa.yaml

echo "⏳ Waiting for PaperIntel deployment..."
kubectl wait --for=condition=ready pod -l app=paperintel -n paperintel --timeout=300s || true

# Install monitoring if enabled
if [ "${DEPLOY_MONITORING}" == "true" ]; then
    echo "📊 Setting up Monitoring Stack..."
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -f monitoring/prometheus.yaml
    kubectl apply -f monitoring/grafana.yaml
    
    echo "⏳ Waiting for monitoring components..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=300s || true
    kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=300s || true
fi

# Get cluster info
echo ""
echo "✅ K3s Cluster Setup Complete!"
echo ""
echo "📊 Cluster Information:"
kubectl get nodes
echo ""
echo "📦 Namespaces:"
kubectl get namespaces
echo ""
echo "🔗 Services:"
kubectl get svc -A
echo ""
echo "💾 Persistent Volumes:"
kubectl get pv
echo ""

# Get LoadBalancer IPs
echo "🌐 LoadBalancer Services:"
kubectl get svc -A -o wide | grep LoadBalancer

echo ""
echo "📚 Next Steps:"
echo "1. Update DNS records to point to LoadBalancer IP"
echo "2. Configure your app secrets in k8s/configmap-secret.yaml"
echo "3. Deploy ArgoCD: bash scripts/setup-argocd.sh"
echo ""
echo "🎯 Access Applications:"
echo "   - PaperIntel: https://${DOMAIN}"
echo "   - Grafana: https://grafana.${DOMAIN}"
echo ""
echo "🔑 Get kubeconfig:"
echo "   scp root@<node-ip>:/etc/rancher/k3s/k3s.yaml ~/.kube/paperintel-config"
echo ""
