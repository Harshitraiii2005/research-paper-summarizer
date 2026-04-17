#!/bin/bash

# Quick reference commands for CI/CD pipeline management

# ============================================
# KUBERNETES CLUSTER COMMANDS
# ============================================

# Get cluster status
get_cluster_status() {
    echo "📊 Cluster Status:"
    kubectl get nodes
    echo ""
    echo "📦 Namespaces:"
    kubectl get namespaces
    echo ""
    echo "🔗 Services:"
    kubectl get svc -A --sort-by=.metadata.namespace
}

# Get pod logs
get_pod_logs() {
    local namespace=${1:-paperintel}
    local pod_name=${2:-}
    
    if [ -z "$pod_name" ]; then
        echo "📋 Pods in namespace: $namespace"
        kubectl get pods -n $namespace
        echo ""
        echo "Usage: get_pod_logs <namespace> <pod-name>"
    else
        echo "📖 Logs for pod: $pod_name"
        kubectl logs -n $namespace $pod_name -f
    fi
}

# ============================================
# ARGOCD COMMANDS
# ============================================

# Login to ArgoCD
argocd_login() {
    local server=${1:-localhost:8080}
    local username=${2:-admin}
    
    echo "🔐 Logging into ArgoCD..."
    argocd login $server --username $username --insecure
}

# Sync ArgoCD application
argocd_sync() {
    local app_name=${1:-paperintel-app}
    
    echo "🔄 Syncing ArgoCD application: $app_name"
    argocd app sync $app_name --grpc-web
    
    echo "⏳ Waiting for sync..."
    argocd app wait $app_name --grpc-web
}

# Get ArgoCD app status
argocd_status() {
    local app_name=${1:-paperintel-app}
    
    echo "📊 Status of application: $app_name"
    argocd app get $app_name --grpc-web
}

# Rollback to previous version
argocd_rollback() {
    local app_name=${1:-paperintel-app}
    local revision=${2:-0}
    
    echo "⏮️  Rolling back application: $app_name to revision: $revision"
    argocd app rollback $app_name $revision --grpc-web
}

# ============================================
# JENKINS COMMANDS
# ============================================

# Get Jenkins logs
jenkins_logs() {
    echo "📖 Jenkins logs (last 50 lines):"
    docker logs $(docker ps | grep jenkins | awk '{print $1}') | tail -50
}

