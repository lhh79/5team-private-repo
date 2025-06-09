import streamlit as st
import boto3
import pandas as pd
import subprocess
import tempfile
import os
from kubernetes import client, config
from datetime import datetime, timezone
import time

def render_kubectl_guide_sidebar():
    """kubectl 명령어 가이드 사이드바를 렌더링합니다."""
    st.markdown("#### 🔧 kubectl 명령어 가이드")
    
    # Pod 관련 명령어
    with st.expander("📦 Pod 관리", expanded=False):
        st.code("kubectl get pods", language="bash")
        st.code("kubectl get pods -o wide", language="bash")
        st.code("kubectl describe pod <pod-name>", language="bash")
        st.code("kubectl logs <pod-name>", language="bash")
        st.code("kubectl exec -it <pod-name> -- /bin/bash", language="bash")
        st.code("kubectl delete pod <pod-name>", language="bash")
    
    # Deployment 관련 명령어
    with st.expander("🚀 Deployment 관리", expanded=False):
        st.code("kubectl get deployments", language="bash")
        st.code("kubectl describe deployment <deployment-name>", language="bash")
        st.code("kubectl scale deployment <deployment-name> --replicas=3", language="bash")
        st.code("kubectl rollout status deployment/<deployment-name>", language="bash")
        st.code("kubectl rollout restart deployment/<deployment-name>", language="bash")
        st.code("kubectl rollout undo deployment/<deployment-name>", language="bash")
    
    # Service 관련 명령어
    with st.expander("🌐 Service 관리", expanded=False):
        st.code("kubectl get services", language="bash")
        st.code("kubectl get svc", language="bash")
        st.code("kubectl describe service <service-name>", language="bash")
        st.code("kubectl port-forward service/<service-name> 8080:80", language="bash")
        st.code("kubectl expose deployment <deployment-name> --port=80 --type=LoadBalancer", language="bash")
    
    # 클러스터 정보 명령어
    with st.expander("📊 클러스터 정보", expanded=False):
        st.code("kubectl cluster-info", language="bash")
        st.code("kubectl get nodes", language="bash")
        st.code("kubectl get nodes -o wide", language="bash")
        st.code("kubectl top nodes", language="bash")
        st.code("kubectl top pods", language="bash")
        st.code("kubectl get namespaces", language="bash")
    
    # ConfigMap & Secret 명령어
    with st.expander("🔐 ConfigMap & Secret", expanded=False):
        st.code("kubectl get configmaps", language="bash")
        st.code("kubectl get secrets", language="bash")
        st.code("kubectl describe configmap <configmap-name>", language="bash")
        st.code("kubectl describe secret <secret-name>", language="bash")
        st.code("kubectl create secret generic <secret-name> --from-literal=key=value", language="bash")
    
    # 리소스 관리 명령어
    with st.expander("📋 리소스 관리", expanded=False):
        st.code("kubectl get all", language="bash")
        st.code("kubectl get all -n <namespace>", language="bash")
        st.code("kubectl apply -f <file.yaml>", language="bash")
        st.code("kubectl delete -f <file.yaml>", language="bash")
        st.code("kubectl edit deployment <deployment-name>", language="bash")
        st.code("kubectl patch deployment <deployment-name> -p '{\"spec\":{\"replicas\":5}}'", language="bash")

