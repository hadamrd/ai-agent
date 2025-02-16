import logging  
from logging.handlers import RotatingFileHandler  

def setup_logger(name):  
    logger = logging.getLogger(name)  
    logger.setLevel(logging.INFO)  
    
    handler = RotatingFileHandler(  
        "AINewsJohnStewart/logs/ai_news.log",  
        maxBytes=1e6,  # 1MB logs  
        backupCount=3  
    )  
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  
    handler.setFormatter(formatter)  
    logger.addHandler(handler)  
    
    return logger  