# Trigger Jenkins job
jenkins_trigger() {
    local job_name=${1:-paperintel-pipeline}
    local jenkins_url=${2:-http://localhost:8080}
    
    echo "🚀 Triggering Jenkins job: $job_name"
    curl -X POST "${jenkins_url}/job/${job_name}/build" \
        --user admin:$JENKINS_TOKEN
}

# ============================================
# MONITORING COMMANDS
# ============================================

# Port forward to Grafana
grafana_port_forward() {
    echo "🌐 Forwarding Grafana port..."
    kubectl port-forward -n monitoring svc/grafana 3000:3000
    echo "Access: http://localhost:3000"
}

# Port forward to Prometheus
prometheus_port_forward() {
    echo "🌐 Forwarding Prometheus port..."
    kubectl port-forward -n monitoring svc/prometheus 9090:9090
    echo "Access: http://localhost:9090"
}

# Port forward to ArgoCD
argocd_port_forward() {
    echo "🌐 Forwarding ArgoCD port..."
    kubectl port-forward -n argocd svc/argocd-server 8080:443
    echo "Access: https://localhost:8080"
}

# Check alerts
check_alerts() {
    echo "🚨 Active Alerts:"
    kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
    sleep 2
    curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {alertname, state, labels}'
    pkill -f "port-forward"
}

# ============================================
# DEPLOYMENT COMMANDS
# ============================================

# Scale deployment
scale_deployment() {
    local deployment=${1:-paperintel}
    local replicas=${2:-3}
    local namespace=${3:-paperintel}
    
    echo "📊 Scaling $deployment to $replicas replicas"
    kubectl scale deployment $deployment -n $namespace --replicas=$replicas
}

# Restart deployment
restart_deployment() {
    local deployment=${1:-paperintel}
    local namespace=${2:-paperintel}
    
    echo "🔄 Restarting deployment: $deployment"
    kubectl rollout restart deployment/$deployment -n $namespace
    
    echo "⏳ Waiting for rollout..."
    kubectl rollout status deployment/$deployment -n $namespace
}

# Get deployment status
deployment_status() {
    local namespace=${1:-paperintel}
    
    echo "📊 Deployment Status in namespace: $namespace"
    kubectl get deployment -n $namespace
    echo ""
    echo "🔄 Rollout Status:"
    kubectl rollout status deployment/paperintel -n $namespace
}

# ============================================
# DEBUGGING COMMANDS
# ============================================

# Get resource usage
resource_usage() {
    echo "💾 Node Resource Usage:"
    kubectl top nodes
    echo ""
    echo "💾 Pod Resource Usage (paperintel):"
    kubectl top pods -n paperintel
}

# Describe resource
describe_resource() {
    local resource_type=${1:-pod}
    local resource_name=${2:-}
    local namespace=${3:-paperintel}
    
    if [ -z "$resource_name" ]; then
        echo "Usage: describe_resource <type> <name> [namespace]"
        echo "Examples:"
        echo "  describe_resource pod paperintel-xyz paperintel"
        echo "  describe_resource deployment paperintel paperintel"
    else
        kubectl describe $resource_type $resource_name -n $namespace
    fi
}

# Get pod shell access
pod_shell() {
    local pod_name=${1:-}
    local namespace=${2:-paperintel}
    
    if [ -z "$pod_name" ]; then
        echo "📋 Pods in namespace: $namespace"
        kubectl get pods -n $namespace
        echo ""
        echo "Usage: pod_shell <pod-name> [namespace]"
    else
        echo "🔌 Connecting to pod: $pod_name"
        kubectl exec -it $pod_name -n $namespace -- /bin/bash
    fi
}

# ============================================
# BACKUP & RESTORE COMMANDS
# ============================================

# Backup database
backup_database() {
    local backup_file=${1:-paperintel-backup-$(date +%Y%m%d-%H%M%S).sql}
    
    echo "💾 Backing up database to: $backup_file"
    kubectl exec -n paperintel statefulset/postgres -- \
        pg_dump -U paperintel paperintel > $backup_file
    
    echo "✅ Backup completed"
}

# Restore database
restore_database() {
    local backup_file=${1:-}
    
    if [ -z "$backup_file" ]; then
        echo "Usage: restore_database <backup-file>"
    else
        echo "📥 Restoring database from: $backup_file"
        kubectl exec -i -n paperintel statefulset/postgres -- \
            psql -U paperintel paperintel < $backup_file
        
        echo "✅ Restore completed"
    fi
}

# ============================================
# CLEANUP COMMANDS
# ============================================

# Clean up old images from DockerHub (requires manual intervention)
cleanup_docker_images() {
    local username=${1:-}
    
    if [ -z "$username" ]; then
        echo "Usage: cleanup_docker_images <docker-username>"
    else
        echo "🧹 Cleaning up Docker images for user: $username"
        echo "⚠️  Please manually remove old tags from:"
        echo "   https://hub.docker.com/r/$username/paperintel/tags"
    fi
}

# Delete old logs
cleanup_logs() {
    local namespace=${1:-paperintel}
    
    echo "🧹 Clearing logs in namespace: $namespace"
    kubectl logs -n $namespace --all-containers=true \
        --timestamps=true --since=720h | wc -l
    
    echo "✅ Logs cleanup completed"
}

# ============================================
# MAIN MENU
# ============================================

show_help() {
    echo "🔧 PaperIntel CI/CD Pipeline Management"
    echo ""
    echo "Available Commands:"
    echo ""
    echo "📊 Cluster Management:"
    echo "  get_cluster_status               - Get overall cluster status"
    echo "  get_pod_logs <ns> <pod>          - Get pod logs"
    echo "  resource_usage                   - Show resource usage"
    echo "  describe_resource <type> <name>  - Describe resource"
    echo "  pod_shell <pod-name>             - Connect to pod shell"
    echo ""
    echo "🔄 Deployment:"
    echo "  deployment_status [ns]           - Check deployment status"
    echo "  scale_deployment <dep> <replicas> - Scale deployment"
    echo "  restart_deployment <dep>         - Restart deployment"
    echo ""
    echo "🔐 ArgoCD:"
    echo "  argocd_login [server] [user]     - Login to ArgoCD"
    echo "  argocd_status [app]              - Get app status"
    echo "  argocd_sync [app]                - Sync application"
    echo "  argocd_rollback [app] [rev]      - Rollback application"
    echo "  argocd_port_forward              - Forward to ArgoCD"
    echo ""
    echo "🐳 Jenkins:"
    echo "  jenkins_logs                     - Get Jenkins logs"
    echo "  jenkins_trigger [job]            - Trigger Jenkins job"
    echo ""
    echo "📊 Monitoring:"
    echo "  grafana_port_forward             - Forward to Grafana"
    echo "  prometheus_port_forward          - Forward to Prometheus"
    echo "  check_alerts                     - Check active alerts"
    echo ""
    echo "💾 Backup & Restore:"
    echo "  backup_database [file]           - Backup database"
    echo "  restore_database <file>          - Restore database"
    echo ""
    echo "🧹 Cleanup:"
    echo "  cleanup_docker_images <user>     - Clean Docker images"
    echo "  cleanup_logs [ns]                - Clean logs"
    echo ""
    echo "Usage: source this script and call functions"
    echo "Example: get_cluster_status"
}

# Display help if sourced with no arguments
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    show_help
fi
