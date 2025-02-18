from typing import Any, Dict, List
from pydantic import BaseModel, Field, field_validator
import yaml
from pathlib import Path
import os
from functools import lru_cache

class SectionLengthLimits(BaseModel):
    opener: Dict[str, int]
    segment: Dict[str, int]
    punchline: Dict[str, int]

class ValidationConfig(BaseModel):
    retry_attempts: int
    retry_max_wait: int
    retry_multiplier: int
    max_length_minutes: int
    section_length_limits: SectionLengthLimits

class FallbackMetadata(BaseModel):
    error_context_template: str
    fallback_type: str
    style_elements: Dict[str, bool]

class StyleGuide(BaseModel):
    banned_topics: List[str]
    required_elements: List[str]
    max_joke_density: float
    joke_density_tolerance: float
    voice: str
    tone_options: List[str]
    structure: List[str]

class TemplateConfig(BaseModel):
    autoescape: List[str]
    trim_blocks: bool
    lstrip_blocks: bool
    required_sections: List[str]

class Script(BaseModel):
    script: List[Dict[str, Any]] = Field(..., description="List of script segments")
    tone: str = Field(..., description="Overall tone of the script")
    
    @field_validator("script")
    def validate_links(cls, v):
        # Verify callback references exist
        callback_refs = [s.get("references") 
                       for s in v if s["type"] == "callback"]
        existing = {s["type"] for s in v}
        
        for refs in callback_refs:
            if not set(refs).issubset(existing):
                missing = set(refs) - existing
                raise ValueError(f"Callback references missing: {missing}")
        return v
    
    @field_validator("tone")
    def validate_tone(cls, v):
        valid_tones = {"sarcastic", "serious", "absurd"}
        if v not in valid_tones:
            raise ValueError(f"Invalid tone: {v}. Must be one of {valid_tones}")
        return v
    
class FallbackConfig(BaseModel):
    script: List[Dict]
    tone: str
    metadata: FallbackMetadata

class ScriptSettings(BaseModel):
    format_example: Script
    fallback: FallbackConfig
    validation: ValidationConfig

class SatiristConfig(BaseModel):
    style_guide: StyleGuide
    templates: TemplateConfig
    script_settings: ScriptSettings

    @property
    def style_rules(self) -> Dict:
        return {
            "voice": self.style_guide.voice,
            "tone_options": self.style_guide.tone_options,
            "structure": self.style_guide.structure,
            "requirements": self.style_guide.required_elements  # Fix property name
        }

class ConfigLoader:
    @staticmethod
    @lru_cache()
    def load_config() -> SatiristConfig:
        config_path = os.path.join(
            Path(__file__).parent,
            "config.yaml"
        )

        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            return SatiristConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")
