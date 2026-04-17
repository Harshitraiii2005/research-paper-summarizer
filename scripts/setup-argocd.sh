#!/bin/bash

# ArgoCD Installation & Configuration Script
# This script installs ArgoCD and sets up automatic deployments

set -e

ARGOCD_NAMESPACE="argocd"
ARGOCD_VERSION="v2.10.0"
DOCKER_USERNAME="${1:-your-dockerhub-username}"
GITHUB_REPO="${2:-https://github.com/your-username/research-paper-summarizer}"
GITHUB_TOKEN="${3:-your-github-token}"
ARGOCD_DOMAIN="${4:-argocd.example.com}"

echo "🚀 Installing ArgoCD..."

# Create namespace
kubectl create namespace ${ARGOCD_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Install ArgoCD
kubectl apply -n ${ARGOCD_NAMESPACE} -f https://raw.githubusercontent.com/argoproj/argo-cd/release-${ARGOCD_VERSION}/manifests/install.yaml

echo "⏳ Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n ${ARGOCD_NAMESPACE} --timeout=300s

# Get initial admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

echo "📝 ArgoCD Initial Admin Password: ${ARGOCD_PASSWORD}"
echo "🌐 ArgoCD Dashboard: https://${ARGOCD_DOMAIN}"

# Port forward for local access
echo "🔗 Setting up port forward to ArgoCD (kubectl port-forward)..."
kubectl port-forward svc/argocd-server -n ${ARGOCD_NAMESPACE} 8080:443 &
sleep 2

# Download ArgoCD CLI
echo "📥 Downloading ArgoCD CLI..."
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# Create GitHub repository secret
echo "🔐 Creating GitHub repository secret..."
kubectl create secret generic github-repo-secret \
  --from-literal=type=git \
  --from-literal=url=${GITHUB_REPO} \
  --from-literal=password=${GITHUB_TOKEN} \
  -n ${ARGOCD_NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

# Add Docker Hub credentials to pull images
echo "🐳 Adding Docker Hub credentials..."
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=${DOCKER_USERNAME} \
  --docker-password=${GITHUB_TOKEN} \
  -n paperintel \
  --dry-run=client -o yaml | kubectl apply -f -

# Create paperintel namespace
kubectl create namespace paperintel --dry-run=client -o yaml | kubectl apply -f -

# Apply ArgoCD application
echo "📦 Applying ArgoCD Application CRD..."
kubectl apply -f argocd/application.yaml

echo "✅ ArgoCD Setup Complete!"
echo ""
echo "📊 Next Steps:"
echo "1. Port forward: kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "2. Access: https://localhost:8080"
echo "3. Login: admin / ${ARGOCD_PASSWORD}"
echo "4. Change password with: argocd account update-password"
echo ""
echo "🔗 To expose ArgoCD externally:"
echo "   kubectl port-forward svc/argocd-server -n argocd 443:443 --address 0.0.0.0"
echo ""
