"""Configuration helpers for the voice agent service."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
DEFAULT_REALTIME_MODEL = "gpt-4o-realtime-mini"
DEFAULT_OPENAI_VOICE = "verse"


@dataclass
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_REALTIME_MODEL
    voice: str = DEFAULT_OPENAI_VOICE
    instructions: Optional[str] = None


@dataclass
class SignalWireConfig:
    space_url: str
    project_id: str
    api_token: str
    stream_url: Optional[str] = None


@dataclass
class Settings:
    openai: OpenAIConfig
    signalwire: SignalWireConfig
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "Settings":
        """Load configuration from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required")

        instructions = os.getenv("VOICE_AGENT_SYSTEM_PROMPT")
        openai_config = OpenAIConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_REALTIME_MODEL", DEFAULT_REALTIME_MODEL),
            voice=os.getenv("OPENAI_VOICE", DEFAULT_OPENAI_VOICE),
            instructions=instructions,
        )

        space_url = os.getenv("SIGNALWIRE_SPACE_URL")
        project_id = os.getenv("SIGNALWIRE_PROJECT_ID")
        api_token = os.getenv("SIGNALWIRE_API_TOKEN")
        if not (space_url and project_id and api_token):
            raise RuntimeError(
                "SIGNALWIRE_SPACE_URL, SIGNALWIRE_PROJECT_ID, and SIGNALWIRE_API_TOKEN are required"
            )
        signalwire_config = SignalWireConfig(
            space_url=space_url,
            project_id=project_id,
            api_token=api_token,
            stream_url=os.getenv("SIGNALWIRE_STREAM_URL"),
        )

        return cls(
            openai=openai_config,
            signalwire=signalwire_config,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.load()
