# Path: /bedrock_chatbot_app/ui/trace_viewer.py

"""
Bedrock 서비스의 트레이스 정보를 시각화하는 UI 모듈
Agent 및 Flow 실행 과정의 상세 정보를 사용자에게 보기 좋게 표시합니다.
"""

import streamlit as st
import json
from lib.trace_utils import extract_trace_summary

def format_trace_for_display(trace):
    """
    트레이스 정보를 UI 표시용으로 포맷팅합니다.
    """
    if not trace:
        return "트레이스 정보가 없습니다."
    
    # 딕셔너리를 보기 좋은 JSON 형태로 변환
    formatted_trace = json.dumps(trace, indent=2, ensure_ascii=False)
    return formatted_trace

def render_trace_viewer():
    """
    트레이스 정보 뷰어 UI를 렌더링합니다.
    
    현재 세션에 저장된 트레이스 정보를 읽어서 요약 및 상세 정보 탭으로 구분하여 표시합니다.
    에이전트나 플로우의 실행 과정을 이해하고 디버깅하는 데 도움이 되는 정보를 제공합니다.
    
    Converse API의 경우 대화 기록을 표시합니다.
    
    트레이스 정보가 없는 경우 안내 메시지를 표시합니다.
    """

    # 디버깅 정보 추가
    st.write("### 트레이스 디버그 정보")
    
    # 세션 상태 확인
    if 'current_trace' in st.session_state:
        if st.session_state.current_trace:
            st.success("세션에 트레이스 정보가 있습니다")
            st.write(f"트레이스 유형: {st.session_state.current_trace.get('response_type')}")
            
            # 트레이스 데이터 확인
            trace_data = st.session_state.current_trace.get("trace_data")
            if trace_data:
                st.success("트레이스 데이터가 존재합니다")
                # 트레이스 데이터 일부 표시
                st.json({k: str(type(v)) for k, v in trace_data.items()} if isinstance(trace_data, dict) else {"데이터 타입": str(type(trace_data))})
            else:
                st.error("트레이스 데이터가 None입니다")
        else:
            st.warning("세션에 트레이스 객체가 있지만 내용이 없습니다")
    else:
        st.error("세션에 트레이스 정보가 없습니다")
        
    # 세션에 저장된 트레이스 정보가 있는지 확인
    if st.session_state.current_trace:
        # 트레이스 데이터 및 응답 유형 가져오기
        trace_data = st.session_state.current_trace["trace_data"]
        response_type = st.session_state.current_trace["response_type"]
        
        # 트레이스 뷰어 제목
        st.header("트레이스 정보")
        
        # 요약 및 상세 정보를 탭으로 구성
        tab1, tab2 = st.tabs(["요약", "상세 정보"])
        
        # 요약 탭 내용
        with tab1:
            if trace_data:
                # 트레이스 정보에서 요약 정보 추출
                try:
                    summary = extract_trace_summary(trace_data, response_type)
                    st.subheader("요약")
                    
                    # 에러 메시지가 있는 경우 표시
                    if isinstance(trace_data, dict) and trace_data.get("error"):
                        st.error(trace_data["error"])
                    
                    # 응답 유형에 따라 다른 요약 정보 표시
                    elif response_type == "agent":
                        # 에이전트 실행 단계 요약
                        st.write(f"총 실행 단계: {summary.get('steps_count', 0)}")
                        
                        # API 호출 정보 표시
                        if summary.get("api_calls"):
                            st.subheader("API 호출")
                            for i, call in enumerate(summary.get("api_calls", [])):
                                st.write(f"{i+1}. {call.get('api')} - 상태: {call.get('status')}")
                    
                    elif response_type == "flow":
                        # 플로우 실행 노드 요약
                        st.write(f"총 노드 수: {summary.get('nodes_count', 0)}")
                        
                        # 노드 실행 상태 표시
                        if summary.get("node_execution"):
                            st.subheader("노드 실행 상태")
                            for i, node in enumerate(summary.get("node_execution", [])):
                                st.write(f"{i+1}. {node.get('node_id')} - 상태: {node.get('status')}")
                    
                    # 기타 응답 유형이나 알 수 없는 구조의 요약 정보는 JSON으로 표시
                    else:
                        st.json(summary)
                        
                except Exception as e:
                    st.error(f"트레이스 요약 처리 중 오류 발생: {str(e)}")
                    if isinstance(trace_data, dict):
                        st.json(trace_data)
            else:
                st.write("요약 정보가 없습니다.")
        
        # 상세 정보 탭 내용
        with tab2:
            try:
                if trace_data:
                    # 트레이스 전체 정보를 포맷팅하여 코드 블록으로 표시
                    st.subheader("전체 트레이스")
                    st.code(format_trace_for_display(trace_data), language="json")
                else:
                    st.write("트레이스 정보가 없습니다.")
            except Exception as e:
                st.error(f"트레이스 데이터 표시 중 오류 발생: {str(e)}")
                st.write("원본 트레이스 데이터:")
                st.json(trace_data)
                
    # Converse API 대화 기록 표시 (트레이스 정보가 없어도)
    elif st.session_state.response_mode == "Converse API" and hasattr(st.session_state, 'converse_history') and st.session_state.converse_history:
        st.header("Converse 대화 기록")
        
        # 대화 기록 테이블로 표시
        converse_history = st.session_state.converse_history
        
        # 대화 흐름을 시각적으로 표시
        for i, msg in enumerate(converse_history):
            role = msg["role"]
            content = msg["content"]
            
            # 역할에 따라 다른 색상으로 표시
            if role == "user":
                st.info(f"👤 사용자: {content}")
            else:
                st.success(f"🤖 어시스턴트: {content}")
                
            # 대화 차례를 구분하는 구분선 (마지막 메시지 제외)
            if i < len(converse_history) - 1:
                st.divider()
    else:
        # 트레이스 정보가 없는 경우 안내 메시지 표시
        st.info("트레이스 정보가 없습니다. 채팅을 시작하면 트레이스 정보가 여기에 표시됩니다.")