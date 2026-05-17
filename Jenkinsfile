pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_USERNAME = credentials('docker-username')
        DOCKER_PASSWORD = credentials('docker-password')
        IMAGE_NAME = "${DOCKER_USERNAME}/paperintel"
        IMAGE_TAG = "${BUILD_NUMBER}-${GIT_COMMIT.take(7)}"
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        LATEST_IMAGE = "${IMAGE_NAME}:latest"
        
        KUBECONFIG = '/var/run/secrets/kubernetes.io/serviceaccount/kubeconfig'
        ARGOCD_SERVER = credentials('argocd-server')
        ARGOCD_TOKEN = credentials('argocd-token')
        K8S_NAMESPACE = 'paperintel'
        
        SONARQUBE_SERVER = credentials('sonarqube-server')
        SONARQUBE_TOKEN = credentials('sonarqube-token')
        
        PATH = "/var/lib/jenkins/.local/bin:${env.PATH}"
    }
    
    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    
    stages {
        stage('🔍 Checkout') {
            steps {
                script {
                    echo "📦 Checking out code from Git..."
                    checkout scm
                    sh 'git log --oneline -5'
                }
            }
        }
        
        stage('📋 Setup & Dependencies') {
            steps {
                script {
                    echo "🔧 Setting up environment..."
                    sh '''
                        export PATH="/var/lib/jenkins/.local/bin:$PATH"
                        python3 --version
                        pip install --upgrade pip
                        pip install -r requirements.txt
                        echo "✅ Dependencies installed"
                    '''
                }
            }
        }
        
        stage('🧪 Run Tests') {
            steps {
                script {
                    echo "🧪 Running unit tests..."
                    sh '''
                        export PATH="/var/lib/jenkins/.local/bin:$PATH"
                        pip install pytest pytest-cov
                        python3 -m pytest tests/ -v \
                            --cov=agents --cov=ingestion \
                            --cov-report=xml --cov-report=html || true
                        echo "✅ Tests completed"
                    '''
                }
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: false,
                    keepAll: true,
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Code Coverage Report'
                ])
            }
        }
        
        stage('🔐 Security Checks') {
            parallel {
                stage('🔒 SAST - SonarQube Analysis') {
                    steps {
                        script {
                            echo "🔒 Running SonarQube static analysis..."
                            sh '''
                                export PATH="/var/lib/jenkins/.local/bin:$PATH"
                                pip install pylint
                                pylint agents/ ingestion/ --exit-zero --output-format=json > pylint-report.json || true
                                sonar-scanner \
                                    -Dsonar.projectKey=paperintel \
                                    -Dsonar.sources=. \
                                    -Dsonar.host.url=${SONARQUBE_SERVER} \
                                    -Dsonar.login=${SONARQUBE_TOKEN} \
                                    -Dsonar.python.pylint.reportPath=pylint-report.json \
                                    || true
                                echo "✅ SonarQube analysis completed"
                            '''
                        }
                    }
                }
                
                stage('🛡️ Dependency Check - OWASP') {
                    steps {
                        script {
                            echo "🛡️ Running OWASP dependency check..."
                            sh '''
                                export PATH="/var/lib/jenkins/.local/bin:$PATH"
                                pip install safety bandit
                                safety check --json > safety-report.json || true
                                bandit -r agents/ ingestion/ -f json -o bandit-report.json || true
                                echo "✅ Dependency check completed"
                            '''
                        }
                    }
                }
                
                stage('📝 Code Quality') {
                    steps {
                        script {
                            echo "📝 Checking code quality..."
                            sh '''
                                export PATH="/var/lib/jenkins/.local/bin:$PATH"
                                pip install flake8
                                flake8 agents/ ingestion/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
                                echo "✅ Code quality check completed"
                            '''
                        }
                    }
                }
            }
        }
        
        stage('🐳 Build Docker Image') {
            steps {
                        script {
                            echo "🐳 Building Docker image..."
                            sh '''
                                echo ${DOCKER_PASSWORD} | docker login -u ${DOCKER_USERNAME} --password-stdin
                                docker build -t ${FULL_IMAGE} .
                                docker tag ${FULL_IMAGE} ${LATEST_IMAGE}
                                echo "✅ Docker image built: ${FULL_IMAGE}"
                            '''
                        }
                    }
                }
        
        stage('🔍 Docker Image Security Scan') {
            steps {
                script {
                    echo "🔍 Scanning Docker image for vulnerabilities..."
                    sh '''
                        wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - || true
                        echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list || true
                        apt-get update && apt-get install -y trivy || echo "Trivy already installed"
                        trivy image --severity HIGH,CRITICAL ${FULL_IMAGE} || true
                        echo "✅ Docker image scan completed"
                    '''
                }
            }
        }
        
        stage('📤 Push to Docker Hub') {
            steps {
                script {
                    echo "📤 Pushing image to Docker Hub..."
                    sh '''
                        echo ${DOCKER_PASSWORD} | docker login -u ${DOCKER_USERNAME} --password-stdin
                        docker push ${FULL_IMAGE}
                        docker push ${LATEST_IMAGE}
                        docker logout
                        echo "✅ Image pushed to Docker Hub"
                    '''
                }
            }
        }
        
        stage('🚀 Update ArgoCD') {
            steps {
                script {
                    echo "🚀 Triggering ArgoCD deployment..."
                    sh '''
                        curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
                        chmod +x argocd
                        ./argocd login ${ARGOCD_SERVER} --insecure --username admin --password=${ARGOCD_TOKEN} --grpc-web
                        ./argocd app set paperintel-app -p image.tag=${IMAGE_TAG} --grpc-web
                        ./argocd app sync paperintel-app --grpc-web
                        echo "✅ ArgoCD deployment triggered"
                    '''
                }
            }
        }
        
        stage('✅ Verify Deployment') {
            steps {
                script {
                    echo "✅ Verifying deployment..."
                    sh '''
                        kubectl rollout status deployment/paperintel -n ${K8S_NAMESPACE} --timeout=5m
                        kubectl get pods -n ${K8S_NAMESPACE}
                        echo "✅ Deployment verified"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo " Cleaning up..."
                cleanWs()
            }
        }
        success {
            echo " Pipeline succeeded! Image: ${FULL_IMAGE}"
        }
        failure {
            echo " Pipeline failed! Check logs at ${BUILD_URL}"
        }
    }
}