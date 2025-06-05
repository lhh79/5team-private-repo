
import streamlit as st
from datetime import datetime
import pandas as pd
import os

# Import custom modules
from config import init_aws_clients
from eks_utils import get_eks_clusters
from compute_nodes_utils import get_compute_nodes_info
from bedrock_utils import invoke_bedrock_model
from ui_components import (
    render_bedrock_sidebar, 
    render_permission_management_sidebar, 
    render_kubectl_guide_sidebar, 
    render_chat_history, 
    render_css_styles
)

def main():
    """메인 Streamlit 애플리케이션"""
    
    # 페이지 설정
    st.set_page_config(
        page_title="EKS Assistant",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS 스타일 적용
    render_css_styles()
    
    # 세션 상태 초기화
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'aws_clients' not in st.session_state:
        st.session_state.aws_clients = None
    if 'selected_cluster' not in st.session_state:
        st.session_state.selected_cluster = None
    
    # 메인 타이틀
    st.title("🚀 EKS Assistant")
    st.markdown("AWS EKS 클러스터 관리 및 AI 어시스턴트")
    
    # 사이드바
    with st.sidebar:
        st.markdown("## ⚙️ 설정")
        
        # AWS 클라이언트 초기화
        if st.button("🔄 AWS 연결"):
            with st.spinner("AWS 클라이언트를 초기화하는 중..."):
                try:
                    aws_clients = init_aws_clients()
                    if aws_clients:
                        st.session_state.aws_clients = aws_clients
                        st.success("✅ AWS 연결 성공!")
                    else:
                        st.error("❌ AWS 연결 실패")
                except Exception as e:
                    st.error(f"AWS 연결 오류: {str(e)}")
        
        # EKS 클러스터 선택
        if st.session_state.aws_clients:
            st.markdown("### 🎯 클러스터 선택")
            
            if st.button("🔍 클러스터 조회"):
                with st.spinner("EKS 클러스터를 조회하는 중..."):
                    clusters = get_eks_clusters(st.session_state.aws_clients['eks'])
                    if clusters:
                        st.session_state.clusters = clusters
                        st.success(f"✅ {len(clusters)}개 클러스터 발견")
                    else:
                        st.warning("클러스터를 찾을 수 없습니다.")
            
            # 클러스터 선택
            if 'clusters' in st.session_state and st.session_state.clusters:
                cluster_names = [cluster['name'] for cluster in st.session_state.clusters]
                selected_cluster_name = st.selectbox(
                    "클러스터 선택",
                    cluster_names,
                    help="관리할 EKS 클러스터를 선택하세요"
                )
                
                if selected_cluster_name:
                    selected_cluster = next(
                        cluster for cluster in st.session_state.clusters 
                        if cluster['name'] == selected_cluster_name
                    )
                    st.session_state.selected_cluster = selected_cluster
            
            # Bedrock 설정
            render_bedrock_sidebar(st.session_state.aws_clients)
            
            # 권한 관리
            render_permission_management_sidebar(st.session_state.aws_clients)
            
            # kubectl 가이드
            render_kubectl_guide_sidebar()
    
    # 메인 콘텐츠
    if st.session_state.selected_cluster:
        cluster = st.session_state.selected_cluster
        
        # 클러스터 정보 표시
        st.markdown(f"## 📊 클러스터: {cluster['name']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("상태", cluster['status'])
        with col2:
            st.metric("버전", cluster['version'])
        with col3:
            st.metric("리전", cluster.get('region', 'N/A'))
        
        # 컴퓨트 노드 정보
        st.markdown("### 💻 컴퓨트 노드 정보")
        
        if st.button("🔄 노드 정보 새로고침"):
            with st.spinner("노드 정보를 조회하는 중..."):
                nodes_info = get_compute_nodes_info(
                    st.session_state.aws_clients,
                    cluster['name']
                )
                st.session_state.nodes_info = nodes_info
        
        # 노드 정보 표시
        if 'nodes_info' in st.session_state:
            nodes_info = st.session_state.nodes_info
            
            # 메트릭 표시
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 노드", nodes_info.get('total_nodes', 0))
            with col2:
                st.metric("Ready 노드", nodes_info.get('ready_nodes', 0))
            with col3:
                st.metric("총 CPU", f"{nodes_info.get('total_capacity', {}).get('cpu', 0)} cores")
            with col4:
                st.metric("총 메모리", f"{nodes_info.get('total_capacity', {}).get('memory', 0)} GB")
            
            # Pod 정보
            if nodes_info.get('real_pods'):
                st.markdown("### 📦 Pod 정보")
                
                pods_df = pd.DataFrame([
                    {
                        'Name': pod['name'],
                        'Namespace': pod['namespace'],
                        'Status': pod['status'],
                        'Node': pod['node'],
                        'CPU Request': pod.get('cpu_request', 'N/A'),
                        'Memory Request': pod.get('memory_request', 'N/A')
                    }
                    for pod in nodes_info['real_pods']
                ])
                
                st.dataframe(pods_df, use_container_width=True)
                
                # Pod 상태 요약
                pod_status_counts = pods_df['Status'].value_counts()
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Running Pods", pod_status_counts.get('Running', 0))
                with col2:
                    st.metric("Pending Pods", pod_status_counts.get('Pending', 0))
                with col3:
                    st.metric("Failed Pods", pod_status_counts.get('Failed', 0))
        
        # AI 어시스턴트 채팅
        st.markdown("### 🤖 AI 어시스턴트")
        
        # 채팅 입력
        user_question = st.text_input(
            "질문을 입력하세요:",
            placeholder="EKS 클러스터에 대해 궁금한 것을 물어보세요...",
            key="chat_input"
        )
        
        if st.button("💬 질문하기") and user_question:
            if st.session_state.aws_clients and 'selected_model_id' in st.session_state:
                with st.spinner("AI가 답변을 생성하는 중..."):
                    try:
                        # 클러스터 컨텍스트 정보 준비
                        context_info = ""
                        if 'nodes_info' in st.session_state:
                            nodes_info = st.session_state.nodes_info
                            context_info = f"""
현재 선택된 클러스터: {cluster['name']}
- 상태: {cluster['status']}
- 버전: {cluster['version']}
- 총 노드: {nodes_info.get('total_nodes', 0)}
- Ready 노드: {nodes_info.get('ready_nodes', 0)}
- 총 CPU: {nodes_info.get('total_capacity', {}).get('cpu', 0)} cores
- 총 메모리: {nodes_info.get('total_capacity', {}).get('memory', 0)} GB
"""
                            if nodes_info.get('real_pods'):
                                context_info += f"- 총 Pod 수: {len(nodes_info['real_pods'])}\n"
                        
                        # Bedrock 호출
                        prompt = f"""다음 EKS 클러스터 정보를 바탕으로 사용자의 질문에 답변해주세요:

{context_info}

사용자 질문: {user_question}

친절하고 전문적으로 답변해주세요. 필요하다면 kubectl 명령어나 구체적인 해결방법도 제시해주세요."""
                        
                        response = invoke_bedrock_model(
                            st.session_state.aws_clients['bedrock'],
                            st.session_state.selected_model_id,
                            prompt,
                            temperature=st.session_state.get('temperature', 0.7),
                            max_tokens=st.session_state.get('max_tokens', 1000),
                            top_p=st.session_state.get('top_p', 0.9),
                            top_k=st.session_state.get('top_k', 250)
                        )
                        
                        if response:
                            # 채팅 기록에 추가
                            st.session_state.chat_history.append(("user", user_question))
                            st.session_state.chat_history.append(("assistant", response))
                            
                            # 입력 초기화
                            st.rerun()
                        else:
                            st.error("AI 응답을 받지 못했습니다.")
                            
                    except Exception as e:
                        st.error(f"AI 응답 생성 중 오류 발생: {str(e)}")
            else:
                st.warning("AWS 연결과 Bedrock 모델을 먼저 설정해주세요.")
        
        # 채팅 기록 표시
        render_chat_history()
    
    else:
        # 클러스터가 선택되지 않은 경우
        st.info("👈 사이드바에서 AWS에 연결하고 클러스터를 선택해주세요.")
        
        # 기본 정보 표시
        st.markdown("""
        ## 🎯 시작하기
        
        1. **AWS 연결**: 사이드바에서 "AWS 연결" 버튼을 클릭하세요
        2. **클러스터 선택**: "클러스터 조회" 버튼으로 EKS 클러스터를 찾고 선택하세요
        3. **AI 어시스턴트**: Bedrock 모델을 설정하고 질문하세요
        
        ### 📋 주요 기능
        - 🎯 EKS 클러스터 모니터링
        - 💻 컴퓨트 노드 정보 조회
        - 📦 Pod 상태 확인
        - 🤖 AI 기반 문제 해결 지원
        - 🔐 권한 관리 도구
        - 📚 kubectl 명령어 가이드
        """)

if __name__ == "__main__":
    main()
