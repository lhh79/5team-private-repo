# Path: /bedrock_chatbot_app/lib/bedrock_client.py

"""Amazon Bedrock 서비스에 접근하기 위한 클라이언트를 제공하는 모듈"""
import boto3
from lib.config import config
from botocore.config import Config as BotoConfig

# 공통 Boto3 Config 객체 설정
boto_config = BotoConfig(
    region_name=config.region_name,
    read_timeout=300,       # 필요시 늘릴 수 있음 (예: 120)
    connect_timeout=30,    # 연결 지연 허용 시간
    retries={
        'max_attempts': 3,
        'mode': 'standard'
    }
)

def get_bedrock_client():
    """기본 Bedrock 런타임 클라이언트(파운데이션 모델, Converse API용)를 반환합니다"""
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=config.region_name
    )

def get_bedrock_agent_client():
    """Bedrock Agent 런타임 클라이언트(Agent, Flow, Knowledge Base용)를 반환합니다"""
    return boto3.client(
        service_name='bedrock-agent-runtime',
        region_name=config.region_name,
        config=boto_config
    )
