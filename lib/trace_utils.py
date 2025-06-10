# Path: /bedrock_chatbot_app/lib/trace_utils.py

"""Bedrock 서비스의 트레이스 정보를 처리하는 유틸리티 모듈"""
import json
import logging

logger = logging.getLogger(__name__)

def ensure_json_serializable(obj):
    """
    객체가 JSON 직렬화 가능하도록 변환합니다.
    
    Args:
        obj: 변환할 객체
        
    Returns:
        JSON 직렬화 가능한 객체
    """
    if obj is None:
        return None
    
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    if isinstance(obj, dict):
        return {k: ensure_json_serializable(v) for k, v in obj.items()}
    
    if isinstance(obj, list):
        return [ensure_json_serializable(i) for i in obj]
    
    if isinstance(obj, bytes):
        try:
            return json.loads(obj.decode('utf-8'))
        except Exception:
            return str(obj)
    
    # 그 외 모든 타입은 문자열로 변환
    return str(obj)

def extract_trace_summary(trace, response_type):
    """
    트레이스 정보에서 주요 요약 정보를 추출합니다.
    
    Args:
        trace (dict): 트레이스 정보
        response_type (str): 응답 유형 ('agent' 또는 'flow')
        
    Returns:
        dict: 요약 정보
    """
    if not trace:
        return {"message": "트레이스 정보 없음"}
    
    summary = {}
    
    if response_type == "agent":
        # Agent 트레이스에서 단계 정보 추출
        steps = []
        invocation_inputs = None
        
        # 가능한 여러 경로 확인
        if "orchestrationTrace" in trace and "invocationInput" in trace["orchestrationTrace"]:
            invocation_inputs = trace["orchestrationTrace"]["invocationInput"]
        elif "invocationInput" in trace:
            invocation_inputs = trace["invocationInput"]
        
        # 단계 추출
        if isinstance(invocation_inputs, list):
            steps = invocation_inputs
        elif isinstance(invocation_inputs, dict) and "steps" in invocation_inputs:
            steps = invocation_inputs["steps"]
        
        # 요약 정보 구성
        if steps:
            summary["steps_count"] = len(steps)
            summary["steps"] = []
            
            for step in steps:
                step_type = step.get("invocationType", "Unknown")
                step_info = {"type": step_type}
                
                if "actionGroupInvocationInput" in step:
                    action = step["actionGroupInvocationInput"]
                    step_info.update({
                        "name": action.get("actionGroupName", "Unknown"),
                        "api": action.get("apiPath", "Unknown"),
                        "method": action.get("verb", "Unknown")
                    })
                
                summary["steps"].append(step_info)
        else:
            summary["message"] = "단계 정보를 찾을 수 없음"
    
    elif response_type == "flow":
        # Flow 트레이스 요약
        if "nodes" in trace:
            nodes = trace["nodes"]
            summary["nodes_count"] = len(nodes)
            summary["nodes"] = []
            
            for node in nodes:
                summary["nodes"].append({
                    "id": node.get("nodeId", "Unknown"),
                    "type": node.get("nodeType", "Unknown"),
                    "status": node.get("status", "Unknown")
                })
        else:
            summary["message"] = "Flow 노드 정보를 찾을 수 없음"
    
    return summary

def find_steps_in_trace(trace_data):
    """
    트레이스 데이터에서 실행 단계(steps) 정보를 추출합니다.
    
    Args:
        trace_data (dict): 트레이스 데이터
        
    Returns:
        list: 스텝 정보 목록이나 빈 리스트
    """
    if not trace_data:
        return []
    
    # 가능한 경로 탐색
    for path in [
        ['orchestrationTrace', 'invocationInput', 'steps'],
        ['orchestrationTrace', 'invocationInput'],
        ['invocationInput', 'steps'],
        ['invocationInput'],
        ['observation']
    ]:
        current = trace_data
        try:
            for key in path:
                current = current[key]
            
            # 리스트인 경우, 바로 반환
            if isinstance(current, list):
                logger.info(f"✅ {'>'.join(path)} 경로에서 스텝 정보 {len(current)}개 발견")
                return current
            # 단일 항목이 아닌 경우, 계속 탐색
        except (KeyError, TypeError):
            continue
    
    # 재귀적으로 스텝 찾기
    def find_steps_recursive(obj, depth=0):
        if depth > 5:  # 재귀 깊이 제한
            return None
            
        if isinstance(obj, dict):
            if "steps" in obj and isinstance(obj["steps"], list):
                return obj["steps"]
                
            for key, value in obj.items():
                result = find_steps_recursive(value, depth + 1)
                if result:
                    return result
                    
        elif isinstance(obj, list) and all(isinstance(item, dict) for item in obj):
            if any("actionGroupInvocationInput" in item or "invocationType" in item for item in obj):
                return obj
        
        return None
    
    steps = find_steps_recursive(trace_data)
    if steps:
        return steps
        
    return []