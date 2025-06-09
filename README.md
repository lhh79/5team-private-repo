# EKS Assistant

AWS EKS 클러스터 관리를 위한 웹 기반 도우미 애플리케이션입니다.

## 기능

- EKS 클러스터 정보 조회 및 관리
- 컴퓨트 노드 및 Pod 상태 모니터링
- Bedrock 모델 목록 조회 및 AI 어시스턴트 기능
- 세션 관리 및 DynamoDB 연동
- AWS 자격 증명 테스트

## 파일 구조

```
streamlit/
├── main.py                          # Streamlit 애플리케이션 메인 코드
├── Dockerfile                       # Docker 이미지 빌드 설정
├── requirements.txt                 # Python 패키지 의존성
├── deploy-eks-assistant.sh          # 전체 배포 스크립트 (Docker + Kubernetes)
├── deploy-eks-assistant-kubectl-only.sh  # Kubernetes 배포만 수행하는 스크립트
├── k8s-manifests.yaml               # Kubernetes 리소스 정의 파일
├── config.py                        # AWS 클라이언트 초기화 설정
├── eks_utils.py                     # EKS 관련 유틸리티 함수
├── compute_nodes_utils.py           # 컴퓨트 노드 정보 조회 유틸리티
├── bedrock_utils.py                 # Bedrock 모델 관련 유틸리티
├── kubernetes_utils.py              # Kubernetes 관련 유틸리티
├── permission_utils.py              # IAM 권한 관련 유틸리티
├── session_utils.py                 # 세션 관리 유틸리티
├── ui_components.py                 # UI 컴포넌트 렌더링 함수
├── create-dynamodb-table.py         # DynamoDB 테이블 생성 스크립트
├── iam-policy.json                  # IAM 정책 정의 파일
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

4. DynamoDB 권한:
   - dynamodb:CreateTable
   - dynamodb:PutItem
   - dynamodb:GetItem
   - dynamodb:DeleteItem
   - dynamodb:UpdateItem

## 문제 해결

문제가 발생하면 다음 명령어로 로그를 확인하세요:

```bash
kubectl logs -n streamlit $(kubectl get pods -n streamlit -l app=eks-assistant -o jsonpath='{.items[0].metadata.name}')
```

## 주요 기능

1. **EKS 클러스터 모니터링**
   - 클러스터 상태, 버전, 리전 정보 표시
   - 노드그룹 및 컴퓨트 노드 정보 조회

2. **컴퓨트 노드 관리**
   - 노드 상태 및 리소스 사용량 모니터링
   - 인스턴스 타입 및 버전 정보 확인

3. **Pod 모니터링**
   - Pod 상태 및 리소스 요청량 확인
   - 네임스페이스별 Pod 분포 확인

4. **AI 어시스턴트**
   - Bedrock 모델을 활용한 EKS 관련 질문 응답
   - 클러스터 컨텍스트 기반 맞춤형 답변 제공

5. **세션 관리**
   - DynamoDB를 활용한 세션 저장 및 복원
   - 사용자 설정 및 클러스터 정보 유지

6. **kubectl 가이드**
   - 일반적인 kubectl 명령어 가이드 제공
   - 문제 해결을 위한 명령어 추천
