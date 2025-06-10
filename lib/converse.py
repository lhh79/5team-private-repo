# Path: /bedrock_chatbot_app/lib/converse.py

"""Amazon Bedrock Converse API를 활용하기 위한 기능을 제공하는 모듈"""
import logging
from lib.bedrock_client import get_bedrock_client
from lib.config import config

logger = logging.getLogger(__name__)

def converse(prompt, conversation_history=None, model_id=None, temperature=0.7, max_tokens=1024):
    """
    Amazon Bedrock Converse API를 호출하여 대화형 응답을 생성합니다.
    
    Args:
        prompt (str): 사용자 입력 프롬프트
        conversation_history (list, optional): 이전 대화 기록
        model_id (str, optional): 사용할 모델 ID
        temperature (float): 응답의 무작위성 조절 (0~1)
        max_tokens (int): 생성할 최대 토큰 수
        
    Returns:
        dict: 생성된 응답과 업데이트된 대화 기록을 포함하는 딕셔너리
    """
    model_id = model_id or config.model_id
    conversation_history = conversation_history or []
    
    logger.info(f"🗣️ Converse API 호출 시작: 모델={model_id}, 온도={temperature}")
    
    try:
        client = get_bedrock_client()
        
        # 대화 기록을 Converse API 형식으로 변환
        messages = []
        
        # 이전 대화 기록 추가
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}]
            })
        
        # 현재 사용자 메시지 추가
        messages.append({
            "role": "user",
            "content": [{"text": prompt}]
        })
        
        # Converse API 호출
        response = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": max_tokens,
            }
        )
        
        logger.info("✅ Converse API 응답 수신 성공")
        
        # 응답 파싱
        response_content = response.get("output", {}).get("message", {}).get("content", [])
        assistant_message = ""
        
        # 응답 텍스트 추출
        for content_item in response_content:
            if content_item.get("type") == "text":
                assistant_message += content_item.get("text", "")
        
        # 대화 기록 업데이트
        updated_history = conversation_history.copy()
        updated_history.append({"role": "user", "content": prompt})
        updated_history.append({"role": "assistant", "content": assistant_message})
        
        logger.info(f"💬 응답 생성 완료: {len(assistant_message)} 글자")
        
        return {
            "response_type": "converse",
            "output": assistant_message,
            "conversation_history": updated_history
        }
    
    except Exception as e:
        error_msg = f"Converse API 오류: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        return {
            "response_type": "error",
            "output": error_msg,
            "conversation_history": conversation_history
        }