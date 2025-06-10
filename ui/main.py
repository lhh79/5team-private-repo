# Path: /bedrock_chatbot_app/ui/main.py

"""
애플리케이션의 메인 UI 구성을 담당하는 모듈
사이드바, 채팅 인터페이스를 조합하여 
전체 애플리케이션 레이아웃을 구성합니다.
"""

import streamlit as st
from ui.sidebar import render_sidebar
from ui.chat_interface import init_chat, display_chat_history, process_user_input, handle_sample_prompt, check_pending_response

def render_main_ui():
    """
    애플리케이션의 메인 UI를 렌더링합니다.
    
    애플리케이션 제목, 사이드바, 채팅 인터페이스를 
    적절한 레이아웃으로 배치합니다.
    """
    # 애플리케이션 제목
    st.title("EKS 클러스터 운영 어시스턴트")
    
    # 채팅 인터페이스 초기화 (세션 상태 준비)
    init_chat()
    
    # 대기 중인 응답 확인 및 처리
    check_pending_response()
    
    # 사이드바 렌더링 (설정 및 모드 선택)
    render_sidebar()
    
    # 샘플 프롬프트 처리
    if "clicked_prompt" in st.session_state and st.session_state.clicked_prompt:
        prompt = st.session_state.clicked_prompt
        st.session_state.clicked_prompt = None  # 즉시 초기화
        handle_sample_prompt(prompt)
    
    # 현재 모드 및 상태 표시
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        # 현재 모드 표시
        current_mode = st.session_state.processing_status.get("current_mode") or st.session_state.response_mode
        st.info(f"현재 모드: **{current_mode}**", icon="ℹ️")
    
    with col_status2:
        # 처리 중 상태 표시
        if st.session_state.processing_status.get("is_processing"):
            st.warning("요청 처리 중...", icon="⏳")
        else:
            st.success("준비 완료", icon="✅")
    
    # 채팅 인터페이스 - 전체 너비 사용
    # 이전 채팅 기록 표시
    display_chat_history()
    
    # 사용자 입력 필드 및 처리 로직
    user_input = st.chat_input("메시지를 입력하세요...", disabled=st.session_state.processing_status.get("is_processing", False))
    if user_input:
        process_user_input(user_input)