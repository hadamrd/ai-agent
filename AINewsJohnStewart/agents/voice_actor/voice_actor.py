import re
from autogen import AssistantAgent
from elevenlabs import generate, save

from AINewsJohnStewart.utils.logger import setup_logger

logger = setup_logger(__name__)

class VoiceActorAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="SnarkyVoice",
            system_message="Convert scripts to audio with dramatic pauses. Add sarcastic tone markers.",
            llm_config={"config_list": [...]}
        )
        self.voice_settings = {
            "voice": "Biden",
            "model": "eleven_multilingual_v2",
            "stability": 0.7,
            "similarity_boost": 0.5
        }

    def text_to_speech(self, script):
        try:
            sanitized = self._sanitize_text(script)
            audio = generate(
                text=sanitized,
                **self.voice_settings
            )
            filename = f"output_{hash(script)}.mp3"
            save(audio, filename)
            return filename
        except Exception as e:
            logger.error(f"Voice generation failed: {str(e)}")
            return None

    def _sanitize_text(self, text):
        # Remove markdown and JSON artifacts
        return re.sub(r'[\[\]{}"]', '', text[:5000])  # Limit for API safety
    