#!/bin/bash
set -e

# 변수 설정
ECR_REPO="703094587997.dkr.ecr.us-west-2.amazonaws.com"
IMAGE_NAME="eks-assistant"
TAG="latest"
NAMESPACE="streamlit"
DEPLOYMENT_NAME="eks-assistant-app"

echo "===== 1. Kubernetes 배포 업데이트 ====="
# 이미지 업데이트 (이미지는 이미 ECR에 있다고 가정)
echo "Deployment 이미지 업데이트 중..."
kubectl set image deployment/${DEPLOYMENT_NAME} ${IMAGE_NAME}=${ECR_REPO}/${IMAGE_NAME}:${TAG} -n ${NAMESPACE}

# 배포 상태 확인
echo "배포 상태 확인 중..."
kubectl rollout status deployment/${DEPLOYMENT_NAME} -n ${NAMESPACE}

echo "===== 2. 배포 검증 ====="
# 파드 상태 확인
echo "파드 상태 확인 중..."
kubectl get pods -n ${NAMESPACE} -l app=eks-assistant

# 인그레스 주소 출력
echo "애플리케이션 접속 주소:"
INGRESS_HOSTNAME=$(kubectl get ingress eks-assistant-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "http://${INGRESS_HOSTNAME}"

echo "배포가 완료되었습니다."
