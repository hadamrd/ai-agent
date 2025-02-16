from datetime import datetime
import logging
import os
from autogen import AssistantAgent
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_random_exponential
from AINewsJohnStewart.agents.satirist.config.loader import ConfigLoader, Script
from AINewsJohnStewart.utils.logger import setup_logger
from AINewsJohnStewart.utils.settings import settings
import re
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = setup_logger(__name__)
CURRDIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRDIR, 'templates')
config = ConfigLoader.load_config()

class SatiristAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="AI_Comedian",
            llm_config=settings.SATIRIST_LLM_CONF,
            system_message=self._load_system_message()
        )
        self.style_guide = config.style_guide.model_dump()
        self.template_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(config.templates.autoescape),
            trim_blocks=config.templates.trim_blocks,
            lstrip_blocks=config.templates.lstrip_blocks
        )
        self.register_reply([AssistantAgent], SatiristAgent.generate_script_reply)

    def generate_script_reply(self, recipient, messages, sender, config):
        last_message = messages[-1].get("content", "")
        try:
            articles = json.loads(last_message).get("processed_articles", [])
            return self.write_script(articles)
        except json.JSONDecodeError:
            return super().generate_reply(recipient, messages, sender, config)
    
    def _load_system_message(self) -> str:
        """Load system message from template"""
        template = self.template_env.get_template('system_message.j2')
        return template.render(
            format_example=config.script_settings.format_example,
            style_rules=config.style_rules
        )

    def _build_prompt(self, articles: List[Dict]) -> str:
        """Generate prompt using template"""
        template = self.template_env.get_template('script_prompt.j2')
        return template.render(
            headlines=[a['title'] for a in articles[:5]],
            tech_fiasco=self._get_current_tech_fiasco(),
            style_guide=self.style_guide,
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
            if not self._validate_input(articles):
                raise ValueError("Invalid article input")
                
            prompt = self._build_prompt(articles)
            raw_response = self.generate_reply([{"content": prompt, "role": "user"}])
            
            return self._validate_output(raw_response)
            
        except Exception as e:
            logger.error(f"Script generation failed: {str(e)}")
            return self._fallback_script()

    def _validate_input(self, articles: List[Dict]) -> bool:
        """Validate input articles before processing"""
        try:
            if not articles or not isinstance(articles, list):
                logger.error("Invalid articles input: must be non-empty list")
                return False
                
            required_fields = {'title', 'content'}
            for article in articles:
                if not isinstance(article, dict):
                    logger.error(f"Invalid article format: {article}")
                    return False
                    
                missing_fields = required_fields - set(article.keys())
                if missing_fields:
                    logger.error(f"Missing required fields: {missing_fields}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Article validation failed: {str(e)}")
            return False
    
    def _validate_output(self, raw: str) -> Dict:
        try:
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            return Script(**data).model_dump()
        except Exception as e:  # Remove duplicate except block
            logger.warning(f"Output validation failed: {str(e)}")
            return self._fallback_script()

    def _fallback_script(self) -> Dict:
        """Generate sophisticated fallback script using template"""
        try:
            template = self.template_env.get_template('fallback_script.j2')
            error_context = {
                "error_message": self._get_last_error() or "General processing error",
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tech_context": self._get_current_tech_fiasco()
            }
            
            return template.render(
                script=config.script_settings.fallback.script,
                tone=config.script_settings.fallback.tone,
                metadata={
                    **config.script_settings.fallback.metadata.model_dump(),
                    "error_context": error_context
                }
            )
        except Exception as e:
            logger.error(f"Fallback script generation failed: {str(e)}")
            # Return basic fallback directly from config
            return {
                "script": config.script_settings.fallback.script,
                "tone": config.script_settings.fallback.tone
            }

    def _get_last_error(self) -> Optional[str]:
        """Get last error message from logger"""
        try:
            handler = next((h for h in logger.handlers if isinstance(h, logging.FileHandler)), None)
            if handler and os.path.exists(handler.baseFilename):
                with open(handler.baseFilename, 'r') as f:
                    lines = f.readlines()
                    errors = [l for l in reversed(lines) if 'ERROR' in l]
                    if errors:
                        return re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - ERROR - ', '', errors[0]).strip()
        except Exception:
            pass
        return None
    
    def _get_current_tech_fiasco(self) -> str:
        """Get current tech industry context for jokes"""
        try:
            # Could be expanded to fetch from news API or maintained list
            return config.script_settings.fallback.metadata.current_fiasco
        except Exception as e:
            logger.warning(f"Failed to get tech fiasco context: {str(e)}")
            return "the ongoing tech industry chaos"
