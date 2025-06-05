
import streamlit as st
import json
from botocore.exceptions import ClientError

def get_available_models(bedrock_client):
    """사용 가능한 Bedrock 모델 목록을 조회합니다."""
    try:
        response = bedrock_client.list_foundation_models()
        models = []
        
        for model in response['modelSummaries']:
            # Anthropic Claude 모델만 필터링하고 Claude 4 모델 제외
            if ('anthropic.claude' in model['modelId'] and
                'TEXT' in model.get('inputModalities', []) and 
                'TEXT' in model.get('outputModalities', []) and
                'claude-4' not in model['modelId'].lower() and
                'opus-4' not in model['modelId'].lower()):
                models.append({
                    'modelId': model['modelId'],
                    'modelName': model['modelName'],
                    'providerName': model['providerName']
                })
        
        return models
    except ClientError as e:
        st.error(f"Bedrock 모델 조회 중 오류가 발생했습니다: {e}")
        return []

def invoke_bedrock_model(bedrock_runtime, model_id, prompt, temperature=0.7, max_tokens=1000, top_p=0.9, top_k=250):
    """Bedrock 모델을 직접 호출합니다."""
    try:
        if 'anthropic.claude' in model_id:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        else:
            st.error(f"지원되지 않는 모델입니다: {model_id}. Anthropic Claude 모델만 지원됩니다.")
            return None
            
    except ClientError as e:
        st.error(f"Bedrock 모델 호출 중 오류가 발생했습니다: {e}")
        return None

def get_simple_model_name(model_id, provider_name):
    """모델 이름을 간단하게 변환하는 함수"""
    # Claude 모델들만 처리
    if 'claude-3-5-sonnet' in model_id:
        return "Claude 3.5 Sonnet"
    elif 'claude-3-5-haiku' in model_id:
        return "Claude 3.5 Haiku"
    elif 'claude-3-opus' in model_id:
        return "Claude 3 Opus"
    elif 'claude-3-sonnet' in model_id:
        return "Claude 3 Sonnet"
    elif 'claude-3-haiku' in model_id:
        return "Claude 3 Haiku"
    elif 'claude' in model_id:
        return f"Claude ({model_id.split('.')[-1]})"
    else:
        return f"Claude Model ({model_id.split('.')[-1]})"
