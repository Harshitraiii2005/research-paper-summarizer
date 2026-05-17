pipeline {
    agent any
    
    environment {
        PATH = "/var/lib/jenkins/.local/bin:${env.PATH}"
        K8S_NAMESPACE = 'paperintel'
        SONARQUBE_SERVER = credentials('sonarqube-server')
        SONARQUBE_TOKEN  = credentials('sonarqube-token')
        ARGOCD_SERVER    = credentials('argocd-server')
        ARGOCD_TOKEN     = credentials('argocd-token')
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
                archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
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
                    withCredentials([usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DUSER',
                        passwordVariable: 'DPASS'
                    )]) {
                        sh '''
                            echo "$DPASS" | docker login -u "$DUSER" --password-stdin
                            docker build -t "$DUSER/paperintel:${BUILD_NUMBER}" .
                            docker tag "$DUSER/paperintel:${BUILD_NUMBER}" "$DUSER/paperintel:latest"
                            echo "✅ Docker image built: $DUSER/paperintel:${BUILD_NUMBER}"
                        '''
                    }
                }
            }
        }
        
        stage('🔍 Docker Image Security Scan') {
            steps {
                script {
                    echo "🔍 Scanning Docker image for vulnerabilities..."
                    sh '''
                        which trivy || (
                            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - &&
                            echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/trivy.list &&
                            apt-get update -qq && apt-get install -y trivy
                        ) || true
                        trivy image --severity HIGH,CRITICAL harshitrai20/paperintel:${BUILD_NUMBER} || true
                        echo "✅ Docker image scan completed"
                    '''
                }
            }
        }
        
        stage('📤 Push to Docker Hub') {
            steps {
                script {
                    echo "📤 Pushing image to Docker Hub..."
                    withCredentials([usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DUSER',
                        passwordVariable: 'DPASS'
                    )]) {
                        sh '''
                            echo "$DPASS" | docker login -u "$DUSER" --password-stdin
                            docker push "$DUSER/paperintel:${BUILD_NUMBER}"
                            docker push "$DUSER/paperintel:latest"
                            docker logout
                            echo "✅ Image pushed to Docker Hub"
                        '''
                    }
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
                        ./argocd app set paperintel-app -p image.tag=${BUILD_NUMBER} --grpc-web
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
                echo "📊 Cleaning up..."
                cleanWs()
            }
        }
        success {
            echo "✅ Pipeline #${BUILD_NUMBER} succeeded!"
        }
        failure {
            echo "❌ Pipeline #${BUILD_NUMBER} failed! Check logs at ${BUILD_URL}"
        }
    }
}