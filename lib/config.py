# Path: /home/ec2-user/streamlit/lib/config.py

"""Bedrock 서비스 설정 정보를 관리하는 모듈"""
from dataclasses import dataclass

@dataclass
class BedrockConfig:
    """
    Amazon Bedrock 서비스의 설정 정보를 관리하는 클래스
    
    Attributes:
        flow_id (str): Bedrock Flow의 ID
        flow_alias_id (str): Bedrock Flow Alias의 ID
        agent_id (str): Bedrock Agent의 ID
        agent_alias_id (str): Bedrock Agent Alias의 ID
        knowledge_base_id (str): Bedrock Knowledge Base의 ID
        
        region_name (str): AWS 리전 이름
        model_id (str): 기본 파운데이션 모델 ID
    """
    # 리소스 ID
    flow_id: str = "D8WTJ2N5A9"  # 실제 Flow ID
    flow_alias_id: str = "JR851K0BJD"  # 실제 Flow Alias ID
    agent_id: str = "OPTQMAOLS6"  # EKS 어시스턴트용 Agent ID
    agent_alias_id: str = "RZTFE36HRW"  # EKS 어시스턴트용 Agent Alias ID
    knowledge_base_id: str = "VZYLXTUTQY"  # 실제 Knowledge Base ID
    
    # AWS 리전 및 모델 설정
    region_name: str = "us-west-2"
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"

# 전역 설정 객체 생성
config = BedrockConfig()
