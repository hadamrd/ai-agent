import pytest
from unittest.mock import patch, MagicMock
from AINewsJohnStewart.agents.satirist.satirist import SatiristAgent
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
        mock_response = self._create_mock_response(
            opener="Breaking news: Silicon Valley's latest breakthrough - toasters that contemplate breakfast...",
            segment="VCs poured $2B into this crispy opportunity...",
            punchline="Soon your appliances will unionize! <skynet_reference>"
        )
        
        with patch.object(satirist_agent, 'generate_reply', return_value=mock_response):
            script = satirist_agent.write_script(mock_scout_data)
            
            TestHelper.assert_satirical_elements(
                script['script'][0]['text'],
                satirist_agent.style_guide['required_elements'],
                satirist_agent.style_guide['banned_topics']
            )
            assert 'unionize' in script['script'][-1]['text']

    def test_comedic_escalation(self, satirist_agent, mock_scout_data):
        """Verify jokes build on previous segments"""
        mock_response = self._create_mock_response(
            opener="AI researchers discovered...",
            segment="Meanwhile in VC land... <vc_mockery>",
            callback="Like those sentient toasters we mentioned...",
            punchline="Skynet meets breakfast!"
        )
        
        with patch.object(satirist_agent, 'generate_reply', return_value=mock_response):
            script = satirist_agent.write_script(mock_scout_data)
            assert 'toasters' in script['script'][2]['text']
            assert 'Skynet' in script['script'][-1]['text']

    def test_joke_density_compliance(self, satirist_agent, mock_scout_data):
        """Test adherence to max_joke_density rule"""
        mock_response = self._create_mock_response(
            opener="Joke 1 <punch>... Joke 2 <punch>...",
            segment="Joke 3 <punch>... Analysis... Joke 4 <punch>",
            punchline="Joke 5 <punch>"
        )
        
        with patch.object(satirist_agent, 'generate_reply', return_value=mock_response):
            script = satirist_agent.write_script(mock_scout_data)
            joke_count = sum(seg['text'].count('<punch>') for seg in script['script'])
            word_count = sum(len(seg['text'].split()) for seg in script['script'])
            
            density = joke_count / word_count
            assert density <= satirist_agent.style_guide['max_joke_density']

    @staticmethod
    def _create_mock_response(**sections) -> str:
        """Create properly structured mock LLM response"""
        script = []
        type_order = ['opener', 'technical_explanation', 'segment', 'callback', 'punchline']
        
        for t in type_order:
            if t in sections:
                script.append({
                    'type': t,
                    'text': sections[t],
                    'length_sec': 20 if t == 'opener' else 15
                })
                
        return json.dumps({
            'script': script,
            'tone': 'sarcastic'
        })
