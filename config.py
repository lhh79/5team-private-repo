
import streamlit as st
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os

@st.cache_resource
def init_aws_clients():
    """AWS 클라이언트들을 초기화합니다."""
    try:
        # AWS 자격 증명 확인
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        # 기본 리전 설정
        region = 'us-west-2'  # 미국 서부 리전
        
        # Access Key 기반 자격 증명이 있는 경우
        if aws_access_key_id and aws_secret_access_key:
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region
            )
        else:
            # IAM Role 기반 자격 증명 시도
            try:
                # 기본 세션으로 IAM Role 자격 증명 사용
                session = boto3.Session(region_name=region)
                
                # 자격 증명 테스트
                sts_client = session.client('sts')
                identity = sts_client.get_caller_identity()
                
            except Exception as e:
                st.error(f"❌ AWS 자격 증명이 설정되지 않았습니다. EKS 환경에서는 IAM Role이, 로컬 환경에서는 Secrets에서 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 설정해주세요. 오류: {e}")
                return None
        
        return {
            'eks': session.client('eks', region_name=region),
            'bedrock_runtime': session.client('bedrock-runtime', region_name='us-west-2'),
            'bedrock': session.client('bedrock', region_name='us-west-2')
        }
    except (NoCredentialsError, ClientError) as e:
        st.error(f"AWS 서비스 초기화 중 오류가 발생했습니다: {e}")
        return None

def get_current_aws_identity():
    """현재 AWS 자격 증명 정보를 가져옵니다."""
    try:
        session = boto3.Session()
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        return {
            'account': identity['Account'],
            'arn': identity['Arn'],
            'user_id': identity['UserId']
        }
    except Exception as e:
        st.error(f"AWS 자격 증명 정보 조회 실패: {e}")
        return None
