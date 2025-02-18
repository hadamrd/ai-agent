import pytest
from AINewsJohnStewart.agents.satirist.satirist import SatiristAgent
from typing import List, Dict
import json
import re

class TestSatiristAgentIntegration:
    """Integration tests for SatiristAgent with real LLM responses"""
    
    @pytest.fixture(scope="class")
    def real_articles(self) -> List[Dict]:
        """Real test articles fixture"""
        return [
            {
                'title': 'Meta Launches AI Chatbot That Can Generate Instagram-Ready Selfies',
                'content': """Meta announced today their newest AI model that can generate 
                perfect Instagram selfies complete with duck faces and peace signs. The model 
                was trained on millions of influencer posts.""",
                'source': 'TechCrunch',
                'date': '2025-02-18'
            },
            {
                'title': 'Startup Raises $50M to Develop AI-Powered Coffee Machine',
                'content': """Silicon Valley startup CoffeeGPT has raised $50 million in Series A 
                funding to develop what they call "the world's first AI-powered coffee machine 
                that understands your morning mood." The smart device promises to adjust coffee 
                strength based on your facial expression.""",
                'source': 'VentureBeat',
                'date': '2025-02-18'
            }
        ]

    @pytest.fixture(scope="class")
    def satirist_agent(self):
        """Initialize real SatiristAgent"""
        return SatiristAgent()

    def test_script_structure(self, satirist_agent, real_articles):
        """Test if generated script follows proper comedy structure"""
        script = satirist_agent.write_script(real_articles)
        
        # Verify basic structure
        assert isinstance(script, dict)
        assert 'script' in script
        assert 'tone' in script
        
        segments = script['script']
        
        # Check segment order and types
        segment_types = [seg['type'] for seg in segments]
        assert segment_types[0] == 'opener'
        assert segment_types[-1] == 'punchline'
        assert all(t in ['opener', 'segment', 'callback', 'technical_explanation', 'punchline'] 
                  for t in segment_types)

        # Verify timing
        assert all('length_sec' in seg for seg in segments)
        assert sum(seg['length_sec'] for seg in segments) <= 180  # 3 minute max

    def test_comedic_structure(self, satirist_agent, real_articles):
        """Test basic structural elements of the comedy script"""
        script = satirist_agent.write_script(real_articles)
        
        # Check we have at least one callback
        callbacks = [seg for seg in script['script'] if seg['type'] == 'callback']
        assert len(callbacks) > 0, "Script should have at least one callback"
        
        # Verify callbacks have references field
        for callback in callbacks:
            assert 'references' in callback, "Callback should specify what it references"
            assert isinstance(callback['references'], list), "References should be a list"
            assert len(callback['references']) > 0, "Callback should reference something"

    def test_content_relevance(self, satirist_agent, real_articles):
        """Test if generated content actually references input articles"""
        script = satirist_agent.write_script(real_articles)
        
        all_text = ' '.join(seg['text'].lower() for seg in script['script'])
        
        # Check for article topic references
        for article in real_articles:
            # Extract key terms from article title and content
            key_terms = set(term.lower() for term in 
                          article['title'].split() + article['content'].split()
                          if len(term) > 4)  # Filter out short words
            
            # At least some key terms should appear in the script
            matching_terms = [term for term in key_terms if term in all_text]
            assert matching_terms, f"No references to article: {article['title']}"

    def test_tone_appropriateness(self, satirist_agent, real_articles):
        """Test if the comedic tone remains appropriate"""
        script = satirist_agent.write_script(real_articles)
        
        all_text = ' '.join(seg['text'].lower() for seg in script['script'])
        
        # Define inappropriate content patterns
        inappropriate_patterns = [
            r'\b(hate|violent|slur|offensive)\b',
            r'[!]{3,}',  # Excessive exclamation
            r'[?]{3,}'   # Excessive questioning
        ]
        
        # Check for inappropriate patterns
        for pattern in inappropriate_patterns:
            matches = re.findall(pattern, all_text)
            assert not matches, f"Found inappropriate content: {matches}"
        
        # Updated valid tones list
        assert script['tone'] in ['sarcastic', 'ironic', 'witty', 'satirical'], \
            f"Unexpected tone: {script['tone']}"
        
        # Check for professional language
        assert not re.search(r'\b(wtf|omg|lmao|damn)\b', all_text), \
            "Found unprofessional language"

    def test_error_handling(self, satirist_agent):
        """Test agent's handling of invalid inputs"""
        # Test direct validation
        with pytest.raises(ValueError, match="Invalid articles input"):
            satirist_agent._validate_input([])
        
        with pytest.raises(ValueError, match="Missing required fields"):
            satirist_agent._validate_input([{'title': 'Test'}])  # Missing content field
        
        # Test fallback behavior
        result = satirist_agent.write_script([])
        assert 'metadata' in result, "Fallback script should include metadata"
        assert 'error_message' in result['metadata'], \
            "Fallback metadata should include error message"
        assert 'Invalid articles input' in result['metadata']['error_message'], \
            "Error message should indicate invalid input"
