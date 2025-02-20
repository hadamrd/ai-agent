import json
import os
from autogen import AssistantAgent
import requests
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_random_exponential
from AINewsJohnStewart.agents.scout.config.loader import ConfigLoader
from AINewsJohnStewart.agents.scout.models import ArticleBrief
from AINewsJohnStewart.agents.scout.news_client import NewsAPIClient
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
        self.news_client = NewsAPIClient()

    def _load_system_message(self) -> str:
        """Load system message from template"""
        return template_env.get_template('system_message.j2').render(
            config=config.model_dump()
        )

    def _process_articles(self, raw_articles: List[Dict]) -> List[ArticleBrief]:
        """Sanitize and enrich articles with full content before analysis"""
        processed = []
        for article in raw_articles[:10]:  # Limit to 10 for cost control
            try:
                # First get the full content
                url = article.get('url')
                if not url:
                    logger.warning(f"Skipping article with no URL: {article.get('title')}")
                    continue

                content = self.news_client._fetch_article_content(url)
                if not content:
                    logger.warning(f"Could not fetch content for: {url}")
                    continue

                # Add full content to article
                article['content'] = content

                # Now analyze with full content
                brief = self.analyze_article(article)
                processed.append(brief)
                
            except Exception as e:
                logger.error(f"Analysis failed for {article.get('title')}: {str(e)}")
                
        return processed

    def _build_analysis_prompt(self, article: Dict) -> str:
        """Generate prompt using template with full content"""
        template = template_env.get_template('analysis_prompt.j2')
        return template.render(
            article=article.get('title', ''),
            content=article.get('content', ''),  # This will now be the full content
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