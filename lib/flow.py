# Path: /bedrock_chatbot_app/lib/flow.py

"""Amazon Bedrock Flow를 호출하기 위한 기능을 제공하는 모듈"""
import json
import logging
import re
from lib.bedrock_client import get_bedrock_agent_client, get_bedrock_client
from lib.config import config

logger = logging.getLogger(__name__)

def invoke_flow(input_text, flow_id=None, flow_alias_id=None, enable_trace=True):
    """
    Bedrock Flow를 호출하여 복잡한 대화형 워크플로우를 실행합니다.
    
    Args:
        input_text (str or dict): 사용자 입력 텍스트 또는 딕셔너리 객체
        flow_id (str, optional): 사용할 Flow ID
        flow_alias_id (str, optional): 사용할 Flow Alias ID
        enable_trace (bool): 트레이스 정보 수집 여부
        
    Returns:
        dict: Flow 실행 결과 및 트레이스 정보
    """
    flow_id = flow_id or config.flow_id
    
    if not flow_id:
        logger.error("🚫 Flow ID가 설정되지 않았습니다")
        return {"response_type": "error", "output": "Flow ID가 설정되지 않았습니다"}
    
    try:
        # 입력 처리 - 모든 케이스를 일관된 형식으로 변환
        if isinstance(input_text, dict):
            # 딕셔너리 입력 - 기본값 채우기
            input_data = {
                "income": input_text.get("income", 80000),
                "totalDebt": input_text.get("totalDebt", 5000),
                "loanTerm": input_text.get("loanTerm", 30),
                "loanAmount": input_text.get("loanAmount", 10000),
                "creditScore": input_text.get("creditScore", 750),
                "mlsId": input_text.get("mlsId", "MLS-1234")
            }
            logger.info("✅ 딕셔너리 입력 처리")
            
        elif isinstance(input_text, str):
            # 문자열 입력 - JSON 또는 자연어
            if input_text.strip().startswith('{') and input_text.strip().endswith('}'):
                try:
                    # JSON 문자열 파싱
                    parsed_json = json.loads(input_text)
                    input_data = {
                        "income": parsed_json.get("income", 80000),
                        "totalDebt": parsed_json.get("totalDebt", 5000),
                        "loanTerm": parsed_json.get("loanTerm", 30),
                        "loanAmount": parsed_json.get("loanAmount", 10000),
                        "creditScore": parsed_json.get("creditScore", 750),
                        "mlsId": parsed_json.get("mlsId", "MLS-1234")
                    }
                    logger.info("✅ JSON 문자열 파싱 성공")
                except json.JSONDecodeError:
                    # 자연어로 처리 - LLM 프롬프트 템플릿 사용
                    logger.info("⚠️ JSON 형식이지만 파싱 실패, 자연어로 처리")
                    input_data = process_natural_language_with_llm(input_text)
            else:
                # 자연어 처리 - LLM 프롬프트 템플릿 사용
                logger.info("📝 자연어 입력 감지: LLM 프롬프트 템플릿으로 처리")
                input_data = process_natural_language_with_llm(input_text)
        else:
            # 지원하지 않는 타입
            logger.error(f"❌ 지원하지 않는 입력 타입: {type(input_text)}")
            return {
                "response_type": "error",
                "output": f"지원하지 않는 입력 타입: {type(input_text)}"
            }
        
        # Bedrock Agent 클라이언트 초기화
        client = get_bedrock_agent_client()
        
        # Flow 호출 파라미터 - 최상위 레벨 필드로 직접 전달
        params = {
            "flowIdentifier": flow_id,
            "inputs": [{
                "nodeName": "FlowInputNode",
                "nodeOutputName": "document",
                "content": {
                    "document": input_data  # 최상위 레벨 필드
                }
            }]
        }
        
        if enable_trace:
            params["enableTrace"] = True
            
        if flow_alias_id:
            params["flowAliasIdentifier"] = flow_alias_id
        
        logger.info(f"🚀 Flow 호출 시작: {json.dumps(input_data)}")
        
        # Flow 호출
        response = client.invoke_flow(**params)
        logger.info("✅ Flow 호출 성공")
        
        # 응답 처리 (이전과 동일)
        result = {}
        outputs = []
        trace_info = {"flow_execution_id": response.get("executionId")}
        
        # 스트림 응답 처리
        if "responseStream" in response:
            for event in response.get("responseStream"):
                result.update(event)
                
                if "flowOutputEvent" in event:
                    output_event = event["flowOutputEvent"]
                    if "content" in output_event and "document" in output_event["content"]:
                        doc = output_event["content"]["document"]
                        if isinstance(doc, str):
                            outputs.append(doc)
                        else:
                            outputs.append(json.dumps(doc, ensure_ascii=False, indent=2))
                
                elif "flowTraceEvent" in event:
                    if "trace_events" not in trace_info:
                        trace_info["trace_events"] = []
                    trace_info["trace_events"].append(event["flowTraceEvent"])
        
        # 성공 여부 확인
        success = False
        reason = "UNKNOWN"
        if "flowCompletionEvent" in result:
            reason = result["flowCompletionEvent"].get("completionReason", "UNKNOWN")
            success = reason == "SUCCESS"
        
        # 최종 응답 구성
        output_text = "\n".join(outputs) if outputs else "No output generated"
        
        return {
            "response_type": "flow",
            "success": success,
            "reason": reason,
            "output": output_text,
            "trace": trace_info,
            "extracted_data": input_data
        }
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {str(e)}", exc_info=True)
        
        return {
            "response_type": "error",
            "success": False,
            "reason": "EXCEPTION",
            "output": f"⚠️ 오류: {str(e)}",
            "trace": {"error": str(e)}
        }


