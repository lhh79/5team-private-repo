# Path: /bedrock_chatbot_app/lib/agent.py

"""Amazon Bedrock Agent를 호출하기 위한 기능을 제공하는 모듈"""
import json
import time
import logging
from lib.bedrock_client import get_bedrock_agent_client
from lib.config import config

logger = logging.getLogger(__name__)

def deep_merge_dict(dict1, dict2):
    """두 딕셔너리를 재귀적으로 병합합니다"""
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict2
    
    for key in dict2:
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            deep_merge_dict(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]
    return dict1

def invoke_agent(input_text, agent_id=None, agent_alias_id=None, enable_trace=True):
    """
    Bedrock Agent를 호출하여 자연어 요청을 처리합니다.
    
    Args:
        input_text (str): 사용자 입력 텍스트
        agent_id (str): 사용할 Agent ID (기본값: config에서 가져옴)
        agent_alias_id (str): 사용할 Agent Alias ID (기본값: config에서 가져옴)
        enable_trace (bool): 트레이스 정보 수집 여부
        
    Returns:
        dict: 응답 정보를 담은 딕셔너리
    """
    # Agent ID 및 Alias ID 설정
    agent_id = agent_id or config.agent_id
    agent_alias_id = agent_alias_id or config.agent_alias_id
    
    if not agent_id or not agent_alias_id:
        logger.error("🚫 Agent ID 또는 Agent Alias ID가 설정되지 않았습니다")
        return {
            "response_type": "agent",
            "output": "Agent ID 또는 Agent Alias ID가 설정되지 않았습니다. 설정을 확인해주세요.",
            "trace": {"error": "Agent ID or Agent Alias ID is not set"}
        }
    
    client = get_bedrock_agent_client()
    session_id = f"session-{int(time.time())}"
    
    try:
        logger.info(f"🚀 Agent API 호출: ID={agent_id}, Alias={agent_alias_id}, 트레이스={enable_trace}")
        
        # Agent 호출
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=enable_trace
        )
        
        logger.info("✅ Agent API 응답 수신 성공")
        
        # 응답 처리
        chunks = []
        trace_data = {}
        
        # 이벤트 스트림 처리
        for event_idx, event in enumerate(response.get("completion", [])):
            # 응답 텍스트 추출
            if "chunk" in event:
                chunk_text = event["chunk"].get("bytes", b"").decode("utf-8")
                if chunk_text:
                    chunks.append(chunk_text)
            
            # 트레이스 정보 처리
            if "trace" in event:
                # 트레이스 바이트 데이터 추출
                raw_trace_data = event["trace"].get("bytes", b"")
                
                if raw_trace_data and len(raw_trace_data) > 0:
                    try:
                        decoded_trace = raw_trace_data.decode("utf-8")
                        trace_info = json.loads(decoded_trace)
                        
                        # 트레이스 정보 병합
                        new_trace_data = trace_info.get("trace", trace_info)
                        deep_merge_dict(trace_data, new_trace_data)
                        
                    except Exception as e:
                        logger.error(f"⚠️ 트레이스 파싱 오류: {str(e)}")
                elif isinstance(event["trace"], dict):
                    # 딕셔너리 형태의 트레이스 처리
                    new_trace_data = {k: v for k, v in event["trace"].items() if k != "bytes"}
                    if new_trace_data:
                        deep_merge_dict(trace_data, new_trace_data)
        
        # 응답 텍스트 결합
        response_text = "".join(chunks)
        
        # finalResponse에서 응답 텍스트 추출 (chunks가 비어있을 경우)
        if not response_text and trace_data:
            # 여러 위치에서 finalResponse 찾기 시도
            final_response_text = None
            
            # 1. orchestrationTrace > observation > finalResponse
            if "orchestrationTrace" in trace_data:
                orch_trace = trace_data["orchestrationTrace"]
                if "observation" in orch_trace and "finalResponse" in orch_trace["observation"]:
                    final_response_text = orch_trace["observation"]["finalResponse"].get("text", "")
            
            # 2. observation > finalResponse
            elif "observation" in trace_data and "finalResponse" in trace_data["observation"]:
                final_response_text = trace_data["observation"]["finalResponse"].get("text", "")
            
            # 3. 재귀 탐색
            if not final_response_text:
                def find_final_response(obj):
                    if not isinstance(obj, dict):
                        return None
                    
                    if "finalResponse" in obj and "text" in obj["finalResponse"]:
                        return obj["finalResponse"]["text"]
                    
                    for key, value in obj.items():
                        if isinstance(value, dict):
                            result = find_final_response(value)
                            if result:
                                return result
                    return None
                
                final_response_text = find_final_response(trace_data)
            
            if final_response_text:
                response_text = final_response_text
        
        # 응답 텍스트 기본값 설정
        response_text = response_text or "응답을 생성할 수 없습니다."
        
        # 디버깅용 트레이스 저장
        if trace_data:
            try:
                with open("last_trace.json", "w") as f:
                    json.dump(trace_data, f, default=str, indent=2)
            except Exception as e:
                logger.debug(f"트레이스 저장 실패: {str(e)}")
        
        # 최종 응답 구성
        return {
            "response_type": "agent",
            "output": response_text,
            "trace": trace_data,
            "session_id": session_id
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Agent API 호출 오류: {error_msg}")
        
        return {
            "response_type": "error",
            "output": f"Agent API 호출 중 오류 발생: {error_msg}",
            "trace": {"error": error_msg, "error_type": "API 호출 오류"},
            "session_id": session_id
        }