#!/bin/bash
set -e

# 변수 설정
ECR_REPO="703094587997.dkr.ecr.us-west-2.amazonaws.com"
IMAGE_NAME="eks-assistant"
TAG="simple-v1"
NAMESPACE="streamlit"
DEPLOYMENT_NAME="eks-assistant-app"
REGION="us-west-2"

echo "===== 1. Docker 이미지 빌드 및 푸시 ====="
# Docker 이미지 빌드
echo "Docker 이미지 빌드 중..."
docker build -t ${IMAGE_NAME}:${TAG} -f Dockerfile .

# ECR 로그인
echo "ECR 로그인 중..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

# 이미지 태깅
echo "이미지 태깅 중..."
docker tag ${IMAGE_NAME}:${TAG} ${ECR_REPO}/${IMAGE_NAME}:${TAG}

# 이미지 푸시
echo "이미지 푸시 중..."
docker push ${ECR_REPO}/${IMAGE_NAME}:${TAG}

echo "===== 2. Kubernetes 배포 업데이트 ====="
# 이미지 업데이트
echo "Deployment 이미지 업데이트 중..."
kubectl set image deployment/${DEPLOYMENT_NAME} ${IMAGE_NAME}=${ECR_REPO}/${IMAGE_NAME}:${TAG} -n ${NAMESPACE}

# 배포 상태 확인
echo "배포 상태 확인 중..."
kubectl rollout status deployment/${DEPLOYMENT_NAME} -n ${NAMESPACE}

echo "===== 3. 배포 검증 ====="
# 파드 상태 확인
echo "파드 상태 확인 중..."
kubectl get pods -n ${NAMESPACE} -l app=eks-assistant

# 인그레스 주소 출력
echo "애플리케이션 접속 주소:"
INGRESS_HOSTNAME=$(kubectl get ingress eks-assistant-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "http://${INGRESS_HOSTNAME}"

echo "===== 4. 로그 확인 ====="
echo "최신 파드의 로그 확인 중..."
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=eks-assistant -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=10

echo "배포가 완료되었습니다."
echo "애플리케이션에 접속하려면 다음 URL을 사용하세요: http://${INGRESS_HOSTNAME}"
