# EKS Assistant

AWS EKS 클러스터 관리를 위한 웹 기반 도우미 애플리케이션입니다.

## 기능

- EKS 클러스터 정보 조회 및 관리
- Bedrock 모델 목록 조회 및 테스트
- AWS 자격 증명 테스트

## 파일 구조

```
streamlit/
├── app.py                           # Streamlit 애플리케이션 코드
├── Dockerfile                       # Docker 이미지 빌드 설정
├── requirements.txt                 # Python 패키지 의존성
├── deploy-eks-assistant.sh          # 전체 배포 스크립트 (Docker + Kubernetes)
├── deploy-eks-assistant-kubectl-only.sh  # Kubernetes 배포만 수행하는 스크립트
├── k8s-manifests.yaml               # Kubernetes 리소스 정의 파일
└── README.md                        # 프로젝트 설명 및 사용 방법
```

## 배포 방법

### 전체 배포 (Docker + Kubernetes)

Docker가 설치된 환경에서 다음 스크립트를 실행합니다:

```bash
cd streamlit
./deploy-eks-assistant.sh
```

이 스크립트는 다음 작업을 수행합니다:
1. Docker 이미지 빌드
2. ECR 로그인
3. 이미지 태깅 및 푸시
4. Kubernetes 배포 업데이트
5. 배포 상태 확인

### Kubernetes 배포만 수행

이미지가 이미 ECR에 있는 경우 다음 스크립트를 실행합니다:

```bash
cd streamlit
./deploy-eks-assistant-kubectl-only.sh
```

이 스크립트는 다음 작업을 수행합니다:
1. Kubernetes 배포 업데이트
2. 배포 상태 확인

### 처음부터 배포하기

처음 배포하는 경우 Kubernetes 리소스를 생성해야 합니다:

```bash
kubectl apply -f k8s-manifests.yaml
```

그런 다음 배포 스크립트를 실행합니다:

```bash
./deploy-eks-assistant.sh
```

## 접속 방법

배포가 완료되면 다음 명령어로 접속 URL을 확인할 수 있습니다:

```bash
kubectl get ingress eks-assistant-ingress -n streamlit -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## 필요한 IAM 권한

애플리케이션이 제대로 작동하려면 다음 IAM 권한이 필요합니다:

1. EKS 권한:
   - eks:ListClusters
   - eks:DescribeCluster
   - eks:ListNodegroups
   - eks:DescribeNodegroup

2. Bedrock 권한:
   - bedrock:ListFoundationModels
   - bedrock:GetFoundationModel
   - bedrock:InvokeModel
   - bedrock:InvokeModelWithResponseStream

3. S3 권한:
   - s3:ListBuckets
   - s3:GetObject
   - s3:PutObject

## 문제 해결

문제가 발생하면 다음 명령어로 로그를 확인하세요:

```bash
kubectl logs -n streamlit $(kubectl get pods -n streamlit -l app=eks-assistant -o jsonpath='{.items[0].metadata.name}')
```
