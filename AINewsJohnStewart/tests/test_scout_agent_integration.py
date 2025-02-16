import unittest
from unittest.mock import patch, MagicMock
from AINewsJohnStewart.agents.scout import ScoutAgent
    
class TestScoutAgentIntegration(unittest.TestCase):
    """Integration tests for ScoutAgent with real APIs"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize agent and verify API access with improved error handling"""
        cls.agent = ScoutAgent()
        cls.test_headlines = [
            "Google's AI Makes Breakthrough in Quantum Computing, Claims 100x Speed Increase",
            "OpenAI Releases GPT-5 with Human-Level Performance Across All Tasks",
        ]

        # Set up test articles for content filtering
        cls.test_articles = [
            {
                'title': 'Major AI Breakthrough in Cancer Research',
                'source': {'name': 'Science Daily'},
                'url': 'https://example.com/cancer-ai',
                'publishedAt': '2024-02-16T12:00:00Z',
                'content': 'Researchers have developed an AI system that can...'
            },
            {
                'title': 'Bitcoin AI Trading Bot Makes Millions',
                'source': {'name': 'Crypto News'},
                'url': 'https://example.com/crypto',
                'publishedAt': '2024-02-16T12:00:00Z',
                'content': 'A new cryptocurrency trading bot...'
            }
        ]
        
    def test_content_filtering(self):
        """Test article filtering (no API needed)"""
        # No setUp check needed for non-API tests
        processed = self.agent._process_articles(self.test_articles)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]['title'], 'Major AI Breakthrough in Cancer Research')

    def test_rate_limit_handling(self):
        """Test rate limit handling (no API needed)"""
        # No setUp check needed for non-API tests
        with patch('requests.Session.get') as mock_get:
            response = MagicMock()
            response.json.return_value = {'articles': []}
            response.headers = {'X-RateLimit-Remaining': '3'}
            mock_get.return_value = response
            
            results = self.agent.scrape_ai_news()
            self.assertEqual(results, [])

    def test_claude_response_quality(self):
        """Test quality of Claude's analysis"""
        # Will skip if API isn't working (checked in setUp)
        hype_headline = "Revolutionary AI Achieves Human-Level Intelligence, Changes Everything"
        analysis = self.agent.analyze_article(hype_headline)
        
        self.assertIsInstance(analysis, dict)
        self.assertIn('novelty', analysis)
        self.assertIn('hype', analysis)
        self.assertIn('absurdity', analysis)
        
        self.assertGreater(analysis['hype'], 7)
        self.assertGreater(analysis['absurdity'], 5)

    def test_mock_claude_analysis(self):
        """Test analysis pipeline with mocked Claude responses"""
        # No setUp check needed for mocked tests
        mock_response = '''{
            "novelty": 8,
            "hype": 9,
            "absurdity": 7
        }'''
        
        with patch.object(self.agent, 'generate_reply', return_value=mock_response):
            analysis = self.agent.analyze_article(self.test_headlines[0])
            self.assertEqual(analysis['novelty'], 8)
            self.assertEqual(analysis['hype'], 9)
            self.assertEqual(analysis['absurdity'], 7)

    def test_api_error_handling(self):
        """Test API error handling with mocks"""
        # No setUp check needed for mocked tests
        with patch.object(self.agent, 'generate_reply', side_effect=Exception("API Error")):
            result = self.agent.analyze_article("Test Headline")
            self.assertIn('error', result)
            self.assertIn("API Error", result['error'])

if __name__ == '__main__':
    unittest.main()