import json
import os
from autogen import AssistantAgent
import requests
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_random_exponential
from AINewsJohnStewart.agents.scout.config.loader import ConfigLoader
from AINewsJohnStewart.agents.scout.models import ArticleBrief
from AINewsJohnStewart.boot.jinja import create_env
from AINewsJohnStewart.utils.logger import setup_logger
from AINewsJohnStewart.boot.settings import settings
import re

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

class Debriefer(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="NewsScout",
            llm_config=settings.SCOUT_CONFIG,
            system_message=self._load_system_message()
        )
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AINewsBot/1.0'})

    def _load_system_message(self) -> str:
        """Load system message from template"""
        return template_env.get_template('system_message.j2').render(
            config=config.model_dump()
        )

    def _process_articles(self, raw_articles: List[Dict]) -> List[ArticleBrief]:
        """Sanitize and enrich articles"""
        processed = []
        for article in raw_articles[:10]:  # Limit to 10 for cost control
            try:
                biref = self.analyze_article(article['title'])
                processed.append(biref)
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                
        return processed

    def _build_analysis_prompt(self, article: Dict) -> str:
        """Generate prompt using template"""
        template = template_env.get_template('analysis_prompt.j2')
        return template.render(
            article=article.get('title', ''),
            content=article.get('content', ''),
        )

    @retry(
        stop=stop_after_attempt(config.script_settings.validation.retry_attempts),
        wait=wait_random_exponential(
            multiplier=config.script_settings.validation.retry_multiplier,
            max=config.script_settings.validation.retry_max_wait
        )
    )
    def analyze_article(self, article: Dict) -> ArticleBrief:
        """Analyze a single article for comedy potential"""
        prompt = self._build_analysis_prompt(article)
        response = self.generate_reply([{"content": prompt, "role": "user"}])
        
        # Parse the tagged response into ArticleBrief
        brief_json = self._extract_tagged_json(response.get("content", ""))
        return ArticleBrief(**brief_json)

    def _extract_tagged_json(self, content: str) -> Dict:
        """Extract JSON from between brief_json tags"""
        pattern = r'<brief_json>(.*?)</brief_json>'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError("No brief_json tags found in response")
        return json.loads(match.group(1).strip())
