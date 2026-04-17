#!/bin/bash

# PaperIntel CI/CD - Quick Deployment Guide

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-your-dockerhub-username}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/your-username/research-paper-summarizer}"
DOMAIN="${DOMAIN:-paperintel.example.com}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🚀 PaperIntel CI/CD Pipeline Deployment Guide      ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}📌 Step: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking Prerequisites"
    
    local missing=0
    
    echo "Checking required tools..."
    for tool in kubectl docker helm git curl; do
        if command -v $tool &> /dev/null; then
            echo "  ✓ $tool found"
        else
            echo "  ✗ $tool NOT found"
            missing=$((missing + 1))
        fi
    done
    
    if [ $missing -gt 0 ]; then
        print_error "Missing $missing required tools. Please install them first."
        return 1
    fi
    
    print_success "All prerequisites met"
    return 0
}

# Initialize configuration
init_configuration() {
    print_step "Initializing Configuration"
    
    read -p "Docker Hub Username [$DOCKER_USERNAME]: " input
    DOCKER_USERNAME="${input:-$DOCKER_USERNAME}"
    
    read -p "GitHub Repository URL [$GITHUB_REPO]: " input
    GITHUB_REPO="${input:-$GITHUB_REPO}"
    
    read -p "Domain Name [$DOMAIN]: " input
    DOMAIN="${input:-$DOMAIN}"
    
    read -p "Slack Webhook URL (optional) [$SLACK_WEBHOOK]: " input
    SLACK_WEBHOOK="${input:-$SLACK_WEBHOOK}"
    
    # Save configuration
    cat > deployment.conf << EOF
DOCKER_USERNAME="$DOCKER_USERNAME"
GITHUB_REPO="$GITHUB_REPO"
DOMAIN="$DOMAIN"
SLACK_WEBHOOK="$SLACK_WEBHOOK"
DEPLOYMENT_DATE="$(date)"
EOF
    
    print_success "Configuration saved to deployment.conf"
}

# Setup K3s cluster
setup_k3s_cluster() {
    print_step "Setting up K3s Cluster"
    
    if ! command -v k3s &> /dev/null; then
        print_warning "K3s not found. Installing..."
        curl -sfL https://get.k3s.io | sh -
    fi
    
    # Verify K3s
    if k3s kubectl cluster-info &> /dev/null; then
        print_success "K3s cluster is running"
    else
        print_error "Failed to start K3s cluster"
        return 1
    fi
    
    # Wait for ready
    echo "⏳ Waiting for cluster to be ready..."
    k3s kubectl wait --for=condition=ready node --all --timeout=600s
    
    print_success "K3s cluster is ready"
}

# Deploy dependencies
deploy_dependencies() {
    print_step "Deploying Dependencies (PostgreSQL, Redis)"
    
    kubectl apply -f k8s/namespace-rbac.yaml
    kubectl apply -f k8s/configmap-secret.yaml
    kubectl apply -f k8s/dependencies.yaml
    
    echo "⏳ Waiting for dependencies..."
    kubectl wait --for=condition=ready pod -l app=postgres -n paperintel --timeout=300s || true
    kubectl wait --for=condition=ready pod -l app=redis -n paperintel --timeout=300s || true
    
    print_success "Dependencies deployed"
}

# Deploy PaperIntel application
deploy_application() {
    print_step "Deploying PaperIntel Application"
    
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service-ingress-hpa.yaml
    
    echo "⏳ Waiting for application to be ready..."
    kubectl wait --for=condition=ready pod -l app=paperintel -n paperintel --timeout=300s || true
    
    print_success "Application deployed"
}

# Deploy monitoring stack
deploy_monitoring() {
    print_step "Deploying Monitoring Stack"
    
    kubectl apply -f monitoring/prometheus.yaml
    kubectl apply -f monitoring/grafana.yaml
    
    echo "⏳ Waiting for monitoring components..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=300s || true
    kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=300s || true
    
    print_success "Monitoring stack deployed"
}

# Setup ArgoCD
setup_argocd() {
    print_step "Setting up ArgoCD"
    
    # Read GitHub token
    read -s -p "GitHub Personal Access Token: " GITHUB_TOKEN
    echo ""
    
    bash scripts/setup-argocd.sh \
        "$DOCKER_USERNAME" \
        "$GITHUB_REPO" \
        "$GITHUB_TOKEN" \
        "argocd.$DOMAIN"
    
    print_success "ArgoCD setup complete"
}

