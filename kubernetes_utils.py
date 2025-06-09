import streamlit as st
import base64
import tempfile
import yaml
import os
from datetime import datetime

def get_kubernetes_client(eks_client, cluster_name):
    """EKS 클러스터의 Kubernetes API 클라이언트를 설정합니다."""
    try:
        from kubernetes import client, config
        
        # 먼저 인클러스터 설정 시도 (서비스 계정 사용)
        try:
            st.info("인클러스터 인증을 시도합니다...")
            config.load_incluster_config()
            v1 = client.CoreV1Api()
            
            # 연결 테스트
            v1.list_namespace(limit=1)
            st.success("인클러스터 인증 성공!")
            return v1
        except Exception as incluster_error:
            st.warning(f"인클러스터 인증 실패: {incluster_error}")
            
            # 다음으로 기본 kubeconfig 파일 사용 시도
            try:
                st.info("기본 kubeconfig 파일을 사용하여 인증을 시도합니다...")
                config.load_kube_config()
                v1 = client.CoreV1Api()
                
                # 연결 테스트
                v1.list_namespace(limit=1)
                st.success("kubeconfig 인증 성공!")
                return v1
            except Exception as kube_config_error:
                st.warning(f"kubeconfig 인증 실패: {kube_config_error}")
                
                # EKS 클러스터 정보를 사용하여 직접 설정
                try:
                    st.info("EKS 클러스터 정보를 사용하여 직접 인증을 시도합니다...")
                    # EKS 클러스터 정보 가져오기
                    cluster_info = eks_client.describe_cluster(name=cluster_name)
                    cluster = cluster_info['cluster']
                    
                    # AWS CLI를 통해 kubeconfig 업데이트
                    import subprocess
                    update_kubeconfig_command = [
                        'aws', 'eks', 'update-kubeconfig',
                        '--name', cluster_name,
                        '--region', 'us-west-2'
                    ]
                    
                    subprocess.run(update_kubeconfig_command, capture_output=True, text=True, check=True)
                    
                    # 업데이트된 kubeconfig 파일 사용
                    config.load_kube_config()
                    v1 = client.CoreV1Api()
                    
                    # 연결 테스트
                    v1.list_namespace(limit=1)
                    st.success("EKS 인증 성공!")
                    return v1
                except Exception as eks_error:
                    st.error(f"EKS 클러스터 정보를 사용한 인증 실패: {eks_error}")
                    return None
    except Exception as e:
        st.error(f"Kubernetes 클라이언트 설정 중 오류가 발생했습니다: {e}")
        return None

