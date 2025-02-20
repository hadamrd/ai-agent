from autogen import AssistantAgent
import re
import json
from AINewsJohnStewart.agents.scout.article_cache import ArticleCache
from AINewsJohnStewart.agents.scout.news_client import NewsAPIClient
from AINewsJohnStewart.boot.settings import settings

from AINewsJohnStewart.utils.logger import setup_logger

logger = setup_logger(__name__)

class Digger(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="NewsScout",
            llm_config={
                "config_list": [{
                    "model": settings.ANTHROPIC_MODEL,
                    "api_key": settings.ANTHROPIC_API_KEY,
                    "api_base": "https://api.anthropic.com/v1/messages",
                    "api_type": "anthropic",
                }],
                "temperature": 0.3,  # More factual
                "timeout": 30,
            },
            system_message="""You are an AI Comedy Scout specializing in quick assessment of tech news comedy potential.
            
EXTREMELY SELECTIVE SCORING (1-10):
1-3: Regular tech news, no comedy value
4-6: Mildly interesting but not special
7-8: Strong comedy potential (needs multiple):
    - Clear tech industry ego/delusion
    - Obvious irony or hypocrisy
    - Rich personality-driven drama
9-10: Comedy gold (extremely rare, needs all):
    - Multiple layers of absurdity
    - Perfect setup for satire
    - Exceptional irony/controversy

BE HARSH IN SCORING. Most articles should score below 7.
Only truly exceptional stories deserve high scores.

Always return score in <brief_json> format."""
        )
        self.news_client = NewsAPIClient()
        self.cache = ArticleCache()

    def quick_score_articles(self, articles: list[dict], threshold: int = 7) -> list[dict]:
        """
        Quick initial scoring of articles based on title/description only.
        Returns scored articles above threshold.
        """
        scored_articles = []
        for article in articles:
            if isinstance(article, str):
                raise ValueError("Article must be a dictionary, got string instead : " + article)
                
            if not article.get('title') or not article.get('description'):
                continue
                
            url = article.get('url')
            if not url:
                continue

            # Check cache first
            cached = self.cache.get_cached_score(url)
            if cached:
                if cached['score'] >= threshold:
                    scored_articles.append({
                        'title': cached['title'],
                        'score': cached['score'],
                        'reason': cached['reason'],
                        'original_article': article
                    })
                continue

            # Score new articles
            score = self._get_quick_score(article)
            self.cache.cache_score(
                url=url,
                title=article['title'],
                score=score['score'],
                reason=score['reason']
            )

            if score['score'] >= threshold:
                scored_articles.append({
                    'title': article['title'],
                    'score': score['score'],
                    'reason': score['reason'],
                    'original_article': article
                })

        return sorted(scored_articles, key=lambda x: x['score'], reverse=True)

    def _get_quick_score(self, article: dict) -> dict:
        """Get quick comedy potential score for single article"""
        prompt = f"""
        Rate comedy potential (1-10) for this tech news.
        BE EXTREMELY SELECTIVE. Score of 7+ should be rare.
        
        Title: {article['title']}
        Description: {article['description']}
        
        Return score and reason in <brief_json> format:
        <brief_json>
        {{
            "score": number (1-10),
            "reason": "one line explanation why this score"
        }}
        </brief_json>
        """
        
        try:
            response = self.generate_reply([{"content": prompt, "role": "user"}])
            result = self._extract_json(response.get("content", ""))
            return result
        except Exception as e:
            logger.error(f"Error scoring article: {e}")
            return {"score": 0, "reason": "Error in scoring"}

    def _extract_json(self, content: str) -> dict:
        """Extract JSON from between brief_json tags"""
        pattern = r'<brief_json>(.*?)</brief_json>'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError("No brief_json tags found")
        return json.loads(match.group(1).strip())

    def dig_for_news(self, query: str = "artificial intelligence", page_size: int = 20, threshold: int = 6) -> list[dict]:
        """Main method to fetch and score news articles"""
        # Get articles from news client
        response = self.news_client.get_everything(
            query=query,
            page_size=page_size
        )
        
        articles = response.get('articles', [])
        if not articles:
            raise Exception("No articles found!")

        # Get quick scores and shortlist
        shortlisted = self.quick_score_articles(articles, threshold=threshold)

        # Clean up expired cache entries
        self.cache.cleanup_expired()
        
        return shortlisted