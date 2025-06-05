
import streamlit as st
from datetime import datetime
import pandas as pd
from config import get_current_aws_identity
from permission_utils import check_eks_permissions, update_aws_auth_configmap

def render_bedrock_sidebar(aws_clients):
    """Bedrock 모델 설정 사이드바를 렌더링합니다."""
    from bedrock_utils import get_available_models, get_simple_model_name
    
    with st.expander("🤖 Bedrock 모델 설정", expanded=True):
        # 사용 가능한 모델 목록 조회
        if 'available_models' not in st.session_state:
            with st.spinner("사용 가능한 모델을 조회하는 중..."):
                models = get_available_models(aws_clients['bedrock'])
                st.session_state.available_models = models
        
        models = st.session_state.get('available_models', [])
        
        if models:
            model_options = [get_simple_model_name(model['modelId'], model['providerName']) for model in models]
            model_ids = [model['modelId'] for model in models]
            
            # Claude 3.5 Sonnet을 기본값으로 찾기
            default_index = 0
            for i, model_id in enumerate(model_ids):
                if 'claude-3-5-sonnet' in model_id:
                    default_index = i
                    break
            
            selected_index = st.selectbox(
                "사용할 모델 선택",
                range(len(model_options)),
                format_func=lambda x: model_options[x],
                index=default_index,
                help="Bedrock에서 사용할 AI 모델을 선택하세요"
            )
            
            selected_model_id = model_ids[selected_index]
            
            # 모델 파라미터 설정
            col1, col2 = st.columns(2)
            with col1:
                temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.7,
                    step=0.1,
                    help="창의성 조절 (0: 일관성, 1: 창의적)"
                )
                
                top_p = st.slider(
                    "Top P",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.9,
                    step=0.1,
                    help="nucleus sampling 확률 (0.1: 보수적, 0.9: 다양한)"
                )
            
            with col2:
                max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=100,
                    max_value=4000,
                    value=1000,
                    step=100,
                    help="최대 응답 길이"
                )
                
                top_k = st.number_input(
                    "Top K",
                    min_value=1,
                    max_value=500,
                    value=250,
                    step=10,
                    help="상위 K개 토큰 선택 (낮을수록 일관성)"
                )
            
            # 설정 저장
            st.session_state.selected_model_id = selected_model_id
            st.session_state.temperature = temperature
            st.session_state.max_tokens = max_tokens
            st.session_state.top_p = top_p
            st.session_state.top_k = top_k
            
            st.success(f"✅ 선택된 모델: {model_options[selected_index]}")
        else:
            st.warning("사용 가능한 모델이 없습니다.")
            if st.button("🔄 모델 목록 새로고침"):
                if 'available_models' in st.session_state:
                    del st.session_state.available_models
                st.rerun()

def render_permission_management_sidebar(aws_clients):
    """권한 관리 사이드바를 렌더링합니다."""
    st.markdown("#### 🔐 권한 관리")
    
    with st.expander("🛠️ EKS 권한 직접 관리", expanded=False):
        if aws_clients and st.session_state.get('selected_cluster'):
            cluster_name = st.session_state.selected_cluster['name']
            
            # 현재 AWS 자격 증명 정보 표시
            aws_identity = get_current_aws_identity()
            if aws_identity:
                st.markdown("##### 현재 AWS 자격 증명:")
                st.text(f"계정: {aws_identity['account']}")
                st.text(f"ARN: {aws_identity['arn']}")
                
                # 권한 확인 버튼
                if st.button("🔍 현재 권한 확인"):
                    from kubernetes_utils import get_kubernetes_client
                    k8s_client = get_kubernetes_client(aws_clients['eks'], cluster_name)
                    if k8s_client:
                        permissions = check_eks_permissions(k8s_client)
                        st.markdown("##### 권한 상태:")
                        for perm, status in permissions.items():
                            emoji = "✅" if status else "❌"
                            st.text(f"{emoji} {perm}")
                    else:
                        st.error("Kubernetes 클라이언트 연결 실패")
                
                # aws-auth 직접 수정
                st.markdown("##### aws-auth ConfigMap 직접 수정:")
                username = st.text_input("사용자명", value="admin", help="aws-auth에 추가할 사용자명")
                
                groups_options = st.multiselect(
                    "권한 그룹",
                    ["system:masters", "system:nodes", "system:bootstrappers"],
                    default=["system:masters"],
                    help="사용자에게 부여할 Kubernetes 그룹"
                )
                
                if st.button("🔧 권한 직접 추가", type="primary"):
                    if username and groups_options:
                        success = update_aws_auth_configmap(
                            aws_clients['eks'],
                            cluster_name,
                            aws_identity['arn'],
                            username,
                            groups_options
                        )
                        if success:
                            st.success("✅ 권한이 성공적으로 추가되었습니다!")
                            st.info("💡 변경사항이 적용되는데 1-2분 정도 소요될 수 있습니다.")
                        else:
                            st.error("❌ 권한 추가에 실패했습니다.")
                    else:
                        st.warning("사용자명과 권한 그룹을 선택해주세요.")
            else:
                st.warning("AWS 자격 증명 정보를 가져올 수 없습니다.")
        else:
            st.info("클러스터를 먼저 선택해주세요.")

