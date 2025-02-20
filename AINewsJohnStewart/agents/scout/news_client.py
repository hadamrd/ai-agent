from typing import Dict, List, Optional
from urllib.parse import urlparse
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
import trafilatura
from AINewsJohnStewart.utils.logger import setup_logger
from AINewsJohnStewart.boot.settings import settings
from bs4 import BeautifulSoup

logger = setup_logger(__name__)

class NewsAPIClient:
    """Low-level client for interacting with NewsAPI"""
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.NEWSAPI_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'AINewsBot/1.0'
        })
        self._setup_rate_limiter()

    def _setup_rate_limiter(self):
        """Initialize rate limiter for the session"""
        self._rate_limiter = NewsAPIRateLimiter()
        self.session.hooks['response'].append(self._rate_limiter)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_everything(
        self,
        query: str,
        *,
        page_size: int = 20,
        language: str = "en",
        sort_by: str = "popularity",
        exclude_domains: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict:
        """
        Search all articles matching criteria
        
        Args:
            query: Search query
            page_size: Number of results per page (max 100)
            language: Article language (e.g. 'en', 'es')
            sort_by: Sort order ('relevancy', 'popularity', 'publishedAt')
            exclude_domains: List of domains to exclude
            from_date: Start date in ISO format (e.g. '2024-02-18')
            to_date: End date in ISO format
            
        Returns:
            Dict containing articles and metadata
        """
        params = {
            'q': query,
            'pageSize': min(page_size, 100),
            'language': language,
            'sortBy': sort_by
        }
        
        if exclude_domains:
            params['excludeDomains'] = ','.join(exclude_domains)
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date

        return self._make_request('everything', params)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_top_headlines(
        self,
        *,
        country: Optional[str] = None,
        category: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 20
    ) -> Dict:
        """
        Fetch top headlines with optional filters
        
        Args:
            country: 2-letter ISO country code
            category: News category ('business', 'technology', etc)
            query: Keywords to search for
            page_size: Number of results per page (max 100)
            
        Returns:
            Dict containing articles and metadata
        """
        params = {'pageSize': min(page_size, 100)}
        
        if country:
            params['country'] = country
        if category:
            params['category'] = category
        if query:
            params['q'] = query

        return self._make_request('top-headlines', params)

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make authenticated request to NewsAPI"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'ok':
                error = data.get('message', 'Unknown error')
                raise NewsAPIError(f"API returned error: {error}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise NewsAPIError(f"Request failed: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            raise NewsAPIError(f"Invalid response format: {str(e)}")

    def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract article content from URL
        Uses trafilatura for better content extraction
        Falls back to BeautifulSoup if needed
        """
        try:
            # Try to get the page content
            response = self.session.get(
                url,
                timeout=10,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            response.raise_for_status()
            
            # First try trafilatura
            content = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False
            )
            
            # If trafilatura fails, try BeautifulSoup
            if not content:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    tag.decompose()
                
                # Try to find main content
                article = soup.find('article') or soup.find(class_=lambda x: x and ('article' in x.lower() or 'content' in x.lower()))
                if article:
                    content = article.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)
            else:
                print("Trafilatura worked!")
            
            return content.strip() if content else None
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
        
class NewsAPIError(Exception):
    """Custom exception for NewsAPI errors"""
    pass

class NewsAPIRateLimiter:
    """Track and enforce NewsAPI rate limits"""
    
    def __init__(self):
        self.call_count = 0
        
    def __call__(self, response: requests.Response, *args, **kwargs):
        """Called after each request to check rate limits"""
        self.call_count += 1
        
        # Check remaining requests
        remaining = int(response.headers.get('X-RateLimit-Remaining', 100))
        if remaining < 5:
            logger.warning(f"NewsAPI rate limit approaching: {remaining} requests remaining")
            
        # Check if we hit the limit
        if remaining == 0:
            reset_time = response.headers.get('X-RateLimit-Reset')
            logger.error(f"NewsAPI rate limit exceeded. Resets at: {reset_time}")
            raise NewsAPIError("Rate limit exceeded")

SKIP_DOMAINS = [
    # Major Paywalls
    'wsj.com',
    'ft.com',
    'nytimes.com',
    'bloomberg.com',
    'reuters.com',
    'economist.com',
    'forbes.com',
    'barrons.com',
    'businessinsider.com',
    'seekingalpha.com',
    'hbr.org',  # Harvard Business Review
    
    # Yahoo Family (Consent Issues)
    'yahoo.com',
    'finance.yahoo.com',
    'news.yahoo.com',
    
    # Strong Anti-Bot Measures
    'medium.com',
    'towardsdatascience.com',  # Medium publication
    'venturebeat.com',
    'techcrunch.com',
    'wired.com',
    'cnet.com',
    'zdnet.com',
    
    # Cookie/GDPR Walls
    'theverge.com',
    'engadget.com',
    'gizmodo.com',
    'mashable.com',
    'telegraph.co.uk',
    'independent.co.uk',
    'thetimes.co.uk',
    
    # Complex JavaScript Requirements
    'insider.com',
    'marketwatch.com',
    'cnbc.com',
    'theregister.com',
    'arstechnica.com',
    
    # Regional Paywalls
    'latimes.com',
    'washingtonpost.com',
    'sfchronicle.com',
    'chicagotribune.com',
    'scmp.com'  # South China Morning Post
]
    
if __name__ == "__main__":
    client = NewsAPIClient()
    
    # First get the articles
    articles = client.get_everything(
        query="artificial intelligence",
        page_size=10,  # Get more since we'll skip some
        sort_by="popularity",
        exclude_domains=SKIP_DOMAINS
    )
    
    print("\nFound articles:")
    for idx, article in enumerate(articles.get('articles', []), 1):
        url = article.get('url', 'No URL')
        domain = urlparse(url).netloc if url != 'No URL' else 'No domain'
        print(f"{idx}. {article['title']}")
        print(f"   Source: {domain}")
        print(f"   URL: {url}")
        print()
    
    # Try articles until we successfully fetch content
    for article in articles.get('articles', []):
        url = article.get('url')
        if not url:
            continue
            
        domain = urlparse(url).netloc
        if domain in SKIP_DOMAINS:
            print(f"Skipping {domain} (known paywall/restrictions)")
            continue
            
        print(f"\nAttempting to fetch: {article['title']}")
        content = client._fetch_article_content(url)
        if content:
            print("\nSuccessfully fetched content:")
            print("=" * 50)
            print(content[:2000] + "..." if len(content) > 500 else content)
            break
        else:
            print(f"Failed to fetch content from {domain}, trying next article...")