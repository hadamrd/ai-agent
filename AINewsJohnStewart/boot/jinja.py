from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import List, Optional, Union, Dict

from pydantic import BaseModel

def bold(text: str) -> str:
    return f"**{text}**"

def italic(text: str) -> str:
    return f"*{text}*"

def code(text: str) -> str:
    return f"`{text}`"

def pydantic_safe(obj):
    """Convert pydantic models to dict for JSON serialization"""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    return obj

def create_env(
    templates_dir: str,
    autoescape: Union[List[str], bool] = ['html', 'xml'],
    trim_blocks: bool = True,
    lstrip_blocks: bool = True
) -> Environment:
    """Create a Jinja environment with custom filters and specified configuration"""
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(autoescape),
        trim_blocks=trim_blocks,
        lstrip_blocks=lstrip_blocks
    )
    
    # Register custom filters
    env.filters['bold'] = bold
    env.filters['italic'] = italic
    env.filters['code'] = code
    env.filters['pydantic_safe'] = pydantic_safe
    
    return env
