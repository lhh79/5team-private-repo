#!/bin/bash

# 스크립트 실행 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 변수 설정
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="eks-assistant-integrated"
IMAGE_TAG="latest"
NAMESPACE="streamlit"
DEPLOYMENT_NAME="eks-assistant-integrated"
SERVICE_NAME="eks-assistant-integrated-service"
INGRESS_NAME="eks-assistant-integrated-ingress"
ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

# ECR 리포지토리 확인
echo "ECR 리포지토리 확인 중..."
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}

# ECR 로그인
echo "ECR 로그인 중..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URI}

# Docker 이미지 빌드 및 푸시
echo "Docker 이미지 빌드 중..."
docker build -t ${ECR_REPO_URI}:${IMAGE_TAG} .

echo "Docker 이미지 푸시 중..."
docker push ${ECR_REPO_URI}:${IMAGE_TAG}

# 네임스페이스 확인
kubectl get namespace $NAMESPACE > /dev/null 2>&1 || kubectl create namespace $NAMESPACE

# RBAC 설정 적용
echo "RBAC 설정 적용 중..."
kubectl apply -f k8s-rbac.yaml

# 기존 배포 확인 및 삭제 (서비스와 Ingress는 유지)
if kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE > /dev/null 2>&1; then
    echo "기존 배포 삭제 중..."
    kubectl delete deployment $DEPLOYMENT_NAME -n $NAMESPACE
fi

# 새 배포 생성
echo "새 배포 생성 중..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $DEPLOYMENT_NAME
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: $DEPLOYMENT_NAME
  template:
    metadata:
      labels:
        app: $DEPLOYMENT_NAME
    spec:
      serviceAccountName: eks-assistant-sa
      containers:
      - name: $DEPLOYMENT_NAME
        image: ${ECR_REPO_URI}:${IMAGE_TAG}
        imagePullPolicy: Always
        ports:
        - containerPort: 8501
        env:
        - name: AWS_DEFAULT_REGION
          value: "us-west-2"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
EOF

# 서비스가 없는 경우에만 생성
if ! kubectl get service $SERVICE_NAME -n $NAMESPACE > /dev/null 2>&1; then
    echo "서비스 생성 중..."
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: $SERVICE_NAME
  namespace: $NAMESPACE
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8501
  selector:
    app: $DEPLOYMENT_NAME
EOF
fi

# Ingress가 없는 경우에만 생성
if ! kubectl get ingress $INGRESS_NAME -n $NAMESPACE > /dev/null 2>&1; then
    echo "Ingress 생성 중..."
    cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: $INGRESS_NAME
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: "internet-facing"
    alb.ingress.kubernetes.io/target-type: "ip"
    alb.ingress.kubernetes.io/healthcheck-path: "/"
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: $SERVICE_NAME
            port:
              number: 80
EOF
fi

echo "배포 완료! 서비스 및 Ingress 상태 확인 중..."
kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE
kubectl get service $SERVICE_NAME -n $NAMESPACE
kubectl get ingress $INGRESS_NAME -n $NAMESPACE

echo "Ingress 주소:"
kubectl get ingress $INGRESS_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
echo ""