def get_direct_k8s_pods(cluster_name, region='us-west-2'):
    """직접 Kubernetes API를 사용하여 Pod 정보를 조회합니다."""
    try:
        with st.spinner(f"클러스터 '{cluster_name}'의 Pod 정보를 직접 조회하는 중..."):
            # 인증 방식 시도
            try:
                # 먼저 in-cluster 설정 시도 (클러스터 내부에서 실행 중일 때)
                config.load_incluster_config()
                st.info("클러스터 내부 설정을 사용합니다.")
            except config.ConfigException:
                try:
                    # 환경 변수에서 kubeconfig 경로 확인
                    if 'KUBECONFIG' in os.environ:
                        config.load_kube_config()
                        st.info(f"환경 변수 KUBECONFIG를 사용합니다: {os.environ['KUBECONFIG']}")
                    else:
                        # AWS CLI를 통해 kubeconfig 생성
                        temp_dir = tempfile.mkdtemp()
                        temp_kubeconfig_path = os.path.join(temp_dir, 'kubeconfig')
                        
                        update_kubeconfig_command = [
                            'aws', 'eks', 'update-kubeconfig',
                            '--name', cluster_name,
                            '--region', region,
                            '--kubeconfig', temp_kubeconfig_path
                        ]
                        
                        result = subprocess.run(update_kubeconfig_command, capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            st.error(f"kubeconfig 생성 실패: {result.stderr}")
                            return []
                        
                        # kubeconfig 파일 로드
                        config.load_kube_config(config_file=temp_kubeconfig_path)
                        st.info(f"임시 kubeconfig를 생성했습니다: {temp_kubeconfig_path}")
                except Exception as e:
                    st.error(f"Kubernetes 설정 로드 실패: {e}")
                    return []
            
            # API 클라이언트 생성
            v1 = client.CoreV1Api()
            
            # 모든 네임스페이스의 Pod 조회
            try:
                pods = v1.list_pod_for_all_namespaces(watch=False)
                st.success(f"총 {len(pods.items)}개의 Pod를 발견했습니다.")
            except client.exceptions.ApiException as e:
                if e.status == 401:
                    st.error("인증 오류: Kubernetes API에 접근할 권한이 없습니다.")
                    return []
                else:
                    st.error(f"Kubernetes API 오류: {e}")
                    return []
            
            # 현재 시간 (UTC)
            now = datetime.now(timezone.utc)
            
            pod_list = []
            for pod in pods.items:
                # Pod 생성 시간으로부터 경과 시간 계산
                age = "N/A"
                if pod.metadata.creation_timestamp:
                    age_seconds = (now - pod.metadata.creation_timestamp).total_seconds()
                    if age_seconds < 60:
                        age = f"{int(age_seconds)}s"
                    elif age_seconds < 3600:
                        age = f"{int(age_seconds/60)}m"
                    elif age_seconds < 86400:
                        age = f"{int(age_seconds/3600)}h"
                    else:
                        age = f"{int(age_seconds/86400)}d"
                
                # 재시작 횟수 계산
                restarts = 0
                if pod.status.container_statuses:
                    restarts = sum(container.restart_count for container in pod.status.container_statuses)
                
                # Pod 정보 구성
                pod_info = {
                    'Name': pod.metadata.name,
                    'Namespace': pod.metadata.namespace,
                    'Status': pod.status.phase,
                    'Node': pod.spec.node_name if pod.spec.node_name else 'N/A',
                    'IP': pod.status.pod_ip if pod.status.pod_ip else 'N/A',
                    'Restarts': restarts,
                    'Age': age
                }
                
                pod_list.append(pod_info)
            
            return pod_list
    except Exception as e:
        st.error(f"Pod 정보 직접 조회 중 오류 발생: {e}")
        return []

def get_simulated_pods(cluster_name, has_nodes=True):
    """인증 오류 시 시뮬레이션된 Pod 정보를 생성합니다."""
    # 노드가 없는 클러스터는 Pod 정보도 없음
    if not has_nodes:
        return []
        
    st.warning("시뮬레이션된 Pod 정보를 표시합니다. (실제 데이터가 아님)")
    
    # 현재 시간
    now = datetime.now()
    
    # 기본 시스템 Pod 생성
    pod_list = [
        {
            'Name': f'kube-proxy-{i}',
            'Namespace': 'kube-system',
            'Status': 'Running',
            'Node': f'node-{i % 3 + 1}',
            'IP': f'10.0.{i}.{i+10}',
            'Restarts': i % 3,
            'Age': '10d'
        } for i in range(1, 4)
    ]
    
    # CoreDNS Pod 추가
    pod_list.extend([
        {
            'Name': f'coredns-{i}abc{i}',
            'Namespace': 'kube-system',
            'Status': 'Running',
            'Node': f'node-{i % 3 + 1}',
            'IP': f'10.0.{i}.{i+20}',
            'Restarts': 0,
            'Age': '10d'
        } for i in range(1, 3)
    ])
    
    # 클러스터 이름에 따라 추가 Pod 생성
    if 'EKS-GNSer' in cluster_name:
        # 다양한 네임스페이스의 Pod 추가
        namespaces = ['streamlit', 'monitoring', 'logging', 'database', 'api', 'frontend', 'backend', 'auth', 'cache']
        pod_prefixes = {
            'streamlit': 'eks-assistant-app',
            'monitoring': 'monitoring-agent',
            'logging': 'logging-collector',
            'database': 'database',
            'api': 'api-service',
            'frontend': 'frontend-app',
            'backend': 'backend-service',
            'auth': 'auth-service',
            'cache': 'redis-cache'
        }
        
        # 각 네임스페이스별로 여러 Pod 생성
        for namespace, prefix in pod_prefixes.items():
            for i in range(1, 8):  # 각 네임스페이스별 7개 Pod
                node_id = f'node-{i % 3 + 1}'
                
                # Pod 정보 생성
                pod_list.append({
                    'Name': f'{prefix}-{i}abcdef{i}',
                    'Namespace': namespace,
                    'Status': 'Running',
                    'Node': node_id,
                    'IP': f'10.0.{len(pod_list) % 255}.{len(pod_list) % 255}',
                    'Restarts': i % 4,
                    'Age': f'{i}d'
                })
    
    return pod_list

def show_pod_monitoring(aws_clients=None):
    """Pod 모니터링 페이지를 표시합니다."""
    st.title("EKS 클러스터 Pod 모니터링")
    st.write("이 페이지에서는 EKS 클러스터의 Pod 정보를 조회합니다.")
    
    # AWS 클라이언트 초기화
    try:
        if aws_clients is None:
            eks_client = boto3.client('eks', region_name='us-west-2')
            st.success("AWS 클라이언트 초기화 성공")
        else:
            eks_client = aws_clients['eks']
    except Exception as e:
        st.error(f"AWS 클라이언트 초기화 실패: {e}")
        return
    
    # 클러스터 목록 조회
    try:
        response = eks_client.list_clusters()
        clusters = response['clusters']
        if not clusters:
            st.warning("사용 가능한 EKS 클러스터가 없습니다.")
            return
        st.success(f"{len(clusters)}개의 클러스터를 발견했습니다.")
    except Exception as e:
        st.error(f"클러스터 목록 조회 실패: {e}")
        return
    
    # 클러스터 선택
    selected_cluster = st.selectbox("클러스터 선택", clusters)
    
    if selected_cluster:
        st.write(f"선택된 클러스터: **{selected_cluster}**")
        
        # 클러스터 정보 자동 조회
        try:
            with st.spinner(f"클러스터 '{selected_cluster}' 정보를 조회하는 중..."):
                cluster_info = eks_client.describe_cluster(name=selected_cluster)
                st.subheader("클러스터 정보")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("상태", cluster_info['cluster']['status'])
                with col2:
                    st.metric("버전", cluster_info['cluster']['version'])
                with col3:
                    st.metric("리전", "us-west-2")
                    
                # 노드그룹 정보 조회
                nodegroups_response = eks_client.list_nodegroups(clusterName=selected_cluster)
                nodegroups = nodegroups_response.get('nodegroups', [])
                
                has_nodes = False  # 노드 존재 여부 플래그
                
                if nodegroups:
                    st.subheader("노드그룹 정보")
                    for ng_name in nodegroups:
                        ng_detail = eks_client.describe_nodegroup(
                            clusterName=selected_cluster,
                            nodegroupName=ng_name
                        )
                        ng = ng_detail['nodegroup']
                        
                        st.write(f"**노드그룹**: {ng_name}")
                        st.write(f"상태: {ng['status']}")
                        st.write(f"인스턴스 타입: {', '.join(ng.get('instanceTypes', ['N/A']))}")
                        st.write(f"용량: 최소 {ng['scalingConfig']['minSize']}, 최대 {ng['scalingConfig']['maxSize']}, 현재 {ng['scalingConfig']['desiredSize']}")
                        st.write("---")
                        
                        # 현재 노드 수가 0보다 크면 노드가 있는 것으로 판단
                        if ng['scalingConfig']['desiredSize'] > 0:
                            has_nodes = True
                else:
                    st.warning("이 클러스터에는 노드그룹이 없습니다.")
                
                # Pod 정보 자동 조회 - 노드가 있는 경우에만
                st.subheader("Pod 정보")
                
                if not has_nodes:
                    st.warning(f"클러스터 '{selected_cluster}'에 노드가 없습니다. Pod 정보를 조회할 수 없습니다.")
                    st.info("노드가 없는 클러스터에서는 Pod가 실행될 수 없습니다. EKS 콘솔에서 노드그룹을 추가하세요.")
                else:
                    # 노드가 있는 경우에만 Pod 정보 조회
                    pods = get_direct_k8s_pods(selected_cluster)
                    
                    # 직접 조회 실패 시 시뮬레이션된 데이터 사용
                    if not pods:
                        pods = get_simulated_pods(selected_cluster, has_nodes=True)
                    
                    if pods:
                        # 데이터프레임 생성
                        pods_df = pd.DataFrame(pods)
                        
                        # 네임스페이스 필터 추가
                        all_namespaces = ['모든 네임스페이스'] + sorted(pods_df['Namespace'].unique().tolist())
                        selected_namespace = st.selectbox("네임스페이스 필터", all_namespaces)
                        
                        # 필터링된 데이터프레임
                        if selected_namespace != '모든 네임스페이스':
                            filtered_pods_df = pods_df[pods_df['Namespace'] == selected_namespace]
                            st.info(f"{selected_namespace} 네임스페이스의 Pod {len(filtered_pods_df)}개를 표시합니다.")
                        else:
                            filtered_pods_df = pods_df
                            st.info(f"모든 네임스페이스의 Pod {len(filtered_pods_df)}개를 표시합니다.")
                        
                        # 데이터프레임 표시
                        st.dataframe(filtered_pods_df, use_container_width=True, height=600)
                        
                        # 네임스페이스별 Pod 수 요약
                        st.subheader("네임스페이스별 Pod 수")
                        namespace_counts = pods_df['Namespace'].value_counts().reset_index()
                        namespace_counts.columns = ['네임스페이스', 'Pod 수']
                        st.dataframe(namespace_counts, use_container_width=True)
                        
                        # Pod 상태 요약
                        st.subheader("Pod 상태 요약")
                        status_counts = pods_df['Status'].value_counts().reset_index()
                        status_counts.columns = ['상태', 'Pod 수']
                        st.dataframe(status_counts, use_container_width=True)
                
        except Exception as e:
            st.error(f"클러스터 정보 조회 실패: {e}")
            import traceback
            st.error(traceback.format_exc())

def show_home():
    """홈 화면을 표시합니다."""
    st.title("EKS 클러스터 운영 어시스턴트")
    
    st.markdown("""
    ## 환영합니다!
    
    이 애플리케이션은 AWS EKS 클러스터를 효율적으로 관리하고 모니터링하기 위한 도구입니다.
    
    왼쪽 사이드바에서 원하는 기능을 선택하세요:
    
    - **EKS 클러스터 Pod 모니터링**: 클러스터의 Pod 정보를 조회하고 모니터링합니다.
    - **kubectl 명령어 가이드**: 자주 사용하는 kubectl 명령어를 확인할 수 있습니다.
    
    ### 주요 기능
    
    - 클러스터 정보 조회
    - 노드그룹 정보 확인
    - Pod 모니터링
    - 네임스페이스별 Pod 수 확인
    - Pod 상태 요약
    """)
    
    st.info("시작하려면 왼쪽 사이드바에서 메뉴를 선택하세요.")

def main():
    st.set_page_config(page_title="EKS 클러스터 운영 어시스턴트", page_icon="🚀", layout="wide")
    
    # 세션 상태 초기화
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    
    # AWS 클라이언트 초기화
    try:
        aws_clients = {'eks': boto3.client('eks', region_name='us-west-2')}
    except Exception as e:
        aws_clients = None
    
    # 사이드바
    with st.sidebar:
        st.title("EKS 어시스턴트")
        st.markdown("---")
        
        # 네비게이션 메뉴
        st.markdown("## 📋 메뉴")
        
        if st.button("🏠 홈", key="home_btn"):
            st.session_state.page = 'home'
            st.rerun()
        
        if st.button("📊 EKS 클러스터 Pod 모니터링", key="pod_monitoring_btn"):
            st.session_state.page = 'pod_monitoring'
            st.rerun()
        
        st.markdown("---")
        
        # kubectl 가이드
        render_kubectl_guide_sidebar()
    
    # 메인 콘텐츠
    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'pod_monitoring':
        show_pod_monitoring(aws_clients)

if __name__ == "__main__":
    main()
