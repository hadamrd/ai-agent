import os
from autogen import AssistantAgent
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_random_exponential
from AINewsJohnStewart.utils.logger import setup_logger
from AINewsJohnStewart.utils.settings import settings
from functools import lru_cache
import re
import json

logger = setup_logger(__name__)

class SatiristAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="AI_Comedian",
            llm_config=settings.SATIRIST_CONFIG,
            system_message="""You're head writer for Last Week Tonight with AI. Create scripts that:
1. Mock AI hype cycles
2. Satirize tech leadership
3. Explain technical concepts through absurd analogies
4. Include 1 callback joke
5. End with ironic twist

Format:
{
"script": [
  {"type": "opener", "text": "...", "length_sec": 20},
  {"type": "segment", "text": "...", "reference": "..."},
  {"type": "punchline", "text": "..."}
],
"tone": "sarcastic/serious/absurd"
}"""
        )
        self.style_guide = {
            "banned_topics": ["violence", "racism", "sexism"],
            "required_elements": ["skynet_reference", "vc_mockery"],
            "max_joke_density": 0.3  # Jokes per token
        }
        self.register_reply([AssistantAgent], SatiristAgent.generate_script_reply)

    def generate_script_reply(self, recipient, messages, sender, config):
        last_message = messages[-1]["content"]
        if "processed_articles" in last_message:
            articles = json.loads(last_message["processed_articles"])
            script = self.write_script(articles)
            return {"script": script, "status": "HUMOR_ENGAGED"}
        return super().generate_reply(recipient, messages, sender, config)
    
    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=60))
    def write_script(self, articles: List[Dict]) -> Dict:
        """Generate satirical script with guardrails"""
        try:
            if not self._validate_input(articles):
                raise ValueError("Invalid article input")
                
            prompt = self._build_prompt(articles)
            raw_response = self.generate_reply([{"content": prompt, "role": "user"}])
            
            return self._validate_output(raw_response)
            
        except Exception as e:
            logger.error(f"Script generation failed: {str(e)}")
            return self._fallback_script()

    def _build_prompt(self, articles: List[Dict]) -> str:
        """Structured prompt engineering"""
        headlines = [a['title'] for a in articles[:5]]  # Use top 5
        return f"""Create 2-minute satirical news script about these AI developments:
{json.dumps(headlines)}

INSTRUCTIONS:
1. Opening joke about AI safety researchers
2. Compare one project to Black Mirror episode
3. Mock investment figures using animal analogies
4. Closing joke referencing {self._get_current_tech_fiasco()}

AVOID:
- Low effort GPT jokes
- Overused Matrix references
- Complaining about AI taking jobs

FORMAT: JSON schema-compliant
"""

    def _validate_input(self, articles: List[Dict]) -> bool:
        """Sanity check incoming data"""
        return (
            len(articles) >= 1 and
            all(isinstance(a, dict) for a in articles) and
            sum(len(a.get('title', '')) for a in articles) < 5000  # Prevent prompt flooding
        )

    def _validate_output(self, raw: str) -> Dict:
        """Ensure safe, structured output"""
        try:
            # Extract JSON from Claude's response
            json_str = re.search(r'\{.*\}', raw, re.DOTALL).group()
            script_data = json.loads(json_str)
            
            # Content safety check
            for banned in self.style_guide["banned_topics"]:
                if re.search(banned, json_str, re.IGNORECASE):
                    raise ValueError(f"Banned topic detected: {banned}")
                    
            # Structure validation
            required_sections = {'opener', 'segment', 'punchline'}
            if not required_sections.issubset([s['type'] for s in script_data['script']]):
                raise ValueError("Missing required script sections")
                
            return script_data
            
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            logger.warning(f"Output validation failed: {str(e)}")
            return self._fallback_script()

    def _fallback_script(self) -> Dict:
        """Fail-safe generic script"""
        return {
            "script": [{
                "type": "opener",
                "text": "Breaking news: AI still can't tell a joke properly...",
                "length_sec": 15
            }],
            "tone": "self-deprecating"
        }

    def _get_current_tech_fiasco(self) -> str:
        """Keep references fresh"""
        # Could be API call to trending tech news
        return "Twitter's Grok AI implementation"
    