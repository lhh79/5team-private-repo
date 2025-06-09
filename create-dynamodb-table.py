import boto3
import argparse
import time

def create_dynamodb_table(table_name, region):
    """DynamoDB 테이블 생성"""
    try:
        print(f"DynamoDB 테이블 '{table_name}' 생성을 시작합니다...")
        
        # DynamoDB 클라이언트 생성
        dynamodb = boto3.client('dynamodb', region_name=region)
        
        # 테이블이 이미 존재하는지 확인
        try:
            existing_tables = dynamodb.list_tables()
            if table_name in existing_tables.get('TableNames', []):
                print(f"테이블 '{table_name}'이(가) 이미 존재합니다.")
                return True
        except Exception as e:
            print(f"테이블 목록 조회 중 오류 발생: {e}")
        
        # 테이블 생성
        response = dynamodb.create_table(
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
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"테이블 생성 요청 완료: {response['TableDescription']['TableStatus']}")
        
        # 테이블이 생성될 때까지 대기
        print("테이블이 생성될 때까지 대기 중...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        # TTL 활성화
        print("TTL 활성화 중...")
        dynamodb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'TTL'
            }
        )
        
        print(f"DynamoDB 테이블 '{table_name}' 생성 완료!")
        return True
    except Exception as e:
        print(f"DynamoDB 테이블 생성 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DynamoDB 테이블 생성')
    parser.add_argument('--table-name', default='StreamlitSessions', help='생성할 DynamoDB 테이블 이름')
    parser.add_argument('--region', default='us-west-2', help='AWS 리전')
    
    args = parser.parse_args()
    create_dynamodb_table(args.table_name, args.region)
