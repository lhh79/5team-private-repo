import boto3
import json
import uuid
import streamlit as st
from datetime import datetime, timedelta

class DynamoDBSessionManager:
    def __init__(self, table_name='StreamlitSessions', region='us-west-2', ttl_days=7):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.ttl_days = ttl_days
        
        # 세션 ID가 없으면 생성
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
    
    def save_session(self, data):
        """세션 데이터를 DynamoDB에 저장"""
        try:
            # TTL 설정 (Unix 타임스탬프)
            expiration_time = int((datetime.now() + timedelta(days=self.ttl_days)).timestamp())
            
            # 저장할 데이터 준비
            session_data = {
                'SessionId': st.session_state.session_id,
                'Data': json.dumps(data),
                'LastUpdated': datetime.now().isoformat(),
                'TTL': expiration_time
            }
            
            # DynamoDB에 저장
            self.table.put_item(Item=session_data)
            return True
        except Exception as e:
            st.error(f"세션 저장 중 오류 발생: {e}")
            return False
    
    def load_session(self):
        """DynamoDB에서 세션 데이터 로드"""
        try:
            response = self.table.get_item(
                Key={'SessionId': st.session_state.session_id}
            )
            
            if 'Item' in response:
                return json.loads(response['Item']['Data'])
            return {}
        except Exception as e:
            st.error(f"세션 로드 중 오류 발생: {e}")
            return {}
    
    def delete_session(self):
        """세션 데이터 삭제"""
        try:
            self.table.delete_item(
                Key={'SessionId': st.session_state.session_id}
            )
            # 세션 ID 재생성
            st.session_state.session_id = str(uuid.uuid4())
            return True
        except Exception as e:
            st.error(f"세션 삭제 중 오류 발생: {e}")
            return False

def create_dynamodb_table(table_name='StreamlitSessions', region='us-west-2'):
    """DynamoDB 테이블이 없으면 생성"""
    try:
        dynamodb = boto3.client('dynamodb', region_name=region)
        
        # 테이블이 이미 존재하는지 확인
        existing_tables = dynamodb.list_tables()
        if table_name in existing_tables.get('TableNames', []):
            return True
        
        # 테이블 생성
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'SessionId',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'SessionId',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'TTL'
            }
        )
        
        # 테이블이 생성될 때까지 대기
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        return True
    except Exception as e:
        st.error(f"DynamoDB 테이블 생성 중 오류 발생: {e}")
        return False
