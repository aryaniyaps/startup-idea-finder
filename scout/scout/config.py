"""Configuration and user profile management for Startup Idea Scout."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables (SCOUT_ prefix)."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "env_prefix": "SCOUT_", "extra": "ignore"}

    # Required
    openai_api_key: str = ""

    # Optional — scouts use stealth browser / RSS when keys are empty (no API keys needed)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    github_token: str = ""
    x_bearer_token: str = ""

    # CamoFox stealth browser API
    browser_api_url: str = "http://localhost:9377"
    browser_user_id: str = "scout"

    scrape_interval_minutes: int = 15
    active_hours_start: int = 6
    active_hours_end: int = 23
    max_ideas_tracked: int = 500
    alert_threshold: int = 70
    llm_model: str = "gpt-4o-mini"
    worldmonitor_url: str = "http://localhost:3000"
    deep_dive_interval_minutes: int = 5

    data_dir: str = str(Path.home() / ".scout")
    db_path: str = str(Path.home() / ".scout" / "scout.db")
    profile_path: str = str(Path.home() / ".scout" / "profile.json")
    graph_path: str = str(Path.home() / "research" / "startup-idea-finder" / "graphify-out" / "graph.json")


@dataclass
class UserProfile:
    """User profile for founder-market fit scoring."""

    skills: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    years_experience: int = 0
    technical_depth: float = 0.5
    capital_available: float = 0.0
    problems_experienced: list[str] = field(default_factory=list)
    anti_preferences: list[str] = field(default_factory=list)


def load_profile(path: str) -> UserProfile:
    """Load user profile from JSON file. Returns defaults if file missing or malformed."""
    try:
        with open(path) as f:
            data = json.load(f)
        return UserProfile(
            skills=data.get("skills", []),
            industries=data.get("industries", []),
            years_experience=data.get("years_experience", 0),
            technical_depth=data.get("technical_depth", 0.5),
            capital_available=data.get("capital_available", 0.0),
            problems_experienced=data.get("problems_experienced", []),
            anti_preferences=data.get("anti_preferences", []),
        )
    except (FileNotFoundError, json.JSONDecodeError):
        return UserProfile()


def save_profile(profile: UserProfile, path: str) -> None:
    """Save user profile to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            {
                "skills": profile.skills,
                "industries": profile.industries,
                "years_experience": profile.years_experience,
                "technical_depth": profile.technical_depth,
                "capital_available": profile.capital_available,
                "problems_experienced": profile.problems_experienced,
                "anti_preferences": profile.anti_preferences,
            },
            f,
            indent=2,
        )
