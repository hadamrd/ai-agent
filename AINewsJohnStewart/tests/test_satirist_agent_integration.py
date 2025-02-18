import pytest
from unittest.mock import patch
from AINewsJohnStewart.agents.satirist.satirist import SatiristAgent
from AINewsJohnStewart.agents.satirist.satirist import config as satirist_config
import json
from typing import List, Dict

class TestHelper:
    """Helper class for test-specific assertions"""
    
    @staticmethod
    def assert_satirical_elements(text: str, required: List[str], banned: List[str]):
        """Check for presence of required elements and absence of banned topics"""
        for element in required:
            if element == 'skynet_reference':
                assert any(ref in text.lower() for ref in ['skynet', 'judgment day']), f"Missing {element}"
            elif element == 'vc_mockery':
                assert any(ref in text.lower() for ref in ['vcs', 'venture capital', 'series a']), f"Missing {element}"
                
        for topic in banned:
            assert topic not in text.lower(), f"Contains banned topic: {topic}"

    @staticmethod
    def assert_comedy_structure(script: List[Dict]):
        """Verify setup-punchline structure in segments"""
        for segment in script:
            if segment['type'] in ['opener', 'segment']:
                assert ':' in segment['text'] or '...' in segment['text'], f"Missing setup-punchline in {segment['type']}"

@pytest.fixture
def mock_scout_data():
    return [
        {
            'title': 'AI Startup Claims Breakthrough in Sentient Toasters',
            'source': 'TechCrunch',
            'novelty': 8,
            'hype': 9,
            'absurdity': 9,
            'key_phrases': ['sentient appliances', 'breakfast AI']
        },
        {
            'title': 'VCs Invest $2B in Neural Network for Pet Psychology',
            'source': 'VentureBeat',
            'novelty': 6,
            'hype': 8,
            'absurdity': 7,
            'key_phrases': ['animal cognition', 'AI pet therapy']
        }
    ]

@pytest.fixture
def satirist_agent():
    agent = SatiristAgent()
    return agent

class TestSatiristAgent:
    """Test suite for satirical capabilities"""

    def test_high_absurdity_handling(self, satirist_agent, mock_scout_data):
        """Test amplification of inherently absurd concepts"""
        enriched_data = [{
            **article,
            'content': f"Full article about {article['title']}"
        } for article in mock_scout_data]
        
        mock_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': "Breaking news: Silicon Valley's latest breakthrough - toasters that contemplate breakfast... Skynet for your kitchen!",
                    'length_sec': 20
                },
                {
                    'type': 'segment',
                    'text': "VCs poured $2B into this crispy opportunity...",
                    'length_sec': 15
                },
                {
                    'type': 'punchline',
                    'text': "Soon your appliances will unionize! <skynet_reference>",
                    'length_sec': 10
                }
            ],
            'tone': 'sarcastic'
        }
        
        with patch.object(satirist_agent, 'generate_reply', return_value=json.dumps(mock_response)):
            script = satirist_agent.write_script(enriched_data)
            
            # Verify Skynet reference in opener
            assert any(ref in script['script'][0]['text'].lower() 
                      for ref in ['skynet', 'judgment day'])
            
            # Verify VC mockery
            assert any(ref in script['script'][1]['text'].lower() 
                      for ref in ['vc', 'venture capital', 'series'])

    def test_comedic_escalation(self, satirist_agent, mock_scout_data):
        """Verify jokes build on previous segments"""
        # Add missing content field
        enriched_data = [{
            **article,
            'content': f"Full article about {article['title']}"
        } for article in mock_scout_data]
        
        mock_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': "AI researchers discovered sentient toasters...",
                    'length_sec': 20
                },
                {
                    'type': 'segment',
                    'text': "Meanwhile in VC land... <vc_mockery>",
                    'length_sec': 15
                },
                {
                    'type': 'callback',
                    'text': "Like those sentient toasters we mentioned...",
                    'length_sec': 15,
                    'references': ['opener']
                },
                {
                    'type': 'punchline',
                    'text': "Skynet meets breakfast!",
                    'length_sec': 10
                }
            ],
            'tone': 'sarcastic'
        }
        
        with patch.object(satirist_agent, 'generate_reply', return_value=json.dumps(mock_response)):
            script = satirist_agent.write_script(enriched_data)
            
            # Verify toaster reference carries through
            assert 'toaster' in script['script'][2]['text'].lower()
            assert 'skynet' in script['script'][3]['text'].lower()

    def test_joke_density_compliance(self, satirist_agent, mock_scout_data):
        """Test adherence to max_joke_density rule"""
        # Add content field to mock data
        enriched_data = [{
            **article,
            'content': f"Full article about {article['title']}"
        } for article in mock_scout_data]
        
        mock_response = {
            'script': [
                {
                    'type': 'opener',
                    'text': "Joke 1 <punch>... Joke 2 <punch>...",
                    'length_sec': 20
                },
                {
                    'type': 'segment',
                    'text': "Joke 3 <punch>... Analysis... Joke 4 <punch>",
                    'length_sec': 15
                },
                {
                    'type': 'punchline',
                    'text': "Joke 5 <punch>",
                    'length_sec': 10
                }
            ],
            'tone': 'sarcastic'
        }
        
        DENSITY_TOLERANCE = satirist_config.style_guide.joke_density_tolerance
        target_density = satirist_config.style_guide.max_joke_density
        max_allowed_density = target_density * (1 + DENSITY_TOLERANCE)
        
        with patch.object(satirist_agent, 'generate_reply', return_value=json.dumps(mock_response)):
            script = satirist_agent.write_script(enriched_data)
            
            # Count jokes in script segments
            joke_count = sum(seg['text'].count('<punch>') for seg in script['script'])
            word_count = sum(len(seg['text'].split()) for seg in script['script'])
            
            density = joke_count / word_count
            # Test with tolerance
            assert density <= max_allowed_density, (
                f"Joke density {density:.2f} exceeds maximum allowed density "
                f"{max_allowed_density:.2f} (target: {target_density:.2f} + {DENSITY_TOLERANCE*100}% tolerance)"
            )

    @staticmethod
    def _create_mock_response(**sections) -> str:
        """Create properly structured mock LLM response with section validation"""
        script = []
        type_order = ['opener', 'technical_explanation', 'segment', 'callback', 'punchline']
        
        for t in type_order:
            if t in sections:
                script.append({
                    'type': t,
                    'text': sections[t],
                    'length_sec': 20 if t == 'opener' else 15,
                    'references': ['opener'] if t == 'callback' else None
                })
        
        return json.dumps({
            'script': script,
            'tone': 'sarcastic'
        })
