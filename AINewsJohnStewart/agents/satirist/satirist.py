from datetime import datetime
import logging
import os
import re
from autogen import AssistantAgent
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_random_exponential
from AINewsJohnStewart.agents.satirist.config.loader import ConfigLoader, Script
from AINewsJohnStewart.utils.logger import setup_logger
from AINewsJohnStewart.boot.settings import settings
import json
from AINewsJohnStewart.boot.jinja import create_env

logger = setup_logger(__name__)
CURRDIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRDIR, 'templates')
config = ConfigLoader.load_config()
template_env = create_env(
    templates_dir=TEMPLATES_DIR,
    autoescape=config.templates.autoescape,
    trim_blocks=config.templates.trim_blocks,
    lstrip_blocks=config.templates.lstrip_blocks
)

class SatiristAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="AI_Comedian",
            llm_config=settings.SATIRIST_LLM_CONF,
            system_message=self._load_system_message()
        )
        self.register_reply([AssistantAgent], SatiristAgent.generate_script_reply)

    def generate_script_reply(self, recipient, messages, sender, config):
        last_message = messages[-1].get("content", "")
        try:
            articles = json.loads(last_message).get("processed_articles", [])
            return self.write_script(articles)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message content: {str(e)}")
            return super().generate_reply(recipient, messages, sender, config)
    
    def _load_system_message(self) -> str:
        """Load system message from template"""
        return template_env.get_template('system_message.j2').render(
            config=config.model_dump()
        )

    def _build_prompt(self, articles: List[Dict]) -> str:
        """Generate prompt using template"""
        template = template_env.get_template('script_prompt.j2')
        return template.render(
            headlines=[a['title'] for a in articles[:5]],
            style_guide=config.style_guide.model_dump(),
            max_length=2
        )

    @retry(
        stop=stop_after_attempt(config.script_settings.validation.retry_attempts),
        wait=wait_random_exponential(
            multiplier=config.script_settings.validation.retry_multiplier,
            max=config.script_settings.validation.retry_max_wait
        )
    )
    def write_script(self, articles: List[Dict]) -> Dict:
        """Generate satirical script with guardrails"""
        try:
            self._validate_input(articles)
            prompt = self._build_prompt(articles)
            raw_response = self.generate_reply([{"content": prompt, "role": "user"}])
            logger.info(f"Script generated successfully: {raw_response}")
            validated_response = self._validate_output(raw_response)
            return validated_response
        except Exception as e:
            logger.error(f"Script generation failed: {str(e)}")
            return self._fallback_script(str(e))

    def _validate_input(self, articles: List[Dict]) -> None:
        """Validate input articles before processing"""
        if not articles or not isinstance(articles, list):
            raise ValueError("Invalid articles input: must be non-empty list")
            
        required_fields = {'title', 'content'}
        for article in articles:
            if not isinstance(article, dict):
                raise ValueError(f"Invalid article format: {article}")
                
            missing_fields = required_fields - set(article.keys())
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
    
    def _validate_output(self, response: Dict) -> Dict:
        """Validate and parse the script output using XML-style tags."""
        try:
            # Extract content from the response
            content = response.get('content', '')
            if not isinstance(content, str):
                raise ValueError(f"Expected string content, got {type(content)}")
                
            # Extract content between script_json tags
            pattern = r'<script_json>(.*?)</script_json>'
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                raise ValueError("No <script_json> tags found in response")
                
            # Get the JSON content from between the tags
            json_content = match.group(1).strip()
            
            # Parse the JSON
            data = json.loads(json_content)
            
            # Validate required fields
            required_fields = {'script', 'tone', 'metadata'}
            if not all(field in data for field in required_fields):
                missing = required_fields - set(data.keys())
                raise ValueError(f"Missing required fields: {missing}")
                
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in script: {str(e)}")
        except Exception as e:
            raise ValueError(f"Validation error: {str(e)}")
    
    def _fallback_script(self, error_message: str) -> Dict:
        """Generate fallback script using config"""
        try:
            # Get base metadata from config
            base_metadata = config.script_settings.fallback.metadata.model_dump()
            
            # Add runtime metadata
            metadata = {
                **base_metadata,
                "error_message": error_message,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_fallback": True  # Add is_fallback flag
            }
            
            script_data = {
                "script": config.script_settings.fallback.script,
                "tone": config.script_settings.fallback.tone,
                "metadata": metadata
            }
            
            # Use Script model for validation
            validated_script = Script(**script_data)
            return validated_script.model_dump()
                    
        except Exception as e:
            logger.error(f"Critical error in fallback script generation: {str(e)}")
            raise RuntimeError("Failed to generate fallback script") from e