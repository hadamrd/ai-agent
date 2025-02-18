import json
from autogen import AssistantAgent
import requests
from typing import List, Dict, Union
from tenacity import retry, stop_after_attempt, wait_exponential
from AINewsJohnStewart.utils.logger import setup_logger
from AINewsJohnStewart.boot.settings import settings
from functools import lru_cache
import re

logger = setup_logger(__name__)

class NewsAPIRateLimiter:
    """Enforce rate limits for NewsAPI (100 reqs/24h free tier)"""
    def __init__(self):
        self.call_count = 0
        
    def __call__(self, response: requests.Response):
        self.call_count += 1
        remaining = int(response.headers.get('X-RateLimit-Remaining', 100))
        if remaining < 5:
            logger.warning(f"NewsAPI rate limit approaching: {remaining} left")

class ScoutAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="NewsScout",
            llm_config=settings.SCOUT_CONFIG,
            system_message="""You are a senior AI news analyst. When analyzing headlines, return a JSON object with these scores:
- novelty (1-10): How innovative or groundbreaking the development is
- hype (1-10): Level of media excitement vs actual substance
- absurdity (1-10): How outlandish or unrealistic the claims are

Example response:
{
    "novelty": 7,
    "hype": 8,
    "absurdity": 4
}"""
        )
        self.rate_limiter = NewsAPIRateLimiter()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AINewsBot/1.0'})

    @retry(stop=stop_after_attempt(3), 
           wait=wait_exponential(multiplier=1, min=4, max=10))
    def scrape_ai_news(self) -> List[Dict]:
        """Production-grade scraping with retries and rate limiting"""
        try:
            response = self.session.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": "artificial intelligence",
                    "sortBy": "popularity",
                    "pageSize": 20,
                    "apiKey": settings.NEWSAPI_KEY,
                    "language": "en",
                    "excludeDomains": "clickbait.com,lowquality.ai"
                },
                hooks={'response': self.rate_limiter}
            )
            response.raise_for_status()
            
            data = response.json()
            if 'articles' not in data:
                logger.error("Invalid API response format")
                return []
                
            return self._process_articles(data['articles'])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Scraping failed: {str(e)}")
            return []
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Invalid API response: {str(e)}")
            return []

    def _process_articles(self, raw_articles: List[Dict]) -> List[Dict]:
        """Sanitize and enrich articles"""
        processed = []
        for article in raw_articles[:10]:  # Limit to 10 for cost control
            if not self._validate_article(article):
                continue
                
            try:
                analysis = self.analyze_article(article['title'])
                processed.append({
                    'title': article['title'],
                    'source': article['source']['name'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    **analysis
                })
            except Exception as e:
                # If analysis fails, include error info but keep other article data
                processed.append({
                    'title': article['title'],
                    'source': article['source']['name'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    'error': str(e)
                })
                
        return processed

    @lru_cache(maxsize=1000)
    def analyze_article(self, headline: str) -> Dict:
        """Use Autogen's built-in LLM handling for analysis"""
        try:
            logger.info(f"Analyzing headline: {headline}")
            
            messages = [{
                "role": "user", 
                "content": f"Analyze this AI news headline:\n{headline}"
            }]
            logger.info(f"Sending messages to Claude: {messages}")
            
            response = self.generate_reply(messages, sender=None)
            logger.info(f"Raw response from generate_reply: {response}")
            logger.info(f"Response type: {type(response)}")
            
            if not response:
                logger.error("Received empty response from generate_reply")
                return {'error': 'Empty response from API'}
                
            result = self._parse_llm_response(response)
            logger.info(f"Parsed result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def _validate_article(self, article: Dict) -> bool:
        """Filter out junk"""
        try:
            title = article.get('title', '')
            if not isinstance(title, str):
                return False
                
            return (
                len(title) > 20 and  # Avoid short titles
                not re.search(r'\b(bitcoin|nft|crypto)\b', title.lower()) and  # Skip crypto
                bool(article.get('content')) and  # Must have content
                article.get('url', '').startswith('http')  # Valid URL
            )
        except (TypeError, AttributeError):
            return False

    def _parse_llm_response(self, response: Union[str, Dict]) -> Dict:
        """Validate and parse LLM output"""
        logger.info(f"Parsing response: {response}")
        
        if not response:
            raise ValueError("Empty LLM response")

        try:
            # Extract the JSON string from the response
            json_str = response
            if isinstance(response, dict):
                # If it's a dict with content, use that
                if 'content' in response:
                    json_str = response['content']
                # If it's already the right format, use it directly
                elif all(key in response for key in ['novelty', 'hype', 'absurdity']):
                    json_str = json.dumps(response)
            
            # Now json_str should be a string containing JSON
            if isinstance(json_str, str):
                # Find JSON in the string
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if not json_match:
                    raise ValueError("No valid JSON found in response")
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Unexpected response format: {type(json_str)}")
                
            logger.info(f"Extracted data: {data}")
            
            # Validate required fields
            required_fields = {'novelty', 'hype', 'absurdity'}
            missing_fields = required_fields - set(data.keys())
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Validate scores
            for key in required_fields:
                if not isinstance(data[key], (int, float)):
                    raise ValueError(f"Invalid type for {key} score: {type(data[key])}")
                if not 1 <= data[key] <= 10:
                    raise ValueError(f"Score out of range (1-10) for {key}: {data[key]}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ValueError(f"Invalid JSON format in response: {str(e)}")
        except Exception as e:
            logger.error(f"Parse error: {str(e)}")
            raise ValueError(f"Error parsing response: {str(e)}")