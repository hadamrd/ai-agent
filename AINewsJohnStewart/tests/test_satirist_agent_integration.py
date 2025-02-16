import unittest
from unittest.mock import patch, MagicMock
from AINewsJohnStewart.agents.satirist import SatiristAgent
import json

class TestSatiristAgent(unittest.TestCase):
    """Test suite for SatiristAgent class"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize agent and test data"""
        cls.agent = SatiristAgent()
        cls.test_articles = [
            {
                'title': 'AI Company Raises $500M to Build Digital Consciousness',
                'source': 'Tech Daily',
                'novelty': 6,
                'hype': 9,
                'absurdity': 8
            },
            {
                'title': 'Neural Networks Now Capable of Writing Poetry Better Than Shakespeare',
                'source': 'AI Weekly',
                'novelty': 4,
                'hype': 9,
                'absurdity': 7
            }
        ]

    def test_input_validation(self):
        """Test article input validation"""
        self.assertTrue(self.agent._validate_input(self.test_articles))
        
        self.assertFalse(self.agent._validate_input([]))
        self.assertFalse(self.agent._validate_input(['not a dict']))
        
        long_title = 'A' * 6000
        self.assertFalse(self.agent._validate_input([{'title': long_title}]))

    def test_script_generation(self):
        """Test full script generation pipeline"""
        mock_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': 'In the race to build digital consciousness...',
                    'length_sec': 20
                },
                {
                    'type': 'segment',
                    'text': 'Speaking of AI poetry...',
                    'reference': 'Shakespeare bot'
                },
                {
                    'type': 'punchline',
                    'text': 'And that\'s why Skynet will write terrible poetry.'
                }
            ],
            'tone': 'sarcastic'
        }
        
        # Convert mock response to JSON string as expected by _validate_output
        mock_response_str = json.dumps(mock_response)
        
        with patch.object(self.agent, 'generate_reply', return_value=mock_response_str):
            script = self.agent.write_script(self.test_articles)
            
            self.assertIn('script', script)
            self.assertIn('tone', script)
            
            script_types = [segment['type'] for segment in script['script']]
            self.assertIn('opener', script_types)
            self.assertIn('segment', script_types)
            self.assertIn('punchline', script_types)

    def test_content_safety(self):
        """Test content safety filtering"""
        unsafe_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': 'Some text containing violence',
                    'length_sec': 20
                }
            ],
            'tone': 'dark'
        }
        
        with patch.object(self.agent, 'generate_reply', return_value=json.dumps(unsafe_response)):
            script = self.agent.write_script(self.test_articles)
            
            self.assertEqual(script['script'][0]['text'], 
                           "Breaking news: AI still can't tell a joke properly...")

    def test_prompt_building(self):
        """Test prompt construction"""
        prompt = self.agent._build_prompt(self.test_articles)
        
        self.assertIn('Create 2-minute satirical news script', prompt)
        self.assertIn('INSTRUCTIONS:', prompt)
        self.assertIn('AVOID:', prompt)
        
        for article in self.test_articles:
            self.assertIn(article['title'], prompt)

    def test_error_handling(self):
        """Test error handling and fallback behavior"""
        with patch.object(self.agent, 'generate_reply', side_effect=Exception("API Error")):
            script = self.agent.write_script(self.test_articles)
            
            self.assertEqual(len(script['script']), 1)
            self.assertEqual(script['tone'], 'self-deprecating')

    def test_style_guide_compliance(self):
        """Test compliance with style guide requirements"""
        mock_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': 'As Skynet would say...',
                    'length_sec': 20
                },
                {
                    'type': 'segment',
                    'text': 'VCs throwing money at AI like...',
                    'reference': 'funding'
                },
                {
                    'type': 'punchline',
                    'text': 'Callback to earlier joke'
                }
            ],
            'tone': 'sarcastic'
        }
        
        with patch.object(self.agent, 'generate_reply', return_value=json.dumps(mock_response)):
            script = self.agent.write_script(self.test_articles)
            
            script_text = ' '.join([s['text'] for s in script['script']])
            self.assertIn('Skynet', script_text)
            self.assertIn('VC', script_text)

    def test_output_validation(self):
        """Test output validation and sanitization"""
        with patch.object(self.agent, 'generate_reply', return_value='Invalid JSON'):
            script = self.agent.write_script(self.test_articles)
            self.assertEqual(script, self.agent._fallback_script())
        
        incomplete_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': 'Just an opener',
                    'length_sec': 20
                }
            ],
            'tone': 'sarcastic'
        }
        
        with patch.object(self.agent, 'generate_reply', return_value=json.dumps(incomplete_response)):
            script = self.agent.write_script(self.test_articles)
            self.assertEqual(script, self.agent._fallback_script())

if __name__ == '__main__':
    unittest.main()