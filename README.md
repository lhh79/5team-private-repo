# EKS 클러스터 운영 어시스턴트

AWS EKS 클러스터 관리 및 모니터링을 위한 웹 기반 도우미 애플리케이션입니다.

## 기능

- EKS 클러스터 정보 조회 및 관리
- 노드그룹 정보 확인
- Pod 상태 모니터링 및 필터링
- kubectl 명령어 가이드 제공

## 파일 구조

```
streamlit/
├── simple_app.py                    # Streamlit 애플리케이션 메인 코드
├── Dockerfile                       # Docker 이미지 빌드 설정
├── requirements.txt                 # Python 패키지 의존성
├── deploy-simple.sh                 # 배포 스크립트 (Docker + Kubernetes)
├── k8s-manifests.yaml               # Kubernetes 리소스 정의 파일
├── k8s-rbac.yaml                    # Kubernetes RBAC 권한 설정
└── README.md                        # 프로젝트 설명 및 사용 방법
```

## 배포 방법

### 전체 배포 (Docker + Kubernetes)

Docker가 설치된 환경에서 다음 스크립트를 실행합니다:

```bash
cd streamlit
./deploy-simple.sh
```

이 스크립트는 다음 작업을 수행합니다:
1. Docker 이미지 빌드
2. ECR 로그인
3. 이미지 태깅 및 푸시
4. Kubernetes 배포 업데이트
5. 배포 상태 확인

### 처음부터 배포하기

처음 배포하는 경우 Kubernetes 리소스를 생성해야 합니다:

```bash
kubectl apply -f k8s-manifests.yaml
kubectl apply -f k8s-rbac.yaml
```

그런 다음 배포 스크립트를 실행합니다:

```bash
./deploy-simple.sh
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

2. Kubernetes API 접근 권한:
   - Pod, Node, Namespace 리소스에 대한 읽기 권한

## 문제 해결

문제가 발생하면 다음 명령어로 로그를 확인하세요:

```bash
kubectl logs -n streamlit $(kubectl get pods -n streamlit -l app=eks-assistant -o jsonpath='{.items[0].metadata.name}')
```

Pod를 재시작하려면 다음 명령어를 사용하세요:

```bash
kubectl rollout restart deployment eks-assistant-app -n streamlit
```

## 주요 기능

1. **홈 화면**
   - 애플리케이션 소개 및 주요 기능 설명
   - 사용 방법 안내

2. **EKS 클러스터 Pod 모니터링**
   - 클러스터 상태, 버전, 리전 정보 표시
   - 노드그룹 정보 조회
   - Pod 상태 및 정보 모니터링
   - 네임스페이스별 Pod 필터링
   - 네임스페이스별 Pod 수 및 상태별 Pod 수 요약

3. **kubectl 명령어 가이드**
   - Pod 관리 명령어
   - Deployment 관리 명령어
   - Service 관리 명령어
   - 클러스터 정보 명령어
   - ConfigMap & Secret 명령어
   - 리소스 관리 명령어

## 사용 방법

1. 애플리케이션에 접속합니다.
2. 왼쪽 사이드바에서 "EKS 클러스터 Pod 모니터링" 메뉴를 클릭합니다.
3. 드롭다운 메뉴에서 조회할 클러스터를 선택합니다.
4. 클러스터 정보, 노드그룹 정보, Pod 정보가 자동으로 표시됩니다.
5. 네임스페이스 필터를 사용하여 특정 네임스페이스의 Pod만 볼 수 있습니다.
6. 왼쪽 사이드바의 kubectl 명령어 가이드를 참조하여 필요한 명령어를 확인할 수 있습니다.

## 참고 사항

- 노드가 없는 클러스터에서는 Pod 정보가 표시되지 않습니다.
- 인증 오류가 발생할 경우 시뮬레이션된 Pod 정보가 표시될 수 있습니다.
- 애플리케이션은 AWS CLI와 Kubernetes Python 클라이언트를 사용하여 정보를 조회합니다.
