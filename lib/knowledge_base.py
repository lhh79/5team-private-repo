# Path: /bedrock_chatbot_app/lib/knowledge_base.py

"""Amazon Bedrock Knowledge Base를 활용하기 위한 기능을 제공하는 모듈"""
import logging
from lib.bedrock_client import get_bedrock_agent_client
from lib.config import config

logger = logging.getLogger(__name__)

def query_knowledge_base(query, knowledge_base_id=None, retrieve_only=False):
    """
    Knowledge Base에 쿼리를 실행하여 정보를 검색하거나 생성형 응답을 얻습니다.
    
    Args:
        query (str): 검색 쿼리
        knowledge_base_id (str, optional): 사용할 Knowledge Base ID
        retrieve_only (bool): 검색만 수행할지 여부 (False면 생성형 응답 포함)
        
    Returns:
        dict: 검색 결과 또는 생성된 응답
    """
    knowledge_base_id = knowledge_base_id or config.knowledge_base_id
    
    logger.info(f"📚 Knowledge Base 쿼리 시작: {retrieve_only and '검색만' or '검색 및 생성'}")
    logger.info(f"쿼리: {query[:50]}{'...' if len(query) > 50 else ''}")
    
    try:
        client = get_bedrock_agent_client()
        
        if retrieve_only:
            # retrieve API - 검색만 수행
            logger.info("🔍 Retrieve API 호출")
            
            response = client.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5
                    }
                }
            )
            
            # 검색 결과 파싱
            retrieval_results = []
            for result in response.get("retrievalResults", []):
                content = result.get("content", {}).get("text", "")
                metadata = result.get("metadata", {})
                source = result.get("location", {}).get("s3Location", {}).get("uri", "Unknown source")
                source_filename = source.split("/")[-1] if "/" in source else source
                score = result.get("score", 0)
                
                retrieval_results.append({
                    "content": content,
                    "metadata": metadata,
                    "source": source,
                    "source_filename": source_filename,
                    "score": score
                })
            
            logger.info(f"✅ 검색 결과: {len(retrieval_results)}개 문서")
            
            return {
                "response_type": "retrieve",
                "query": query,
                "results": retrieval_results
            }
        
        else:
            # retrieve_and_generate API - 검색 + 생성형 응답
            logger.info("🔍 RetrieveAndGenerate API 호출")
            
            # 모델 ARN 구성
            model_arn = f"arn:aws:bedrock:{config.region_name}::foundation-model/{config.model_id}"
            
            response = client.retrieve_and_generate(
                input={"text": query},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": knowledge_base_id,
                        "modelArn": model_arn
                    }
                }
            )
            
            # 생성된 응답과 인용 정보 추출
            output = response.get("output", {}).get("text", "")
            citations = response.get("citations", [])
            
            # 인용 정보 처리
            citation_details = []
            for citation in citations:
                citation_text = citation.get("generatedResponsePart", {}).get("textResponsePart", {}).get("text", "")
                references = citation.get("retrievedReferences", [])
                
                for ref in references:
                    location = ref.get("location", {})
                    source = "Unknown"
                    for loc_type in ["s3Location", "webLocation", "confluenceLocation", "salesforceLocation", "sharePointLocation"]:
                        if loc_type in location:
                            source = location[loc_type].get("uri", location[loc_type].get("url", "Unknown"))
                            break
                            
                    source_filename = source.split("/")[-1] if "/" in source else source
                    content = ref.get("content", {}).get("text", "")
                    
                    citation_details.append({
                        "generated_part": citation_text,
                        "source_file": source_filename,
                        "source_uri": source,
                        "referenced_content": content
                    })
            
            logger.info(f"✅ 응답 생성 완료: {len(output)} 글자, {len(citation_details)} 인용")
            
            return {
                "response_type": "retrieve_and_generate",
                "query": query,
                "output": output,
                "citation_details": citation_details
            }
            
    except Exception as e:
        error_msg = f"Knowledge Base API 오류: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        return {
            "response_type": "error",
            "query": query,
            "output": error_msg,
            "results": [] if retrieve_only else None
        }