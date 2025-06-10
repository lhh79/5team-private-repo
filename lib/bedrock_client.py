# Path: /bedrock_chatbot_app/lib/bedrock_client.py

"""Amazon Bedrock 서비스에 접근하기 위한 클라이언트를 제공하는 모듈"""
import boto3
from lib.config import config

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
        region_name=config.region_name
    )