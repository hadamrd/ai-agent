import unittest
from unittest.mock import patch, MagicMock, call
import json
from requests.exceptions import RequestException
from AINewsJohnStewart.agents.scout.scout import ScoutAgent, NewsAPIRateLimiter
import logging


class TestScoutAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ScoutAgent()
        self.sample_article = {
            'title': 'AI Makes Breakthrough in Quantum Computing',
            'source': {'name': 'Tech News'},
            'url': 'https://example.com/article',
            'publishedAt': '2024-02-16T12:00:00Z',
            'content': 'Sample content here'
        }
        # Capture logged messages
        self.log_messages = []
        self.logger = logging.getLogger('AINewsJohnStewart.agents.scout')
        self.original_error = self.logger.error
        self.logger.error = self.log_messages.append

    def tearDown(self):
        # Restore original logger
        self.logger.error = self.original_error

    def test_validate_article(self):
        """Test article validation logic with edge cases"""
        # Valid article
        self.assertTrue(self.agent._validate_article(self.sample_article))
        
        # Test all edge cases
        edge_cases = [
            (
                {**self.sample_article, 'title': 'BTC'},
                False,
                "Should reject titles shorter than 20 characters"
            ),
            (
                {**self.sample_article, 'title': 'Bitcoin News'},
                False,
                "Should filter crypto-related content"
            ),
            (
                {**self.sample_article, 'content': None},
                False,
                "Should require content"
            ),
            (
                {**self.sample_article, 'url': 'not-a-url'},
                False,
                "Should validate URL format"
            ),
            (
                {**self.sample_article, 'title': None},
                False,
                "Should handle missing title"
            ),
            (
                {'url': 'http://example.com'},
                False,
                "Should handle missing required fields"
            )
        ]
        
        for case, expected, message in edge_cases:
            with self.subTest(msg=message):
                self.assertEqual(self.agent._validate_article(case), expected, message)

    def test_parse_llm_response(self):
        """Test LLM response parsing"""
        # Valid response
        valid_response = '''Here's the analysis: {"novelty": 8, "hype": 7, "absurdity": 4}'''
        result = self.agent._parse_llm_response(valid_response)
        self.assertEqual(result, {'novelty': 8, 'hype': 7, 'absurdity': 4})

        # Invalid cases
        invalid_cases = [
            ("Not JSON at all", "No valid JSON found"),
            ('{"novelty": 8, "hype": 7}', "Missing required fields"),
            ('{"novelty": 11, "hype": 5, "absurdity": 3}', "Score out of range"),
            ('{"novelty": "high", "hype": 7, "absurdity": 4}', "Invalid type")
        ]

        for input_str, expected_error in invalid_cases:
            with self.assertRaises(ValueError) as context:
                self.agent._parse_llm_response(input_str)
            self.assertIn(expected_error, str(context.exception))

    @patch('AINewsJohnStewart.agents.scout.ScoutAgent.analyze_article')
    def test_process_articles_error_handling(self, mock_analyze):
        """Test article processing with error conditions"""
        # Test successful case
        mock_analyze.return_value = {'novelty': 7, 'hype': 6, 'absurdity': 5}
        processed = self.agent._process_articles([self.sample_article])
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]['novelty'], 7)

        # Test analysis failure
        mock_analyze.side_effect = Exception("Analysis failed")
        processed = self.agent._process_articles([self.sample_article])
        self.assertEqual(len(processed), 1)
        self.assertIn('error', processed[0])
        self.assertEqual(processed[0]['error'], "Analysis failed")

        # Test empty article list
        processed = self.agent._process_articles([])
        self.assertEqual(processed, [])

        # Test limit enforcement
        many_articles = [self.sample_article] * 15
        processed = self.agent._process_articles(many_articles)
        self.assertLessEqual(len(processed), 10, "Should limit to 10 articles")

    @patch('AINewsJohnStewart.agents.scout.ScoutAgent.generate_reply')
    def test_analyze_article_caching(self, mock_generate):
        """Test article analysis caching behavior"""
        mock_generate.return_value = '{"novelty": 7, "hype": 6, "absurdity": 5}'
        
        # First call should hit the API
        result1 = self.agent.analyze_article("Test headline")
        self.assertEqual(mock_generate.call_count, 1)
        
        # Second call with same headline should use cache
        result2 = self.agent.analyze_article("Test headline")
        self.assertEqual(mock_generate.call_count, 1)
        self.assertEqual(result1, result2)
        
        # Different headline should hit API again
        self.agent.analyze_article("Different headline")
        self.assertEqual(mock_generate.call_count, 2)

if __name__ == '__main__':
    unittest.main()
