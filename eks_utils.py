
import streamlit as st
from botocore.exceptions import ClientError

def get_eks_clusters(eks_client):
    """EKS 클러스터 목록을 조회합니다."""
    try:
        response = eks_client.list_clusters()
        clusters = []
        
        for cluster_name in response['clusters']:
            cluster_detail = eks_client.describe_cluster(name=cluster_name)
            clusters.append({
                'name': cluster_name,
                'status': cluster_detail['cluster']['status'],
                'version': cluster_detail['cluster']['version'],
                'endpoint': cluster_detail['cluster']['endpoint'],
                'created_at': cluster_detail['cluster']['createdAt']
            })
        
        return clusters
    except ClientError as e:
        st.error(f"EKS 클러스터 조회 중 오류가 발생했습니다: {e}")
        return []

def get_instance_capacity(instance_type):
    """인스턴스 타입별 대략적인 용량 반환"""
    # AWS EC2 인스턴스 타입별 대략적인 스펙
    capacity_map = {
        't3.micro': {'cpu': 2, 'memory': 1, 'pods': 4},
        't3.small': {'cpu': 2, 'memory': 2, 'pods': 8},
        't3.medium': {'cpu': 2, 'memory': 4, 'pods': 17},
        't3.large': {'cpu': 2, 'memory': 8, 'pods': 35},
        't3.xlarge': {'cpu': 4, 'memory': 16, 'pods': 58},
        't3.2xlarge': {'cpu': 8, 'memory': 32, 'pods': 58},
        'm5.large': {'cpu': 2, 'memory': 8, 'pods': 29},
        'm5.xlarge': {'cpu': 4, 'memory': 16, 'pods': 58},
        'm5.2xlarge': {'cpu': 8, 'memory': 32, 'pods': 58},
        'm5.4xlarge': {'cpu': 16, 'memory': 64, 'pods': 234},
        'c5.large': {'cpu': 2, 'memory': 4, 'pods': 29},
        'c5.xlarge': {'cpu': 4, 'memory': 8, 'pods': 58},
        'c5.2xlarge': {'cpu': 8, 'memory': 16, 'pods': 58},
        'c5.4xlarge': {'cpu': 16, 'memory': 32, 'pods': 234},
    }
    
    return capacity_map.get(instance_type, {'cpu': 2, 'memory': 4, 'pods': 17})
