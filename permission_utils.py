
import streamlit as st
import subprocess
import yaml
import tempfile
from config import get_current_aws_identity

def update_aws_auth_configmap(eks_client, cluster_name, user_arn, username, groups=None):
    """aws-auth ConfigMap을 업데이트하여 사용자 권한을 추가합니다."""
    try:
        if groups is None:
            groups = ['system:masters']
        
        # kubectl을 사용하여 현재 aws-auth ConfigMap 가져오기
        try:
            # kubeconfig 업데이트
            subprocess.run([
                'aws', 'eks', 'update-kubeconfig',
                '--region', 'us-west-2',
                '--name', cluster_name
            ], check=True, capture_output=True)
            
            # 현재 aws-auth ConfigMap 가져오기
            result = subprocess.run([
                'kubectl', 'get', 'configmap', 'aws-auth',
                '-n', 'kube-system', '-o', 'yaml'
            ], capture_output=True, text=True, check=True)
            
            configmap = yaml.safe_load(result.stdout)
            
            # mapUsers 섹션 업데이트
            mapUsers = yaml.safe_load(configmap['data'].get('mapUsers', '[]'))
            
            # 새 사용자 추가
            new_user = {
                'userarn': user_arn,
                'username': username,
                'groups': groups
            }
            
            # 중복 확인 후 추가
            existing_user = None
            for i, user in enumerate(mapUsers):
                if user.get('userarn') == user_arn:
                    existing_user = i
                    break
            
            if existing_user is not None:
                mapUsers[existing_user] = new_user
                st.info(f"기존 사용자 권한을 업데이트했습니다: {username}")
            else:
                mapUsers.append(new_user)
                st.success(f"새 사용자 권한을 추가했습니다: {username}")
            
            # ConfigMap 업데이트
            configmap['data']['mapUsers'] = yaml.dump(mapUsers)
            
            # 임시 파일에 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(configmap, f)
                temp_file = f.name
            
            # kubectl apply로 업데이트
            subprocess.run([
                'kubectl', 'apply', '-f', temp_file
            ], check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            st.error(f"kubectl 명령어 실행 실패: {e}")
            return False
            
    except Exception as e:
        st.error(f"aws-auth ConfigMap 업데이트 실패: {e}")
        return False

def check_eks_permissions(k8s_client):
    """현재 사용자의 EKS 권한을 확인합니다."""
    try:
        # 기본 권한 테스트
        permissions = {}
        
        test_operations = [
            ('pods', 'list'),
            ('nodes', 'list'),
            ('deployments', 'list'),
            ('services', 'list'),
            ('configmaps', 'get')
        ]
        
        for resource, verb in test_operations:
            try:
                if resource == 'pods':
                    k8s_client.list_pod_for_all_namespaces(limit=1)
                elif resource == 'nodes':
                    k8s_client.list_node(limit=1)
                elif resource == 'deployments':
                    from kubernetes import client
                    apps_v1 = client.AppsV1Api(k8s_client.api_client)
                    apps_v1.list_deployment_for_all_namespaces(limit=1)
                elif resource == 'services':
                    k8s_client.list_service_for_all_namespaces(limit=1)
                elif resource == 'configmaps':
                    k8s_client.list_config_map_for_all_namespaces(limit=1)
                
                permissions[f"{resource}:{verb}"] = True
            except Exception:
                permissions[f"{resource}:{verb}"] = False
        
        return permissions
        
    except Exception as e:
        st.error(f"권한 확인 중 오류 발생: {e}")
        return {}
