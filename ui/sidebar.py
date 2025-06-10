# Path: /bedrock_chatbot_app/ui/sidebar.py

"""
Streamlit 애플리케이션의 사이드바 UI 구성 모듈

사이드바 UI는 다양한 응답 모드 설정, 파라미터 입력, 대화 관리 기능을 제공하며
사용자가 샘플 프롬프트를 선택할 수 있는 인터페이스를 제공합니다.
"""
import streamlit as st
from lib.config import config

# 모든 모드에서 공통으로 사용할 샘플 프롬프트
SAMPLE_PROMPTS = [
    "특정 디플로이먼트(Deployment)의 상세 정보를 조회해줘"
]

# 모델 옵션 목록
MODEL_OPTIONS = [
    "anthropic.claude-3-sonnet-20240229-v1:0", 
    "anthropic.claude-3-haiku-20240307-v1:0", 
    "amazon.titan-text-express-v1"
]

def render_sidebar():
    """애플리케이션 사이드바 UI를 렌더링합니다."""
    with st.sidebar:
        st.title("EKS 클러스터 운영 어시스턴트")
        
        # 설정 섹션
        st.header("설정")
        render_response_mode_selector()
        
        # 파라미터 섹션
        st.header("파라미터")
        render_parameter_inputs()
        
        # 설정 저장 및 대화 초기화 버튼
        render_action_buttons()
        
        # 샘플 프롬프트 섹션
        st.header("샘플 프롬프트")
        render_sample_prompts()
        
        # 푸터
        st.divider()
        st.write("EKS 클러스터 운영 어시스턴트")


def render_response_mode_selector():
    """응답 모드 선택 라디오 버튼을 렌더링합니다."""
    st.session_state.response_mode = st.radio(
        "응답 모드 선택",
        ["Agent"],
        index=0,
        help="채팅봇이 사용할 응답 생성 방식을 선택하세요."
    )


def render_parameter_inputs():
    """선택된 응답 모드에 따라 적절한 파라미터 입력 필드를 렌더링합니다."""
    mode = st.session_state.response_mode
    
    # Foundation Model 설정
    if mode == "Foundation Model":
        st.session_state.model_id = st.selectbox(
            "모델 선택", MODEL_OPTIONS, index=0,
            help="사용할 파운데이션 모델을 선택하세요."
        )
    
    # Converse API 설정
    elif mode == "Converse API":
        st.session_state.model_id = st.selectbox(
            "모델 선택", MODEL_OPTIONS, index=0,
            help="사용할 파운데이션 모델을 선택하세요."
        )
        st.session_state.temperature = st.slider(
            "Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1,
            help="높을수록 더 창의적인 응답을 생성합니다."
        )
        st.session_state.max_tokens = st.number_input(
            "최대 토큰 수", min_value=100, max_value=4000, value=1024, step=100,
            help="응답에 사용할 최대 토큰 수를 설정합니다."
        )
    
    # Knowledge Base 설정
    elif "Knowledge Base" in mode:
        st.session_state.knowledge_base_id = st.text_input(
            "Knowledge Base ID", config.knowledge_base_id,
            help="사용할 Knowledge Base의 ID를 입력하세요."
        )
    
    # Agent 설정
    elif mode == "Agent":
        st.session_state.agent_id = st.text_input(
            "Agent ID", config.agent_id,
            help="사용할 Agent의 ID를 입력하세요. 예: WCTRUTGMGO"
        )
        st.session_state.agent_alias_id = st.text_input(
            "Agent Alias ID", config.agent_alias_id,
            help="사용할 Agent Alias의 ID를 입력하세요. 예: DGHR6RUQQV"
        )
    
    # Flow 설정
    elif mode == "Flow":
        st.session_state.flow_id = st.text_input(
            "Flow ID", config.flow_id,
            help="사용할 Flow ID를 입력하세요. 예: 948RU2IFMO"
        )
        st.session_state.flow_alias_id = st.text_input(
            "Flow Alias ID", config.flow_alias_id,
            help="사용할 Flow Alias ID를 입력하세요."
        )


def render_action_buttons():
    """설정 저장 및 대화 초기화 버튼을 렌더링합니다."""
    
    # 대화 초기화 버튼
    if st.button("대화 초기화", help="현재 대화 내용을 모두 삭제합니다."):
        reset_conversation()
        st.success("대화가 초기화되었습니다.")
        st.rerun()

def reset_conversation():
    """대화 기록 및 관련 상태를 초기화합니다."""
    # 초기화할 세션 상태 항목들
    reset_items = [
        {"key": "chat_messages", "default": []},
        {"key": "current_trace", "default": None},
        {"key": "converse_history", "default": []},
        {"key": "processing_status", "default": {
            "is_processing": False,
            "current_prompt": None,
            "current_mode": None
        }}
    ]
    
    for item in reset_items:
        if item["key"] in st.session_state:
            st.session_state[item["key"]] = item["default"]


def render_sample_prompts():
    """모든 모드에서 공통으로 사용할 샘플 프롬프트 버튼을 렌더링합니다."""
    # 처리 중일 때는 샘플 프롬프트 비활성화
    disabled = st.session_state.get("processing_status", {}).get("is_processing", False)
    
    st.write("샘플 질문:")
    
    # 모든 샘플 프롬프트에 대한 버튼 생성
    for i, prompt in enumerate(SAMPLE_PROMPTS):
        button_key = f"sample_prompt_{i}"
        
        # 문자열인 경우만 처리 (JSON 예제 제외)
        if isinstance(prompt, str):
            if st.button(prompt, key=button_key, disabled=disabled):
                st.session_state.clicked_prompt = prompt
                st.rerun()