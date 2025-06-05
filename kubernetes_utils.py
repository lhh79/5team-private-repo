
import streamlit as st
import base64
import tempfile
import yaml
import subprocess
import json
from datetime import datetime

def get_kubernetes_client(eks_client, cluster_name):
    """EKS 클러스터의 Kubernetes API 클라이언트를 설정합니다."""
    try:
        from kubernetes import client, config
        
        # EKS 클러스터 정보 가져오기
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        cluster = cluster_info['cluster']
        
        # AWS STS를 통한 토큰 생성 (직접 처리)
        try:
            # AWS CLI를 통한 토큰 획득
            token_command = [
                'aws', 'eks', 'get-token',
                '--cluster-name', cluster_name,
                '--region', 'us-west-2'
            ]
            
            result = subprocess.run(token_command, capture_output=True, text=True, check=True)
            token_data = json.loads(result.stdout)
            bearer_token = token_data['status']['token']
            
            # 직접 인증 헤더 설정
            configuration = client.Configuration()
            configuration.host = cluster['endpoint']
            configuration.verify_ssl = True
            configuration.api_key = {"authorization": "Bearer " + bearer_token}
            configuration.api_key_prefix = {"authorization": "Bearer"}
            
            # CA 인증서 설정
            ca_cert_data = base64.b64decode(cluster['certificateAuthority']['data'])
            with tempfile.NamedTemporaryFile(delete=False, suffix='.crt') as ca_file:
                ca_file.write(ca_cert_data)
                ca_file.flush()
                configuration.ssl_ca_cert = ca_file.name
            
            # 클라이언트 생성
            api_client = client.ApiClient(configuration)
            v1 = client.CoreV1Api(api_client)
            
            # 연결 테스트
            v1.list_namespace(limit=1)
            
            return v1
            
        except subprocess.CalledProcessError as e:
            st.error(f"AWS CLI 토큰 획득 실패: {e}")
            return None
        except Exception as token_error:
            st.error(f"토큰 기반 인증 실패: {token_error}")
            
            # 대안: kubeconfig 파일 사용
            kubeconfig = {
                'apiVersion': 'v1',
                'clusters': [{
                    'name': cluster_name,
                    'cluster': {
                        'server': cluster['endpoint'],
                        'certificate-authority-data': cluster['certificateAuthority']['data']
                    }
                }],
                'contexts': [{
                    'name': cluster_name,
                    'context': {
                        'cluster': cluster_name,
                        'user': cluster_name
                    }
                }],
                'current-context': cluster_name,
                'users': [{
                    'name': cluster_name,
                    'user': {
                        'exec': {
                            'apiVersion': 'client.authentication.k8s.io/v1beta1',
                            'command': 'aws',
                            'args': [
                                'eks',
                                'get-token',
                                '--cluster-name',
                                cluster_name,
                                '--region',
                                'us-west-2'
                            ]
                        }
                    }
                }]
            }
            
            # 임시 파일에 kubeconfig 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(kubeconfig, f)
                kubeconfig_path = f.name
            
            # Kubernetes 클라이언트 설정
            config.load_kube_config(config_file=kubeconfig_path)
            v1 = client.CoreV1Api()
            
            return v1
        
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
            pod_info = {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'node': pod.spec.node_name if pod.spec.node_name else 'Pending',
                'restart_count': sum([container.restart_count for container in pod.status.container_statuses]) if pod.status.container_statuses else 0,
                'created_at': pod.metadata.creation_timestamp,
                'labels': pod.metadata.labels if pod.metadata.labels else {},
                'ready': 'True' if pod.status.conditions and any(condition.type == 'Ready' and condition.status == 'True' for condition in pod.status.conditions) else 'False',
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
               aws eks update-cluster-config --name <cluster-name> --resources-vpc-config subnetIds=<subnet-ids>
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
            3. AWS 콘솔에서 EKS 클러스터 → Configuration → Compute에서 권한을 확인하세요
            """)
        else:
            st.error(f"노드 정보 조회 중 오류가 발생했습니다: {e}")
        return []
