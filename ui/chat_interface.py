# Path: /bedrock_chatbot_app/ui/chat_interface.py

"""
채팅 인터페이스 관련 기능을 구현하는 모듈

이 모듈은 Streamlit 기반의 채팅 인터페이스를 제공합니다.
사용자 입력 처리, 응답 생성, 채팅 기록 표시 및 트레이스 정보 시각화 기능을 담당합니다.
"""
import streamlit as st
import time
import json
from lib.invoke_model import invoke_model
from lib.converse import converse
from lib.knowledge_base import query_knowledge_base
from lib.agent import invoke_agent
from lib.flow import invoke_flow
from lib.trace_utils import ensure_json_serializable
from lib.logging_config import logger


def init_chat():
    """채팅 인터페이스 초기화 - 필요한 세션 변수들을 초기화합니다"""
    # 기본 채팅 관련 상태 초기화
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "current_trace" not in st.session_state:
        st.session_state.current_trace = None
    if "converse_history" not in st.session_state:
        st.session_state.converse_history = []
    
    # 처리 상태 관련 변수 초기화
    if "processing_status" not in st.session_state:
        st.session_state.processing_status = {
            "is_processing": False,
            "current_prompt": None,
            "current_mode": None
        }
    if "pending_message" not in st.session_state:
        st.session_state.pending_message = None
        
    # 기본 응답 모드 설정
    if "response_mode" not in st.session_state:
        st.session_state.response_mode = "Foundation Model"


def add_message(role, content, response_type=None):
    """채팅 메시지를 저장합니다"""
    message = {
        "role": role,
        "content": content,
        "timestamp": time.time()
    }
    
    if role == "assistant" and response_type:
        message["response_type"] = response_type
    
    st.session_state.chat_messages.append(message)


def display_chat_history():
    """저장된 채팅 기록을 화면에 표시합니다"""
    # 저장된 메시지 표시
    for msg_idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"]):
            # 응답 유형 표시 (존재하는 경우)
            if msg["role"] == "assistant" and "response_type" in msg:
                response_type_display = get_response_type_display(msg["response_type"])
                st.caption(f"응답 유형: {response_type_display}")
            
            # 메시지 내용 표시
            st.markdown(msg["content"])
            
            # 트레이스 정보 표시 (Agent/Flow인 경우)
            if msg["role"] == "assistant" and msg.get("response_type") in ["agent", "flow"]:
                display_trace_info(msg_idx)
    
    # 대기 중인 메시지 표시
    if st.session_state.pending_message:
        with st.chat_message("assistant"):
            st.write("생각 중...")


def display_trace_info(msg_idx):
    """특정 메시지와 연관된 트레이스 정보를 표시합니다"""
    trace_available = 'current_trace' in st.session_state and st.session_state.current_trace is not None
    
    if trace_available:
        trace_data = st.session_state.current_trace.get("trace_data", {})
        
        with st.expander("🔍 트레이스 정보", expanded=False):
            if "orchestrationTrace" in trace_data:
                display_orchestration_trace(trace_data["orchestrationTrace"], msg_idx)
            else:
                st.json(trace_data)
    else:
        with st.expander("⚠️ 트레이스 정보 없음", expanded=False):
            st.warning("트레이스 정보를 찾을 수 없습니다.")


def display_orchestration_trace(trace, msg_idx):
    """오케스트레이션 트레이스를 스텝별로 표시합니다"""
    # 스텝 정보 추출
    steps = trace.get("invocationInput", {}).get("steps", [])
    
    if not steps:
        st.warning("스텝 정보가 없습니다.")
        st.json(trace)
        return
    
    # 요약 탭과 스텝별 탭 생성
    tab_titles = ["요약"] + [f"스텝 {i+1}" for i in range(len(steps))]
    tabs = st.tabs(tab_titles)
    
    # 요약 탭
    with tabs[0]:
        st.subheader("실행 요약")
        st.write(f"총 스텝 수: {len(steps)}개")
        
        for i, step in enumerate(steps):
            step_type = "API 호출" if "action" in step else "내부 처리"
            if "action" in step:
                api_path = step.get("action", {}).get("apiPath", "Unknown API")
                st.markdown(f"**스텝 {i+1}**: {step_type} - {api_path}")
            else:
                st.write(f"**스텝 {i+1}**: {step_type}")
    
    # 각 스텝 탭
    for i, step in enumerate(steps):
        with tabs[i+1]:
            st.subheader(f"스텝 {i+1} 상세 정보")
            step_type = "API 호출" if "action" in step else "내부 처리"
            st.write(f"**유형**: {step_type}")
            
            if "action" in step:
                action = step["action"]
                st.write(f"**API 경로**: {action.get('apiPath', 'Unknown')}")
                st.write(f"**메서드**: {action.get('httpMethod', 'Unknown')}")
                
                parameters = action.get("parameters", [])
                if parameters:
                    st.write("**파라미터:**")
                    for param in parameters:
                        st.write(f"- {param.get('name')}: {param.get('value')}")
            
            with st.expander("전체 스텝 데이터", expanded=False):
                st.json(step)


