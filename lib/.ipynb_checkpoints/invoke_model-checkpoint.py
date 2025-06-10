# Path: /bedrock_chatbot_app/lib/invoke_model.py

"""Amazon Bedrock 파운데이션 모델을 호출하기 위한 기능을 제공하는 모듈"""
import json
import logging
from lib.bedrock_client import get_bedrock_client
from lib.config import config

logger = logging.getLogger(__name__)

def invoke_model(prompt, model_id=None):
    """
    Amazon Bedrock 파운데이션 모델을 호출하여 텍스트 응답을 생성합니다.
    
    Args:
        prompt (str): 모델에게 전달할 프롬프트 텍스트
        model_id (str, optional): 사용할 모델 ID
        
    Returns:
        str: 모델이 생성한 텍스트 응답
    """
    model_id = model_id or config.model_id
    
    logger.info(f"🤖 파운데이션 모델 호출: {model_id}")
    logger.debug(f"프롬프트: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
    
    try:
        client = get_bedrock_client()
        
        # 모델별 요청 형식 설정
        if "anthropic.claude" in model_id:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
        elif "amazon.titan" in model_id:
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1024,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            }
        else:
            raise ValueError(f"지원되지 않는 모델: {model_id}")
        
        # 모델 호출
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        # 응답 파싱
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # 모델별 응답 텍스트 추출
        if "anthropic.claude" in model_id:
            response_text = response_body['content'][0]['text']
        elif "amazon.titan" in model_id:
            response_text = response_body['results'][0]['outputText']
        else:
            response_text = str(response_body)
        
        logger.info(f"✅ 모델 응답 생성 완료: {len(response_text)} 글자")
        return response_text
        
    except Exception as e:
        error_msg = f"파운데이션 모델 호출 오류: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"오류: {error_msg}"