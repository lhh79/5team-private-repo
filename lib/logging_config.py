# Path: /bedrock_chatbot_app/lib/logging_config.py

"""애플리케이션 전체에서 일관된 로깅 시스템을 제공하는 모듈"""
import logging
import sys
import os

def setup_logging(level=logging.INFO):
    """
    애플리케이션 전체에서 사용할 로깅 시스템을 설정합니다.
    색상으로 구분된 로그 메시지를 출력합니다.
    
    Args:
        level: 로깅 레벨 (기본값: logging.INFO)
        
    Returns:
        logging.Logger: 설정된 로거 객체
    """
    logger = logging.getLogger('bedrock_app')
    logger.setLevel(level)
    
    # 이미 핸들러가 설정되어 있으면 추가하지 않음
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # 색상 지원 확인 (Windows CMD에서는 컬러 지원이 제한적)
        use_colors = hasattr(sys, 'ps1') or os.name != 'nt' or 'ANSICON' in os.environ
        
        if use_colors:
            # 색상 코드
            RESET = "\033[0m"
            BOLD = "\033[1m"
            BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = ["\033[1;%dm" % (30 + i) for i in range(8)]
            
            fmt = "%(asctime)s - %(name)s - {color}%(levelname)s{reset}: %(message)s".format(
                color="%(color)s", reset=RESET
            )
            
            class ColoredFormatter(logging.Formatter):
                COLORS = {
                    'DEBUG': CYAN,
                    'INFO': GREEN,
                    'WARNING': YELLOW,
                    'ERROR': RED,
                    'CRITICAL': BOLD + RED,
                }
                
                def format(self, record):
                    record.color = self.COLORS.get(record.levelname, WHITE)
                    return super(ColoredFormatter, self).format(record)
                    
            formatter = ColoredFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        else:
            # 색상 없는 기본 포맷터
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s', 
                                         datefmt="%Y-%m-%d %H:%M:%S")
                                         
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# 기본 로거 생성
logger = setup_logging()