def show_flow_trace(trace_data, msg_idx):
    """Flow 트레이스 정보를 표시합니다"""
    if "flow_execution_id" in trace_data:
        st.write(f"**Flow 실행 ID**: {trace_data['flow_execution_id']}")
    
    if 'flow_extracted_data' in st.session_state:
        st.subheader("입력으로 추출된 데이터")
        st.json(st.session_state.flow_extracted_data)
    
    with st.expander("전체 Flow 트레이스 데이터", expanded=False):
        st.json(trace_data)


def get_response_type_display(response_type):
    """응답 유형을 사용자 친화적인 텍스트로 변환합니다"""
    type_map = {
        "foundation_model": "파운데이션 모델",
        "converse": "Converse API",
        "retrieve": "Knowledge Base (Retrieve API)",
        "retrieve_and_generate": "Knowledge Base (RetrieveandGenerate API)",
        "agent": "Agent",
        "flow": "Flow",
        "error": "오류"
    }
    
    return type_map.get(response_type, response_type)


def handle_sample_prompt(prompt):
    """샘플 프롬프트를 처리합니다"""
    if st.session_state.processing_status["is_processing"]:
        return False
        
    current_mode = st.session_state.response_mode
    
    st.session_state.processing_status = {
        "is_processing": True,
        "current_prompt": prompt,
        "current_mode": current_mode
    }
    
    add_message("user", prompt)
    st.session_state.pending_message = True
    st.rerun()


def process_user_input(user_input):
    """사용자 입력을 처리합니다"""
    if not user_input:
        return False
        
    # 중복 처리 방지
    if st.session_state.processing_status["is_processing"]:
        return False
    if user_input == st.session_state.processing_status.get("current_prompt"):
        return False
    
    response_mode = st.session_state.response_mode
    
    # 로깅
    logger.info(f"사용자 입력 처리 시작: '{user_input}'")
    logger.info(f"현재 응답 모드: {response_mode}")
    
    if response_mode == "Agent":
        logger.info(f"Agent API 호출 - enableTrace: {st.session_state.get('agent_enable_trace', True)}")
    elif response_mode == "Flow":
        logger.info(f"Flow API 호출 - enableTrace: {st.session_state.get('flow_enable_trace', True)}")
    
    # 처리 상태 업데이트
    st.session_state.processing_status = {
        "is_processing": True,
        "current_prompt": user_input,
        "current_mode": response_mode
    }
    
    add_message("user", user_input)
    st.session_state.pending_message = True
    st.rerun()


def check_pending_response():
    """대기 중인 응답이 있는지 확인하고 처리합니다"""
    if (st.session_state.processing_status["is_processing"] and 
        st.session_state.pending_message):
        
        prompt = st.session_state.processing_status["current_prompt"]
        mode = st.session_state.processing_status["current_mode"]
        
        try:
            # 응답 생성
            response_data = generate_response(prompt, mode)
            output = response_data.get("output", "응답을 생성할 수 없습니다.")
            response_type = response_data.get("response_type", "unknown")
            
            # 디버그 정보 처리
            if "debug_info" in response_data:
                logger.info(f"응답 디버그 정보: {response_data['debug_info']}")
            
            # 트레이스 정보 처리
            if "trace" in response_data and response_data["trace"]:
                process_trace_data(response_data, response_type)
            else:
                logger.warning("트레이스 정보 없음")
                st.session_state.current_trace = None
            
            # 응답 메시지 추가
            add_message("assistant", output, response_type)
            
            # Converse API 대화 기록 업데이트
            if response_data.get("response_type") == "converse" and "conversation_history" in response_data:
                st.session_state.converse_history = response_data["conversation_history"]
        
        except Exception as e:
            logger.error(f"응답 생성 중 오류 발생: {str(e)}", exc_info=True)
            add_message("assistant", f"⚠️ 오류 발생: {str(e)}", "error")
        
        finally:
            # 처리 완료
            st.session_state.processing_status["is_processing"] = False
            st.session_state.pending_message = None


