from typing import Dict, List
from pydantic import BaseModel, Field
import yaml
from pathlib import Path
import os
from functools import lru_cache

class StyleGuide(BaseModel):
    banned_topics: List[str]
    required_elements: List[str]
    max_joke_density: float
    voice: str
    tone_options: List[str]
    structure: List[str]

class TemplateConfig(BaseModel):
    autoescape: List[str]
    trim_blocks: bool
    lstrip_blocks: bool

class FormatExample(BaseModel):
    script: List[Dict]
    tone: str

class SatiristConfig(BaseModel):
    style_guide: StyleGuide
    templates: TemplateConfig
    format_example: FormatExample

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

# Create a singleton instance
config = ConfigLoader.load_config()