def get_real_pods_info(k8s_client):
    """실제 클러스터에서 Pod 정보를 조회합니다."""
    try:
        # 모든 네임스페이스의 Pod 조회
        pods = k8s_client.list_pod_for_all_namespaces()
        
        pod_list = []
        for pod in pods.items:
            # CPU 및 메모리 요청 계산
            cpu_request = 0
            memory_request = 0
            
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        if 'cpu' in container.resources.requests:
                            cpu_val = container.resources.requests['cpu']
                            if isinstance(cpu_val, str) and cpu_val.endswith('m'):
                                cpu_request += int(cpu_val[:-1]) / 1000
                            else:
                                cpu_request += float(cpu_val)
                                
                        if 'memory' in container.resources.requests:
                            mem_val = container.resources.requests['memory']
                            if isinstance(mem_val, str):
                                if mem_val.endswith('Ki'):
                                    memory_request += int(mem_val[:-2]) / (1024 * 1024)
                                elif mem_val.endswith('Mi'):
                                    memory_request += int(mem_val[:-2]) / 1024
                                elif mem_val.endswith('Gi'):
                                    memory_request += float(mem_val[:-2])
                                else:
                                    try:
                                        memory_request += int(mem_val) / (1024 * 1024 * 1024)
                                    except ValueError:
                                        pass
            
            pod_info = {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'node': pod.spec.node_name if pod.spec.node_name else 'Pending',
                'restart_count': sum([container.restart_count for container in pod.status.container_statuses]) if pod.status.container_statuses else 0,
                'created_at': pod.metadata.creation_timestamp,
                'labels': pod.metadata.labels if pod.metadata.labels else {},
                'ready': 'True' if pod.status.conditions and any(condition.type == 'Ready' and condition.status == 'True' for condition in pod.status.conditions) else 'False',
                'cpu_request': f"{cpu_request:.2f} cores" if cpu_request > 0 else 'N/A',
                'memory_request': f"{memory_request:.2f} GB" if memory_request > 0 else 'N/A',
                'containers': []
            }
            
            # 컨테이너 정보
            if pod.spec.containers:
                for container in pod.spec.containers:
                    container_info = {
                        'name': container.name,
                        'image': container.image,
                        'resources': {
                            'requests': container.resources.requests if container.resources and container.resources.requests else {},
                            'limits': container.resources.limits if container.resources and container.resources.limits else {}
                        }
                    }
                    pod_info['containers'].append(container_info)
            
            pod_list.append(pod_info)
        
        return pod_list
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            st.error(f"🔐 Kubernetes API 인증 오류: {e}")
            st.warning("⚠️ AWS IAM 사용자/역할에 EKS 클러스터 접근 권한이 없습니다.")
            st.info("""
            **해결 방법:**
            1. AWS IAM에서 다음 정책을 사용자/역할에 추가하세요:
               - AmazonEKSClusterPolicy
               - AmazonEKSWorkerNodePolicy
               - AmazonEKS_CNI_Policy
            
            2. 또는 클러스터 생성자가 다음 명령으로 권한을 추가해야 합니다:
               ```
               kubectl edit configmap aws-auth -n kube-system
               ```
               
               다음과 같이 mapRoles 또는 mapUsers에 항목을 추가하세요:
               ```yaml
               mapRoles:
               - rolearn: <IAM_ROLE_ARN>
                 username: eks-admin
                 groups:
                 - system:masters
               ```
            
            3. kubectl이 설정되어 있다면 다음 명령으로 확인하세요:
               ```
               kubectl auth can-i get pods --all-namespaces
               ```
            """)
        else:
            st.error(f"Pod 정보 조회 중 오류가 발생했습니다: {e}")
        return []

def get_real_nodes_info(k8s_client):
    """실제 클러스터에서 노드 정보를 조회합니다."""
    try:
        nodes = k8s_client.list_node()
        
        node_list = []
        for node in nodes.items:
            node_info = {
                'name': node.metadata.name,
                'status': 'Ready' if any(condition.type == 'Ready' and condition.status == 'True' for condition in node.status.conditions) else 'NotReady',
                'instance_type': node.metadata.labels.get('node.kubernetes.io/instance-type', 'Unknown'),
                'nodegroup': node.metadata.labels.get('eks.amazonaws.com/nodegroup', 'Unknown'),
                'version': node.status.node_info.kubelet_version,
                'capacity': {
                    'cpu': node.status.capacity.get('cpu', '0'),
                    'memory': node.status.capacity.get('memory', '0Ki'),
                    'pods': node.status.capacity.get('pods', '0')
                },
                'allocatable': {
                    'cpu': node.status.allocatable.get('cpu', '0'),
                    'memory': node.status.allocatable.get('memory', '0Ki'),
                    'pods': node.status.allocatable.get('pods', '0')
                },
                'created_at': node.metadata.creation_timestamp,
                'labels': node.metadata.labels if node.metadata.labels else {}
            }
            node_list.append(node_info)
        
        return node_list
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            st.error(f"🔐 Kubernetes API 인증 오류: {e}")
            st.warning("⚠️ AWS IAM 사용자/역할에 EKS 클러스터 접근 권한이 없습니다.")
            st.info("""
            **해결 방법:**
            1. EKS 클러스터의 aws-auth ConfigMap에 현재 IAM 사용자/역할을 추가하세요
            2. 또는 클러스터 관리자에게 권한 요청을 하세요
            3. AWS 콘솔에서 EKS 클러스터 → Configuration → Access entries에서 권한을 확인하세요
            """)
        else:
            st.error(f"노드 정보 조회 중 오류가 발생했습니다: {e}")
        return []