def process_trace_data(response_data, response_type):
    """트레이스 데이터를 처리하고 저장합니다"""
    trace_data = response_data["trace"]
    trace_type = type(trace_data).__name__
    trace_keys = list(trace_data.keys()) if isinstance(trace_data, dict) else "N/A"
    
    logger.info(f"트레이스 정보: 존재=True, 타입={trace_type}, 키={trace_keys}")
    
    # 트레이스 정보 저장
    st.session_state.current_trace = {
        "trace_data": ensure_json_serializable(trace_data),
        "response_type": response_type,
        "timestamp": time.time()
    }
    logger.info("✅ 트레이스 정보 저장 완료")
    
    # 디버깅용 파일 저장
    try:
        with open("last_trace.json", "w") as f:
            json.dump(ensure_json_serializable(trace_data), f, indent=2)
    except Exception as e:
        logger.warning(f"트레이스 파일 저장 실패: {str(e)}")


def generate_response(prompt, mode):
    """선택된 모드에 따라 응답을 생성합니다"""
    
    # Foundation Model 모드
    if mode == "Foundation Model":
        model_id = st.session_state.get("model_id")
        # 이 부분을 수정:
        response = invoke_model(prompt, model_id)  # invoke_foundation_model -> invoke_model
        return {
            "response_type": "foundation_model",
            "output": response
        }
    
    # Converse API 모드
    elif mode == "Converse API":
        model_id = st.session_state.get("model_id")
        temperature = st.session_state.get("temperature", 0.7)
        max_tokens = st.session_state.get("max_tokens", 1024)
        
        return invoke_converse(
            prompt, 
            conversation_history=st.session_state.converse_history,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    # Knowledge Base Retrieve 모드
    elif mode == "Knowledge Base (Retrieve)":
        kb_id = st.session_state.get("knowledge_base_id")
        response = query_knowledge_base(prompt, kb_id, retrieve_only=True)
        
        # 검색 결과 포맷팅
        if response.get("results"):
            response["output"] = format_kb_results(response["results"])
        else:
            response["output"] = "검색 결과가 없습니다."
            
        return response
    
    # Knowledge Base Retrieve & Generate 모드
    elif mode == "Knowledge Base (Retrieve & Generate)":
        kb_id = st.session_state.get("knowledge_base_id")
        return query_knowledge_base(prompt, kb_id, retrieve_only=False)
    
    # Agent 모드
    elif mode == "Agent":
        agent_id = st.session_state.get("agent_id")
        agent_alias_id = st.session_state.get("agent_alias_id")
        enable_trace = True
        
        logger.info(f"Agent API 호출 - enableTrace: {enable_trace}")
        
        return invoke_agent(prompt, agent_id=agent_id, 
                           agent_alias_id=agent_alias_id,
                           enable_trace=enable_trace)
    
    # Flow 모드
    elif mode == "Flow":
        flow_id = st.session_state.get("flow_id")
        flow_alias_id = st.session_state.get("flow_alias_id")
        enable_trace = True
        
        logger.info(f"Flow API 호출 - enableTrace: {enable_trace}")
        
        response = invoke_flow(
            prompt, 
            flow_id=flow_id,
            flow_alias_id=flow_alias_id,
            enable_trace=enable_trace
        )
        
        # 추출된 데이터 저장
        if "extracted_data" in response:
            st.session_state.flow_extracted_data = response["extracted_data"]
            
        return response
    
    # 알 수 없는 모드
    else:
        return {
            "response_type": "error",
            "output": f"선택한 응답 모드가 유효하지 않습니다: {mode}"
        }


def format_kb_results(results):
    """지식베이스 검색 결과를 읽기 쉬운 마크다운 형식으로 변환합니다"""
    formatted_output = f"## 검색 결과 ({len(results)}개)\n\n"
    
    for i, result in enumerate(results):
        formatted_output += f"### 결과 {i+1} (점수: {result['score']:.4f})\n"
        formatted_output += f"{result['content']}\n\n"
        
        source = result.get('source', 'Unknown')
        filename = result.get('source_filename', 'Unknown')
        formatted_output += f"**출처:** [{filename}]({source})\n\n---\n\n"
    
    return formatted_output