def process_natural_language_with_llm(text):
    """
    LLM 프롬프트 템플릿을 사용하여 자연어에서 구조화된 데이터 추출
    """
    try:
        # 프롬프트 템플릿 생성
        prompt = create_extraction_prompt(text)
        
        # LLM 호출 (Claude 사용)
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId=config.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        # 응답 파싱
        response_body = json.loads(response['body'].read().decode('utf-8'))
        extracted_json_text = response_body['content'][0]['text']
        
        logger.info(f"LLM 응답: {extracted_json_text[:100]}...")
        
        # JSON 파싱 시도
        try:
            extracted_data = json.loads(extracted_json_text)
            logger.info("✅ LLM 응답 JSON 파싱 성공")
        except json.JSONDecodeError:
            # JSON 부분만 추출 시도
            logger.warning("⚠️ LLM 응답 직접 파싱 실패, 정규식으로 추출 시도")
            json_pattern = r'\{[\s\S]*\}'
            match = re.search(json_pattern, extracted_json_text)
            if match:
                try:
                    extracted_data = json.loads(match.group(0))
                    logger.info("✅ 정규식으로 JSON 추출 성공")
                except:
                    logger.error("❌ 정규식으로 추출한 JSON 파싱 실패")
                    return create_default_structure()
            else:
                logger.error("❌ JSON 패턴을 찾을 수 없음")
                return create_default_structure()
        
        # 필수 필드 확인 및 기본값 보완
        result = create_default_structure()
        for key, value in extracted_data.items():
            if key in result and value is not None and value != "":
                result[key] = value
        
        logger.info(f"✅ 자연어 처리 완료: {json.dumps(result)}")
        return result
        
    except Exception as e:
        logger.error(f"자연어 처리 중 오류: {str(e)}")
        return create_default_structure()


def create_extraction_prompt(text):
    """
    자연어에서 구조화된 데이터를 추출하기 위한 프롬프트 템플릿 생성
    """
    # 중괄호를 이스케이프하여 f-string 오류 방지
    prompt = f"""
    아래 텍스트에서 대출 관련 정보를 추출하여 JSON 형식으로 변환해주세요.
    
    ### 입력 텍스트:
    {text}
    
    ### 요구사항:
    1. 다음 필드를 정확히 추출해주세요: income(연간 소득), totalDebt(총 부채), loanTerm(대출 기간), loanAmount(대출 금액), creditScore(신용점수), mlsId(MLS 번호)
    2. 숫자 필드는 숫자 형식으로, 문자열은 문자열 형식으로 반환해주세요 (따옴표 사용)
    3. 추출할 수 없는 값은 null로 설정해주세요
    4. 월 소득이 언급된 경우 연간 소득으로 변환해주세요 (월 소득 × 12)
    5. 백분율 값은 정수로 변환해주세요 (예: 10% -> 10)
    6. 금액에서 쉼표, 통화 기호 등은 제거하고 숫자만 추출해주세요
    
    ### 출력 형식:
    다음과 같은 형태의 JSON만 출력하세요.
    
    {{
      "income": 123456,
      "totalDebt": 1000,
      "loanTerm": 30,
      "loanAmount": 500000,
      "creditScore": 750,
      "mlsId": "MLS-1234"
    }}
    
    ### 출력:
    """
    return prompt


def create_default_structure():
    """Flow API가 기대하는 데이터 구조의 기본값 생성"""
    return {
        "income": 80000,
        "totalDebt": 5000,
        "loanTerm": 30,
        "loanAmount": 10000,
        "creditScore": 750,
        "mlsId": "MLS-1234"
    }