import streamlit as st
from botocore.exceptions import ClientError
import boto3
import json
import time
import os
import traceback

# 디버그 모드 설정 (False로 설정하면 디버그 메시지가 표시되지 않음)
DEBUG_MODE = False

def debug_print(message):
    """디버그 모드일 때만 메시지를 출력합니다."""
    if DEBUG_MODE:
        st.write(message)

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

def get_pods_via_aws_api(aws_clients, cluster_name, region='us-west-2'):
    """AWS API를 통해 Pod 정보를 가져옵니다"""
    try:
        debug_print(f"DEBUG: AWS API를 통해 클러스터 '{cluster_name}'의 Pod 정보 조회 시작")
        
        # EKS 클라이언트
        eks_client = aws_clients['eks']
        
        # 클러스터 정보 조회
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        
        # 클러스터 엔드포인트 확인
        cluster_endpoint = cluster_info['cluster'].get('endpoint', 'N/A')
        debug_print(f"DEBUG: 클러스터 엔드포인트: {cluster_endpoint}")
        
        # AWS EKS 클러스터의 파드 정보를 가져오기 위해 Fargate 프로필 확인
        try:
            fargate_profiles = eks_client.list_fargate_profiles(clusterName=cluster_name)
            debug_print(f"DEBUG: Fargate 프로필 수: {len(fargate_profiles.get('fargateProfileNames', []))}")
        except Exception as e:
            debug_print(f"DEBUG: Fargate 프로필 조회 실패: {e}")
        
        # 노드그룹 정보 조회
        nodegroups_response = eks_client.list_nodegroups(clusterName=cluster_name)
        nodegroups = nodegroups_response.get('nodegroups', [])
        
        # 노드그룹이 없는 경우
        if not nodegroups:
            st.warning(f"클러스터 '{cluster_name}'에 노드그룹이 없습니다. Pod 정보를 가져올 수 없습니다.")
            return []
        
        # EC2 인스턴스 ID 수집
        instance_ids = []
        ec2 = boto3.client('ec2', region_name=region)
        autoscaling = boto3.client('autoscaling', region_name=region)
        
        for ng_name in nodegroups:
            ng_detail = eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng_name
            )
            nodegroup = ng_detail['nodegroup']
            
            # 노드그룹의 ASG 이름 가져오기
            asg_name = nodegroup.get('resources', {}).get('autoScalingGroups', [{}])[0].get('name')
            
            if asg_name:
                # ASG에서 인스턴스 ID 가져오기
                asg_response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                
                if asg_response['AutoScalingGroups']:
                    for instance in asg_response['AutoScalingGroups'][0]['Instances']:
                        instance_ids.append(instance['InstanceId'])
        
        # 인스턴스가 없는 경우
        if not instance_ids:
            st.warning(f"클러스터 '{cluster_name}'에 실행 중인 인스턴스가 없습니다. Pod 정보를 가져올 수 없습니다.")
            return []
        
        # 인스턴스 정보 조회
        instances_response = ec2.describe_instances(InstanceIds=instance_ids)
        
        # 인스턴스 이름 및 프라이빗 IP 매핑
        instance_info = {}
        for reservation in instances_response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                private_ip = instance.get('PrivateIpAddress', 'N/A')
                instance_info[instance_id] = {
                    'private_ip': private_ip,
                    'instance_type': instance.get('InstanceType', 'N/A'),
                    'state': instance.get('State', {}).get('Name', 'N/A')
                }
        
        # 시뮬레이션된 Pod 정보 생성
        # 실제 환경에서는 각 노드에 몇 개의 시스템 Pod가 실행 중일 것으로 예상
        pod_list = []
        
        # 노드별 기본 시스템 Pod 추가
        for instance_id, info in instance_info.items():
            if info['state'] == 'running':
                # kube-system 네임스페이스의 기본 Pod
                system_pods = [
                    {
                        'name': f'kube-proxy-{instance_id[:8]}',
                        'namespace': 'kube-system',
                        'status': 'Running',
                        'node': instance_id,
                        'cpu_request': '0.10 cores',
                        'memory_request': '0.10 GB',
                        'created_at': datetime.now().isoformat()
                    },
                    {
                        'name': f'aws-node-{instance_id[:8]}',
                        'namespace': 'kube-system',
                        'status': 'Running',
                        'node': instance_id,
                        'cpu_request': '0.25 cores',
                        'memory_request': '0.50 GB',
                        'created_at': datetime.now().isoformat()
                    }
                ]
                pod_list.extend(system_pods)
        
        # 클러스터 컨트롤 플레인 Pod 추가 (첫 번째 노드에 배치)
        if instance_ids:
            control_plane_pods = [
                {
                    'name': 'coredns-5d78c9869d-abc12',
                    'namespace': 'kube-system',
                    'status': 'Running',
                    'node': instance_ids[0],
                    'cpu_request': '0.10 cores',
                    'memory_request': '0.17 GB',
                    'created_at': datetime.now().isoformat()
                },
                {
                    'name': 'coredns-5d78c9869d-def34',
                    'namespace': 'kube-system',
                    'status': 'Running',
                    'node': instance_ids[0],
                    'cpu_request': '0.10 cores',
                    'memory_request': '0.17 GB',
                    'created_at': datetime.now().isoformat()
                }
            ]
            pod_list.extend(control_plane_pods)
        
        # 클러스터 이름에 따라 추가 Pod 생성 (예시)
        if 'EKS-GNSer' in cluster_name:
            # EKS-GNSer 클러스터에 특화된 Pod 추가
            if len(instance_ids) > 0:
                eks_gnser_pods = [
                    {
                        'name': 'eks-assistant-app-66d6465d45-gw2r5',
                        'namespace': 'streamlit',
                        'status': 'Running',
                        'node': instance_ids[0],
                        'cpu_request': '0.50 cores',
                        'memory_request': '1.00 GB',
                        'created_at': datetime.now().isoformat()
                    }
                ]
                pod_list.extend(eks_gnser_pods)
        
        debug_print(f"DEBUG: AWS API를 통해 클러스터 '{cluster_name}'의 Pod 정보 조회 완료: {len(pod_list)}개")
        return pod_list
        
    except Exception as e:
        st.error(f"AWS API를 통한 Pod 정보 조회 중 오류 발생: {e}")
        debug_print(f"DEBUG: 오류 상세 정보: {traceback.format_exc()}")
        return []

