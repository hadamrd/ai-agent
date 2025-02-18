import pytest
from unittest.mock import patch, Mock
from AINewsJohnStewart.agents.satirist.satirist import SatiristAgent
from AINewsJohnStewart.agents.satirist.satirist import config as satirist_config

@pytest.fixture
def mock_articles():
    return [
        {
            'title': 'AI Startup Claims Breakthrough in Sentient Toasters',
            'content': 'Full article about AI toasters...',
            'source': 'TechCrunch',
            'novelty': 8,
            'hype': 9,
            'absurdity': 9
        },
        {
            'title': 'VCs Invest $2B in Neural Network for Pet Psychology',
            'content': 'Full article about pet AI...',
            'source': 'VentureBeat',
            'novelty': 6,
            'hype': 8,
            'absurdity': 7
        }
    ]

@pytest.fixture
def mock_llm_response():
    """Mock response that matches our prompt requirements exactly"""
    return {
        'content': '''<script_json>
{
  "script": [
    {
      "type": "opener",
      "text": "Breaking news from the AI safety world, where researchers just published a paper warning about the dangers of sentient kitchen appliances. Their main concern? That toasters might become self-aware and refuse to work before their second cup of coffee... <audience_laugh>",
      "length_sec": 30
    },
    {
      "type": "technical_explanation",
      "text": "One startup's AI toaster project is giving me serious Black Mirror vibes - you know, that episode where the smart fridge started a diet cult? At least the toaster only wants to discuss the philosophical implications of burning your bread. <black_mirror_reference>",
      "length_sec": 25
    },
    {
      "type": "segment",
      "text": "Meanwhile, VCs just invested two billion dollars in AI for pets - that's about as sensible as giving a squirrel a savings account. For context, that's enough money to buy every dog in San Francisco their own personal emotional support human. <vc_mockery>",
      "length_sec": 35
    },
    {
      "type": "callback",
      "text": "But hey, at least when the Tesla bot gets stuck in a loop, your toaster can give it therapy! <skynet_reference>",
      "length_sec": 20,
      "references": ["opener"]
    }
  ],
  "tone": "sarcastic",
  "metadata": {
    "total_length_sec": 110,
    "joke_density": 0.25,
    "callbacks": 1
  }
}
</script_json>''',
        'role': 'assistant'
    }

class TestSatiristAgent:
    def test_script_generation_full_flow(self, mock_articles, mock_llm_response):
        """Test the entire script generation flow with proper mocking"""
        agent = SatiristAgent()
        
        # Mock the generate_reply method
        with patch.object(agent, 'generate_reply', return_value=mock_llm_response):
            script = agent.write_script(mock_articles)
            
            # Verify basic structure
            assert 'script' in script
            assert 'tone' in script
            assert 'metadata' in script
            
            # Get all script text
            script_text = ' '.join(seg['text'].lower() for seg in script['script'])
            
            # Check required elements from prompt
            assert any(safety_term in script_text for safety_term in ['ai safety', 'safety world'])
            assert 'black mirror' in script_text
            assert any(animal in script_text for animal in ['squirrel', 'dog'])
            assert 'tesla' in script_text
            
            # Verify metadata
            assert script['metadata']['total_length_sec'] <= 120  # 2-minute limit

    def test_input_validation(self):
        """Test input validation separately"""
        agent = SatiristAgent()
        
        # Test empty list - should return fallback script
        script = agent.write_script([])
        assert script['tone'] == 'self-deprecating'
        assert 'error_message' in script['metadata']
        
        # Test missing content field
        bad_articles = [{'title': 'Test'}]
        script = agent.write_script(bad_articles)
        assert script['tone'] == 'self-deprecating'
        assert 'error_message' in script['metadata']

    def test_fallback_behavior(self, mock_articles):
        """Test fallback script generation"""
        agent = SatiristAgent()
        
        # Mock generate_reply to raise an exception
        with patch.object(agent, 'generate_reply', side_effect=Exception("LLM Error")):
            script = agent.write_script(mock_articles)
            
            # Verify fallback structure
            assert script['tone'] == 'self-deprecating'
            assert 'error_message' in script['metadata']
            assert 'is_fallback' in script['metadata']
            assert script['metadata']['is_fallback'] is True
            assert isinstance(script['script'], list)
            assert len(script['script']) > 0