# Configure Jenkins
configure_jenkins() {
    print_step "Configuring Jenkins"
    
    echo ""
    echo "Manual Jenkins Configuration Required:"
    echo ""
    echo "1. Access Jenkins at: http://localhost:8080"
    echo "   (or install on your infrastructure)"
    echo ""
    echo "2. Create New Pipeline Job:"
    echo "   - Name: paperintel-pipeline"
    echo "   - Type: Pipeline"
    echo "   - Definition: Pipeline script from SCM"
    echo "   - SCM: Git"
    echo "   - Repository URL: $GITHUB_REPO"
    echo "   - Jenkinsfile: Jenkinsfile"
    echo ""
    echo "3. Add Credentials (Manage Jenkins → Manage Credentials):"
    echo "   - docker-username (Secret text)"
    echo "   - docker-password (Secret text)"
    echo "   - github-token (Secret text)"
    echo "   - argocd-server (Secret text)"
    echo "   - argocd-token (Secret text)"
    echo ""
    echo "4. Configure GitHub Webhook:"
    echo "   - URL: http://jenkins:8080/github-webhook/"
    echo "   - Trigger: Push events"
    echo ""
    read -p "Press ENTER when Jenkins is configured..."
    
    print_success "Jenkins configuration acknowledged"
}

# Verify deployment
verify_deployment() {
    print_step "Verifying Deployment"
    
    echo ""
    echo "🔍 Checking Cluster Status:"
    kubectl get nodes
    
    echo ""
    echo "📦 Checking Namespaces:"
    kubectl get namespaces
    
    echo ""
    echo "🚀 Checking Deployments:"
    kubectl get deployment -A
    
    echo ""
    echo "🔗 Checking Services:"
    kubectl get svc -A
    
    echo ""
    echo "📊 Checking HPA:"
    kubectl get hpa -n paperintel
    
    echo ""
    echo "💾 Checking Persistent Volumes:"
    kubectl get pv
    
    print_success "Verification complete"
}

# Display access information
display_access_info() {
    print_step "Access Information"
    
    echo ""
    echo "🌐 Web Applications:"
    echo "  - PaperIntel:  https://$DOMAIN"
    echo "  - ArgoCD:      https://argocd.$DOMAIN"
    echo "  - Grafana:     https://grafana.$DOMAIN"
    echo "  - Prometheus:  https://prometheus.$DOMAIN"
    echo ""
    echo "🔐 Port Forwards (if using localhost):"
    echo "  - ArgoCD:   kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "  - Grafana:  kubectl port-forward svc/grafana -n monitoring 3000:3000"
    echo "  - Prom:     kubectl port-forward svc/prometheus -n monitoring 9090:9090"
    echo ""
    echo "📝 Default Credentials:"
    echo "  - Grafana:  admin / grafana-admin-password-change-me"
    echo "  - ArgoCD:   admin / (check setup-argocd.sh output)"
    echo ""
    echo "📚 Useful Commands:"
    echo "  source scripts/cicd-commands.sh"
    echo "  get_cluster_status"
    echo "  deployment_status"
    echo "  argocd_status paperintel-app"
    echo ""
}

# Main flow
main() {
    print_banner
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    echo ""
    
    # Initialize configuration
    init_configuration
    echo ""
    
    # Ask if user wants to proceed
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 1
    fi
    echo ""
    
    # Execute deployment steps
    setup_k3s_cluster && echo "" || exit 1
    deploy_dependencies && echo "" || exit 1
    deploy_application && echo "" || exit 1
    deploy_monitoring && echo "" || exit 1
    setup_argocd && echo "" || exit 1
    configure_jenkins && echo "" || exit 1
    verify_deployment && echo "" || exit 1
    display_access_info
    
    echo ""
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║   ✅ Deployment Completed Successfully!                  ║"
    echo "║                                                           ║"
    echo "║  Your CI/CD pipeline is now ready:                       ║"
    echo "║  - Jenkins: Code checkout, test, build, push            ║"
    echo "║  - ArgoCD: Automatic deployment to K3s                  ║"
    echo "║  - Monitoring: Prometheus + Grafana                     ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Run main function
main
