
import streamlit as st
from botocore.exceptions import ClientError
from kubernetes_utils import get_kubernetes_client, get_real_nodes_info, get_real_pods_info
from eks_utils import get_instance_capacity

def get_compute_nodes_info(eks_client, cluster_name):
    """클러스터의 Compute Nodes, Pods, Capacity 정보를 조회합니다."""
    try:
        # 노드 그룹 정보
        nodegroups_response = eks_client.list_nodegroups(clusterName=cluster_name)
        nodegroups = []
        
        for ng_name in nodegroups_response.get('nodegroups', []):
            ng_detail = eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng_name
            )
            nodegroups.append(ng_detail['nodegroup'])
        
        # Kubernetes 클라이언트 설정
        k8s_client = get_kubernetes_client(eks_client, cluster_name)
        
        # 실제 노드 정보 조회
        compute_nodes = []
        total_capacity = {'cpu': 0, 'memory': 0, 'pods': 0}
        
        if k8s_client:
            compute_nodes = get_real_nodes_info(k8s_client)
            
            # 총 용량 계산
            for node in compute_nodes:
                cpu_str = node['capacity']['cpu']
                if cpu_str.endswith('m'):
                    cpu_cores = float(cpu_str[:-1]) / 1000
                else:
                    cpu_cores = float(cpu_str)
                
                memory_str = node['capacity']['memory']
                if memory_str.endswith('Ki'):
                    memory_gb = float(memory_str[:-2]) / (1024 * 1024)
                elif memory_str.endswith('Mi'):
                    memory_gb = float(memory_str[:-2]) / 1024
                elif memory_str.endswith('Gi'):
                    memory_gb = float(memory_str[:-2])
                else:
                    memory_gb = float(memory_str) / (1024 * 1024 * 1024)
                
                total_capacity['cpu'] += cpu_cores
                total_capacity['memory'] += memory_gb
                total_capacity['pods'] += int(node['capacity']['pods'])
        else:
            # Kubernetes 연결 실패 시 노드 그룹 정보로 대체
            for ng in nodegroups:
                instance_types = ng.get('instanceTypes', [])
                desired_size = ng.get('scalingConfig', {}).get('desiredSize', 0)
                
                for instance_type in instance_types:
                    node_capacity = get_instance_capacity(instance_type)
                    for i in range(desired_size):
                        node_info = {
                            'name': f"{ng['nodegroupName']}-node-{i+1}",
                            'status': 'Ready' if ng['status'] == 'ACTIVE' else 'NotReady',
                            'instance_type': instance_type,
                            'capacity': node_capacity,
                            'nodegroup': ng['nodegroupName'],
                            'version': ng.get('version', 'Unknown'),
                            'created_at': ng.get('createdAt')
                        }
                        compute_nodes.append(node_info)
                        
                        total_capacity['cpu'] += node_capacity['cpu']
                        total_capacity['memory'] += node_capacity['memory']
                        total_capacity['pods'] += node_capacity['pods']
        
        # 실제 Pod 정보 조회
        real_pods = []
        if k8s_client:
            real_pods = get_real_pods_info(k8s_client)
        
        return {
            'nodegroups': nodegroups,
            'compute_nodes': compute_nodes,
            'total_capacity': total_capacity,
            'real_pods': real_pods,
            'cluster_name': cluster_name,
            'k8s_connected': k8s_client is not None
        }
    except ClientError as e:
        st.error(f"Compute Nodes 정보 조회 중 오류가 발생했습니다: {e}")
        return None

def get_compute_nodes_info(eks_client, cluster_name):
    """클러스터의 Compute Nodes, Pods, Capacity 정보를 조회합니다."""
    try:
        # 노드 그룹 정보
        nodegroups_response = eks_client.list_nodegroups(clusterName=cluster_name)
        nodegroups = []
        
        for ng_name in nodegroups_response.get('nodegroups', []):
            ng_detail = eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng_name
            )
            nodegroups.append(ng_detail['nodegroup'])
        
        # Kubernetes 클라이언트 설정
        k8s_client = get_kubernetes_client(eks_client, cluster_name)
        
        # 실제 노드 정보 조회
        compute_nodes = []
        total_capacity = {'cpu': 0, 'memory': 0, 'pods': 0}
        
        if k8s_client:
            compute_nodes = get_real_nodes_info(k8s_client)
            
            # 총 용량 계산
            for node in compute_nodes:
                cpu_str = node['capacity']['cpu']
                if cpu_str.endswith('m'):
                    cpu_cores = float(cpu_str[:-1]) / 1000
                else:
                    cpu_cores = float(cpu_str)
                
                memory_str = node['capacity']['memory']
                if memory_str.endswith('Ki'):
                    memory_gb = float(memory_str[:-2]) / (1024 * 1024)
                elif memory_str.endswith('Mi'):
                    memory_gb = float(memory_str[:-2]) / 1024
                elif memory_str.endswith('Gi'):
                    memory_gb = float(memory_str[:-2])
                else:
                    memory_gb = float(memory_str) / (1024 * 1024 * 1024)
                
                total_capacity['cpu'] += cpu_cores
                total_capacity['memory'] += memory_gb
                total_capacity['pods'] += int(node['capacity']['pods'])
        else:
            # Kubernetes 연결 실패 시 노드 그룹 정보로 대체
            for ng in nodegroups:
                instance_types = ng.get('instanceTypes', [])
                desired_size = ng.get('scalingConfig', {}).get('desiredSize', 0)
                
                for instance_type in instance_types:
                    node_capacity = get_instance_capacity(instance_type)
                    for i in range(desired_size):
                        node_info = {
                            'name': f"{ng['nodegroupName']}-node-{i+1}",
                            'status': 'Ready' if ng['status'] == 'ACTIVE' else 'NotReady',
                            'instance_type': instance_type,
                            'capacity': node_capacity,
                            'nodegroup': ng['nodegroupName'],
                            'version': ng.get('version', 'Unknown'),
                            'created_at': ng.get('createdAt')
                        }
                        compute_nodes.append(node_info)
                        
                        total_capacity['cpu'] += node_capacity['cpu']
                        total_capacity['memory'] += node_capacity['memory']
                        total_capacity['pods'] += node_capacity['pods']
        
        # 실제 Pod 정보 조회
        real_pods = []
        if k8s_client:
            real_pods = get_real_pods_info(k8s_client)
        
        return {
            'nodegroups': nodegroups,
            'compute_nodes': compute_nodes,
            'total_capacity': total_capacity,
            'real_pods': real_pods,
            'cluster_name': cluster_name,
            'k8s_connected': k8s_client is not None
        }
    except ClientError as e:
        st.error(f"Compute Nodes 정보 조회 중 오류가 발생했습니다: {e}")
        return None