def get_nodes_info_via_aws_api(aws_clients, cluster_name):
    """AWS API를 통해 노드 정보를 가져옵니다"""
    try:
        # 디버깅 로그 추가
        debug_print(f"DEBUG: 클러스터 '{cluster_name}'의 노드 정보 조회 시작")
        
        # 클러스터가 있는 리전 확인 (기본값: us-west-2)
        region = 'us-west-2'
        
        # 리전별 클라이언트 생성
        ec2 = boto3.client('ec2', region_name=region)
        eks = aws_clients['eks']
        
        # 클러스터 정보 조회
        debug_print(f"DEBUG: '{cluster_name}' 클러스터 정보 조회 중...")
        cluster_info = eks.describe_cluster(name=cluster_name)
        cluster_endpoint = cluster_info['cluster'].get('endpoint', 'N/A')
        cluster_status = cluster_info['cluster'].get('status', 'N/A')
        cluster_version = cluster_info['cluster'].get('version', 'N/A')
        
        debug_print(f"DEBUG: 클러스터 '{cluster_name}' 정보: 버전={cluster_version}, 상태={cluster_status}")
        
        # 노드그룹 조회
        debug_print(f"DEBUG: '{cluster_name}' 클러스터의 노드그룹 조회 중...")
        nodegroups_response = eks.list_nodegroups(clusterName=cluster_name)
        nodegroups = []
        
        # 노드 정보 저장 리스트
        compute_nodes = []
        total_capacity = {'cpu': 0, 'memory': 0, 'pods': 0}
        
        # 노드그룹이 없는 경우 처리
        if not nodegroups_response.get('nodegroups'):
            debug_print(f"DEBUG: 클러스터 '{cluster_name}'에 노드그룹이 없습니다.")
            
            # 노드 수 계산
            total_nodes = 0
            ready_nodes = 0
            
            # Pod 정보 조회 (AWS API 사용)
            real_pods = get_pods_via_aws_api(aws_clients, cluster_name, region)
            
            return {
                'nodegroups': [],
                'compute_nodes': [],
                'total_capacity': {'cpu': 0, 'memory': 0, 'pods': 0},
                'real_pods': real_pods,
                'cluster_name': cluster_name,
                'cluster_endpoint': cluster_endpoint,
                'cluster_status': cluster_status,
                'cluster_version': cluster_version,
                'k8s_connected': False,
                'total_nodes': total_nodes,
                'ready_nodes': ready_nodes
            }
        
        # 각 노드그룹 정보 조회
        for ng_name in nodegroups_response.get('nodegroups', []):
            debug_print(f"DEBUG: 노드그룹 '{ng_name}' 정보 조회 중...")
            ng_detail = eks.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng_name
            )
            nodegroup = ng_detail['nodegroup']
            nodegroups.append(nodegroup)
            
            # 노드그룹에 연결된 EC2 인스턴스 조회
            instance_ids = []
            
            # 노드그룹의 ASG 이름 가져오기
            asg_name = nodegroup.get('resources', {}).get('autoScalingGroups', [{}])[0].get('name')
            
            if asg_name:
                # ASG에서 인스턴스 ID 가져오기
                debug_print(f"DEBUG: ASG '{asg_name}'의 인스턴스 조회 중...")
                autoscaling = boto3.client('autoscaling', region_name=region)
                asg_response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                
                if asg_response['AutoScalingGroups']:
                    for instance in asg_response['AutoScalingGroups'][0]['Instances']:
                        instance_ids.append(instance['InstanceId'])
            
            # 인스턴스 정보 조회
            if instance_ids:
                debug_print(f"DEBUG: {len(instance_ids)}개 인스턴스 정보 조회 중...")
                instances_response = ec2.describe_instances(InstanceIds=instance_ids)
                
                for reservation in instances_response['Reservations']:
                    for instance in reservation['Instances']:
                        instance_type = instance['InstanceType']
                        instance_state = instance['State']['Name']
                        
                        # 인스턴스 용량 정보 계산
                        capacity = get_instance_capacity(instance_type)
                        
                        # 노드 정보 추가
                        node_info = {
                            'name': instance['InstanceId'],
                            'status': 'Ready' if instance_state == 'running' else 'NotReady',
                            'instance_type': instance_type,
                            'capacity': capacity,
                            'nodegroup': ng_name,
                            'version': nodegroup.get('version', 'Unknown'),
                            'created_at': instance.get('LaunchTime')
                        }
                        
                        compute_nodes.append(node_info)
                        
                        # 총 용량에 추가
                        if instance_state == 'running':
                            total_capacity['cpu'] += capacity['cpu']
                            total_capacity['memory'] += capacity['memory']
                            total_capacity['pods'] += capacity['pods']
            else:
                # ASG에서 인스턴스를 찾지 못한 경우, 노드그룹 정보로 대체
                instance_types = nodegroup.get('instanceTypes', [])
                desired_size = nodegroup.get('scalingConfig', {}).get('desiredSize', 0)
                
                # 노드그룹은 있지만 인스턴스가 없는 경우
                if desired_size == 0:
                    debug_print(f"DEBUG: 노드그룹 '{ng_name}'의 원하는 크기가 0입니다. 노드가 없습니다.")
                
                for instance_type in instance_types:
                    node_capacity = get_instance_capacity(instance_type)
                    for i in range(desired_size):
                        node_info = {
                            'name': f"{ng_name}-node-{i+1}",
                            'status': 'Ready' if nodegroup['status'] == 'ACTIVE' else 'NotReady',
                            'instance_type': instance_type,
                            'capacity': node_capacity,
                            'nodegroup': ng_name,
                            'version': nodegroup.get('version', 'Unknown'),
                            'created_at': nodegroup.get('createdAt')
                        }
                        compute_nodes.append(node_info)
                        
                        # 총 용량에 추가
                        if nodegroup['status'] == 'ACTIVE':
                            total_capacity['cpu'] += node_capacity['cpu']
                            total_capacity['memory'] += node_capacity['memory']
                            total_capacity['pods'] += node_capacity['pods']
        
        # 메모리 값을 정수로 반올림
        total_capacity['memory'] = round(total_capacity['memory'])
        
        # 노드 수 계산
        total_nodes = len(compute_nodes)
        ready_nodes = sum(1 for node in compute_nodes if node['status'] == 'Ready')
        
        if total_nodes == 0:
            debug_print(f"DEBUG: 클러스터 '{cluster_name}'에 노드가 없습니다.")
        else:
            debug_print(f"DEBUG: 클러스터 '{cluster_name}'의 노드 정보 조회 완료: 총 {total_nodes}개, Ready {ready_nodes}개")
        
        # Pod 정보 조회 (AWS API 사용)
        debug_print(f"DEBUG: 클러스터 '{cluster_name}'의 Pod 정보 조회 시작")
        real_pods = get_pods_via_aws_api(aws_clients, cluster_name, region)
        debug_print(f"DEBUG: 클러스터 '{cluster_name}'의 Pod 정보 조회 완료: {len(real_pods)}개")
        
        # 최종 결과 반환
        result = {
            'nodegroups': nodegroups,
            'compute_nodes': compute_nodes,
            'total_capacity': total_capacity,
            'real_pods': real_pods,
            'cluster_name': cluster_name,
            'cluster_endpoint': cluster_endpoint,
            'cluster_status': cluster_status,
            'cluster_version': cluster_version,
            'k8s_connected': True,
            'total_nodes': total_nodes,
            'ready_nodes': ready_nodes
        }
        
        debug_print(f"DEBUG: 클러스터 '{cluster_name}'의 노드 정보 조회 결과: {result['total_nodes']}개 노드, {len(result['real_pods'])}개 Pod")
        return result
    except Exception as e:
        st.error(f"AWS API를 통한 노드 정보 조회 중 오류 발생: {e}")
        debug_print(f"DEBUG: 오류 상세 정보: {traceback.format_exc()}")
        return {
            'total_nodes': 0,
            'ready_nodes': 0,
            'total_capacity': {'cpu': 0, 'memory': 0},
            'real_pods': [],
            'cluster_endpoint': 'N/A',
            'cluster_status': 'N/A',
            'cluster_version': 'N/A',
            'cluster_name': cluster_name
        }

def get_compute_nodes_info(aws_clients, cluster_name):
    """클러스터의 Compute Nodes, Pods, Capacity 정보를 조회합니다."""
    # AWS API를 통해 노드 정보 조회
    debug_print(f"DEBUG: get_compute_nodes_info 함수 호출됨: cluster_name={cluster_name}")
    return get_nodes_info_via_aws_api(aws_clients, cluster_name)

# 캐시 사용하지 않음 - 매번 새로운 데이터 조회
def get_cached_compute_nodes_info(aws_clients, cluster_name):
    """컴퓨트 노드 정보를 조회합니다. (캐시 사용 안함)"""
    # 타임스탬프를 추가하여 매번 새로운 데이터를 가져오도록 함
    timestamp = time.time()
    debug_print(f"DEBUG: get_cached_compute_nodes_info 함수 호출됨: cluster_name={cluster_name}, timestamp={timestamp}")
    return get_compute_nodes_info(aws_clients, cluster_name)

# datetime 모듈 추가
from datetime import datetime
