import streamlit as st
import base64
import tempfile
import yaml
import os
import time
from datetime import datetime
import subprocess
from kubernetes import client, config

def get_kubernetes_client(eks_client, cluster_name):
    """EKS 클러스터의 Kubernetes API 클라이언트를 설정합니다."""
    try:
        st.info(f"클러스터 '{cluster_name}'에 대한 Kubernetes 클라이언트 설정 시작")
        
        # 임시 디렉토리 생성
        temp_dir = tempfile.mkdtemp()
        temp_kubeconfig_path = os.path.join(temp_dir, 'kubeconfig')
        
        # 환경 변수 설정
        os.environ['KUBECONFIG'] = temp_kubeconfig_path
        
        # AWS CLI를 통해 kubeconfig 생성
        update_kubeconfig_command = [
            'aws', 'eks', 'update-kubeconfig',
            '--name', cluster_name,
            '--region', 'us-west-2',
            '--kubeconfig', temp_kubeconfig_path
        ]
        
        st.info(f"kubeconfig 생성 명령어: {' '.join(update_kubeconfig_command)}")
        result = subprocess.run(update_kubeconfig_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            st.error(f"kubeconfig 생성 실패: {result.stderr}")
            return None
        
        st.success(f"kubeconfig 생성 성공: {temp_kubeconfig_path}")
        
        # kubeconfig 내용 확인
        with open(temp_kubeconfig_path, 'r') as f:
            kubeconfig_content = f.read()
            st.info(f"kubeconfig 내용 (일부): {kubeconfig_content[:100]}...")
        
        # 현재 컨텍스트 확인
        check_context_command = ['kubectl', 'config', 'current-context', '--kubeconfig', temp_kubeconfig_path]
        context_result = subprocess.run(check_context_command, capture_output=True, text=True)
        
        if context_result.returncode == 0:
            st.info(f"현재 컨텍스트: {context_result.stdout.strip()}")
        else:
            st.warning(f"컨텍스트 확인 실패: {context_result.stderr}")
        
        # 명시적으로 kubeconfig 파일 로드
        config.load_kube_config(config_file=temp_kubeconfig_path)
        
        # API 클라이언트 생성
        v1 = client.CoreV1Api()
        
        # 연결 테스트
        try:
            namespaces = v1.list_namespace(limit=1)
            st.success(f"Kubernetes API 연결 성공! 네임스페이스: {namespaces.items[0].metadata.name}")
            
            # 클러스터 정보 확인
            nodes = v1.list_node()
            if nodes.items:
                st.info(f"클러스터 노드 수: {len(nodes.items)}")
                st.info(f"첫 번째 노드 이름: {nodes.items[0].metadata.name}")
            
            return v1
        except Exception as api_error:
            st.error(f"Kubernetes API 연결 테스트 실패: {api_error}")
            return None
            
    except Exception as e:
        st.error(f"Kubernetes 클라이언트 설정 중 오류 발생: {e}")
        return None

def get_real_nodes_info(k8s_client):
    """실제 클러스터에서 노드 정보를 조회합니다."""
    try:
        nodes = k8s_client.list_node()
        
        node_list = []
        for node in nodes.items:
            node_name = node.metadata.name
            node_status = "Ready"
            
            # 노드 상태 확인
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    node_status = "Ready" if condition.status == "True" else "NotReady"
                    break
            
            # 인스턴스 타입 확인
            instance_type = node.metadata.labels.get("node.kubernetes.io/instance-type", "Unknown")
            
            # 노드그룹 확인
            nodegroup = node.metadata.labels.get("eks.amazonaws.com/nodegroup", "Unknown")
            
            # 버전 확인
            version = node.status.node_info.kubelet_version
            
            # 용량 정보
            capacity = {
                'cpu': node.status.capacity.get('cpu', '0'),
                'memory': node.status.capacity.get('memory', '0'),
                'pods': node.status.capacity.get('pods', '0')
            }
            
            node_info = {
                'name': node_name,
                'status': node_status,
                'instance_type': instance_type,
                'capacity': capacity,
                'nodegroup': nodegroup,
                'version': version,
                'created_at': node.metadata.creation_timestamp
            }
            
            node_list.append(node_info)
        
        return node_list
    except Exception as e:
        st.error(f"노드 정보 조회 중 오류가 발생했습니다: {e}")
        return []

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
                                    memory_request += int(mem_val[:-2])
                                else:
                                    memory_request += int(mem_val) / (1024 * 1024 * 1024)
                            else:
                                memory_request += float(mem_val) / (1024 * 1024 * 1024)
            
            # Pod 정보 구성
            pod_info = {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'node': pod.spec.node_name if pod.spec.node_name else 'N/A',
                'cpu_request': f"{cpu_request:.2f} cores" if cpu_request > 0 else 'N/A',
                'memory_request': f"{memory_request:.2f} GB" if memory_request > 0 else 'N/A',
                'created_at': pod.metadata.creation_timestamp
            }
            
            pod_list.append(pod_info)
        
        return pod_list
    except Exception as e:
        st.error(f"Pod 정보 조회 중 오류가 발생했습니다: {e}")
        return []
