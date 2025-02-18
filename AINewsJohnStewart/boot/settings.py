from functools import lru_cache
from pydantic import PositiveInt, field_validator
from typing import Optional, Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Main configuration with validation and env fallbacks"""
    
    # API Keys
    ANTHROPIC_API_KEY: str 
    NEWSAPI_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    
    # Model Configurations
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Budget Controls
    MAX_TOKENS_PER_RUN: PositiveInt = 50_000
    ENABLE_COST_LIMITS: bool = True
    
    # Predefined Model Configurations
    @property
    def SCOUT_CONFIG(self) -> Dict:
        """Configuration for news analysis agent"""
        return {
            "config_list": [{
                "model": self.ANTHROPIC_MODEL,
                "api_key": self.ANTHROPIC_API_KEY,
                "api_base": "https://api.anthropic.com/v1/messages",
                "api_type": "anthropic",
            }],
            "temperature": 0.3,  # More factual
            "timeout": 30,
        }
    
    @property
    def SATIRIST_LLM_CONF(self) -> Dict:
        """Configuration for comedy writing agent"""
        return {
            "config_list": [{
                "model": self.ANTHROPIC_MODEL,
                "api_key": self.ANTHROPIC_API_KEY,
                "max_tokens": 1500,
                "temperature": 0.7,  # More creative
            }],
            "timeout": 45,
            "cache_seed": 42,  # Reproducible humor
        }
    
    @property
    def DEFAULT_HEADERS(self) -> Dict:
        """Standard headers for API requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "AINewsBot/1.0",
            "X-Api-Key": self.ANTHROPIC_API_KEY,
        }
    
    @field_validator('ANTHROPIC_API_KEY')
    def validate_anthropic_key(cls, v: str) -> str:
        """Ensure Anthropic API key has correct format"""
        if not v.startswith('sk-ant-'):
            raise ValueError("Invalid Anthropic API key format")
        return v.strip()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='allow'
    )

    @classmethod
    @lru_cache()
    def get_settings(cls) -> "Settings":
        """Load config with error handling"""
        return cls()

# Singleton config instance
settings = Settings.get_settings()