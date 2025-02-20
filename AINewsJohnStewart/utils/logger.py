import logging  
from logging.handlers import RotatingFileHandler

from AINewsJohnStewart.boot.settings import settings

def setup_logger(name):  
    logger = logging.getLogger(name)  
    logger.setLevel(logging.INFO)  
    log_file = settings.AI_AGENTS_LOGS_DIR / "ai_news.log"
    
    handler = RotatingFileHandler(  
        log_file,  
        maxBytes=1e6,  # 1MB logs  
        backupCount=3  
    )  
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  
    handler.setFormatter(formatter)  
    logger.addHandler(handler)  
    
    return logger  