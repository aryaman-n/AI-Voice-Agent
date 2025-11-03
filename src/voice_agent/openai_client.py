"""Async client for interacting with the OpenAI Realtime API."""
from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, Optional

import websockets

from .config import OpenAIConfig

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


class OpenAIRealtimeClient:
    """Minimal helper around the OpenAI realtime websocket API."""

    def __init__(self, config: OpenAIConfig):
        self._config = config
        self._connection: Optional[websockets.WebSocketClientProtocol] = None

    async def __aenter__(self) -> "OpenAIRealtimeClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.closed

    async def connect(self) -> websockets.WebSocketClientProtocol:
        if self.is_connected:
            return self._connection  # type: ignore[return-value]

        url = f"{OPENAI_REALTIME_URL}?model={self._config.model}"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        self._connection = await websockets.connect(url, extra_headers=headers)

        # configure the realtime session
        session_update = {
            "type": "session.update",
            "session": {
                "voice": self._config.voice,
            },
        }
        if self._config.instructions:
            session_update["session"]["instructions"] = self._config.instructions
        await self.send_json(session_update)

        return self._connection

    async def close(self) -> None:
        if self._connection and not self._connection.closed:
            await self._connection.close()
        self._connection = None

    async def send_json(self, payload: Dict) -> None:
        if not self.is_connected:
            raise RuntimeError("Realtime client not connected")
        await self._connection.send(json.dumps(payload))

    async def send_audio_chunk(self, audio_base64: str, end_of_input: bool = False) -> None:
        await self.send_json(
            {
                "type": "input_audio_buffer.append",
                "audio": audio_base64,
            }
        )
        if end_of_input:
            await self.send_json({"type": "input_audio_buffer.commit"})
            await self.send_json({"type": "response.create", "response": {}})

    async def responses(self) -> AsyncGenerator[Dict, None]:
        if not self.is_connected:
            raise RuntimeError("Realtime client not connected")

        assert self._connection is not None
        async for message in self._connection:
            yield json.loads(message)

    async def drain_until_finished(self) -> Dict:
        """Consume websocket responses until a response is complete."""
        final_event: Optional[Dict] = None
        async for event in self.responses():
            if event.get("type") == "response.completed":
                final_event = event
                break
        return final_event or {}
