from typing import Dict, List
from autogen import AssistantAgent
from pydantic import BaseModel

class ComedyPotential(BaseModel):
    """Identified comedy elements in an article"""
    absurdity_score: int  # 1-10 how absurd is this
    tech_buzzwords: List[str]  # Overused tech terms that could be mocked
    exaggerations: List[str]  # Claims that seem overblown
    contrasts: List[str]  # Ironic or contradictory elements
    numbers_to_mock: List[Dict[str, str]]  # Funding amounts, metrics etc worth joking about
    pop_culture_hooks: List[str]  # References that could be used (Black Mirror etc)
    callback_hooks: List[str]  # Elements that could be referenced later

class ArticleBrief(BaseModel):
    """Processed article with comedy potential"""
    title: str
    key_points: List[str]
    main_players: List[str]  # Companies, researchers, VCs involved
    quotable_quotes: List[str]  # Funny or mockable quotes
    numbers_and_stats: List[str]
    comedy_potential: ComedyPotential
