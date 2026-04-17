#!/bin/bash

# Complete CI/CD Pipeline Setup Script
# Sets up Jenkins, K3s, ArgoCD, and Monitoring

set -e

DOCKER_USERNAME="${1:-}"
DOCKER_PASSWORD="${2:-}"
GITHUB_TOKEN="${3:-}"
GITHUB_REPO="${4:-https://github.com/your-username/research-paper-summarizer}"
DOMAIN="${5:-example.com}"

if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Missing required parameters"
    echo "Usage: $0 <docker-username> <docker-password> <github-token> [github-repo] [domain]"
    exit 1
fi

echo "🚀 Setting up Complete CI/CD Pipeline..."
echo ""

# Setup K3s
echo "📦 Step 1: Setting up K3s cluster..."
bash scripts/setup-k3s.sh paperintel-prod "${DOMAIN}" v1.27.4 true

echo ""
echo "✅ K3s cluster is ready!"
echo ""

# Setup ArgoCD
echo "📦 Step 2: Setting up ArgoCD..."
bash scripts/setup-argocd.sh "${DOCKER_USERNAME}" "${GITHUB_REPO}" "${GITHUB_TOKEN}" "argocd.${DOMAIN}"

echo ""
echo "✅ ArgoCD is ready!"
echo ""

# Create Jenkins namespace
echo "📦 Step 3: Preparing Jenkins setup..."
kubectl create namespace jenkins --dry-run=client -o yaml | kubectl apply -f -

# Create Jenkins admin secret
kubectl create secret generic jenkins-admin \
  --from-literal=username=admin \
  --from-literal=password=jenkins-admin-password-change-me \
  -n jenkins \
  --dry-run=client -o yaml | kubectl apply -f -

# Create Docker credentials secret for Jenkins
kubectl create secret docker-registry docker-credentials \
  --docker-server=docker.io \
  --docker-username="${DOCKER_USERNAME}" \
  --docker-password="${DOCKER_PASSWORD}" \
  -n jenkins \
  --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "✅ Jenkins namespace prepared!"
echo ""

# Summary
echo "✅ Complete CI/CD Pipeline Setup Finished!"
echo ""
echo "📊 Architecture Overview:"
echo ""
echo "   Jenkins CI           →  Docker Image       →  Docker Hub"
echo "        ↓"
echo "   Run Tests & Security Checks"
echo "        ↓"
echo "   Build & Push to DockerHub"
echo "        ↓"
echo "   Update ArgoCD Manifest"
echo "        ↓"
echo "   ArgoCD CD            →  K3s Cluster      →  Auto-Deploy"
echo "        ↓"
echo "   Sync Git Repo"
echo "        ↓"
echo "   Deploy to Kubernetes"
echo "        ↓"
echo "   Prometheus/Grafana   →  Monitor & Alert"
echo ""
echo "🔗 Access URLs:"
echo "   - ArgoCD:     https://argocd.${DOMAIN}"
echo "   - Grafana:    https://grafana.${DOMAIN}"
echo "   - PaperIntel: https://paperintel.${DOMAIN}"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Configure Jenkins:"
echo "   - Install Jenkins on a machine (or deploy to K3s)"
echo "   - Configure credentials: Docker, GitHub, Slack"
echo "   - Create pipeline job pointing to: ${GITHUB_REPO}"
echo "   - Set Jenkinsfile path: Jenkinsfile"
echo ""
echo "2. Configure Webhooks:"
echo "   - GitHub webhook → Jenkins (push events)"
echo "   - Jenkins → ArgoCD (on successful build)"
echo ""
echo "3. Update Secrets:"
echo "   - GROQ_API_KEY in k8s/configmap-secret.yaml"
echo "   - DATABASE_URL for PostgreSQL"
echo "   - AWS S3 credentials if using S3 storage"
echo ""
echo "4. Update Domains:"
echo "   - Update DNS records to point to K3s LoadBalancer IP"
echo "   - Update ingress hostnames in k8s/service-ingress-hpa.yaml"
echo ""
echo "🎯 CI/CD Flow:"
echo "   1. Push code to GitHub → Webhook triggers Jenkins"
echo "   2. Jenkins runs tests & security checks"
echo "   3. Jenkins builds Docker image"
echo "   4. Jenkins pushes to DockerHub"
echo "   5. Jenkins updates ArgoCD"
echo "   6. ArgoCD syncs latest image from manifests"
echo "   7. K3s deploys new version automatically"
echo "   8. Prometheus monitors & Grafana visualizes"
echo ""