def render_kubectl_guide_sidebar():
    """kubectl 명령어 가이드 사이드바를 렌더링합니다."""
    st.markdown("#### 🔧 kubectl 명령어 가이드")
    
    # Pod 관련 명령어
    with st.expander("📦 Pod 관리", expanded=False):
        st.code("kubectl get pods", language="bash")
        st.code("kubectl get pods -o wide", language="bash")
        st.code("kubectl describe pod <pod-name>", language="bash")
        st.code("kubectl logs <pod-name>", language="bash")
        st.code("kubectl exec -it <pod-name> -- /bin/bash", language="bash")
        st.code("kubectl delete pod <pod-name>", language="bash")
    
    # Deployment 관련 명령어
    with st.expander("🚀 Deployment 관리", expanded=False):
        st.code("kubectl get deployments", language="bash")
        st.code("kubectl describe deployment <deployment-name>", language="bash")
        st.code("kubectl scale deployment <deployment-name> --replicas=3", language="bash")
        st.code("kubectl rollout status deployment/<deployment-name>", language="bash")
        st.code("kubectl rollout restart deployment/<deployment-name>", language="bash")
        st.code("kubectl rollout undo deployment/<deployment-name>", language="bash")
    
    # Service 관련 명령어
    with st.expander("🌐 Service 관리", expanded=False):
        st.code("kubectl get services", language="bash")
        st.code("kubectl get svc", language="bash")
        st.code("kubectl describe service <service-name>", language="bash")
        st.code("kubectl port-forward service/<service-name> 8080:80", language="bash")
        st.code("kubectl expose deployment <deployment-name> --port=80 --type=LoadBalancer", language="bash")
    
    # 클러스터 정보 명령어
    with st.expander("📊 클러스터 정보", expanded=False):
        st.code("kubectl cluster-info", language="bash")
        st.code("kubectl get nodes", language="bash")
        st.code("kubectl get nodes -o wide", language="bash")
        st.code("kubectl top nodes", language="bash")
        st.code("kubectl top pods", language="bash")
        st.code("kubectl get namespaces", language="bash")
    
    # ConfigMap & Secret 명령어
    with st.expander("🔐 ConfigMap & Secret", expanded=False):
        st.code("kubectl get configmaps", language="bash")
        st.code("kubectl get secrets", language="bash")
        st.code("kubectl describe configmap <configmap-name>", language="bash")
        st.code("kubectl describe secret <secret-name>", language="bash")
        st.code("kubectl create secret generic <secret-name> --from-literal=key=value", language="bash")
    
    # 리소스 관리 명령어
    with st.expander("📋 리소스 관리", expanded=False):
        st.code("kubectl get all", language="bash")
        st.code("kubectl get all -n <namespace>", language="bash")
        st.code("kubectl apply -f <file.yaml>", language="bash")
        st.code("kubectl delete -f <file.yaml>", language="bash")
        st.code("kubectl edit deployment <deployment-name>", language="bash")
        st.code("kubectl patch deployment <deployment-name> -p '{\"spec\":{\"replicas\":5}}'", language="bash")

def render_chat_history():
    """채팅 기록을 렌더링합니다."""
    if st.session_state.chat_history:
        st.markdown("### 💬 대화 기록")
        
        chat_container = st.container()
        
        with chat_container:
            for i, (role, message) in enumerate(st.session_state.chat_history):
                if role == "user":
                    st.markdown(f"""
                    <div style="background-color: #2b313e; padding: 10px; border-radius: 10px; margin: 10px 0; border-left: 3px solid #4CAF50;">
                        <strong>👤 사용자:</strong><br>
                        {message}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    formatted_message = message.replace('\n', '<br>')
                    st.markdown(f"""
                    <div style="background-color: #1e1e1e; padding: 10px; border-radius: 10px; margin: 10px 0; border-left: 3px solid #2196F3;">
                        <strong>🤖 어시스턴트:</strong><br>
                        {formatted_message}
                    </div>
                    """, unsafe_allow_html=True)

def render_css_styles():
    """CSS 스타일링을 렌더링합니다."""
    st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117;
        }
        
        .stSidebar {
            background-color: #1e1e1e;
        }
        
        .stButton > button {
            background-color: #262730;
            color: white;
            border: 1px solid #333;
            border-radius: 6px;
        }
        
        .stButton > button:hover {
            background-color: #364364;
            border-color: #4a90e2;
        }
        
        .stTextInput > div > div > input {
            background-color: #1e1e1e;
            color: white;
            border: 1px solid #333;
        }
        
        .stSelectbox > div > div > select {
            background-color: #1e1e1e;
            color: white;
            border: 1px solid #333;
        }
        
        h1 {
            color: white;
            font-size: 1.2rem;
        }
        
        h2 {
            color: white;
            font-size: 1.1rem;
        }
        
        h3 {
            color: white;
            font-size: 1rem;
        }
        
        h4 {
            color: white;
            font-size: 0.9rem;
        }
        
        p {
            color: #ccc;
            font-size: 0.85rem;
        }
        
        .stMarkdown {
            font-size: 0.85rem;
        }
        
        /* Metric 값들 폰트 크기 조정 */
        [data-testid="metric-container"] [data-testid="metric-value"] {
            font-size: 0.9rem !important;
        }
        
        [data-testid="metric-container"] [data-testid="metric-label"] {
            font-size: 0.8rem !important;
        }
        
        [data-testid="metric-container"] [data-testid="metric-delta"] {
            font-size: 0.75rem !important;
        }
        
        .stMetric {
            font-size: 0.8rem !important;
        }
        
        .stInfo, .stSuccess, .stWarning, .stError {
            font-size: 0.8rem !important;
        }
        
        .stCode {
            font-size: 0.75rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem !important;
        }
        
        .stButton > button {
            font-size: 0.8rem !important;
        }
        
        .stTextInput input, .stSelectbox select {
            font-size: 0.8rem !important;
        }
    </style>
    """, unsafe_allow_html=True)
