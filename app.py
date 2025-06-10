# Path: /bedrock_chatbot_app/app.py
#
# 애플리케이션의 진입점(entry point) 역할을 하는 메인 파일
# Streamlit 앱 설정을 구성하고 메인 UI를 렌더링합니다.

import streamlit as st
from ui.main import render_main_ui

# Streamlit 앱 설정
st.set_page_config(
    page_title="Amazon Bedrock 채팅봇",  # 브라우저 탭에 표시될 제목
    page_icon="🤖",                     # 브라우저 탭에 표시될 아이콘
    layout="wide",                      # 화면 레이아웃 (wide: 전체 화면 사용)
    initial_sidebar_state="expanded"    # 사이드바 초기 상태 (expanded: 펼침)
)

# 메인 UI 렌더링 함수 호출
render_main_ui()